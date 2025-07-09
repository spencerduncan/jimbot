mod api;
mod config;
mod grpc;
mod metrics;
mod proto;
mod routing;
mod tracing_config;

use anyhow::Result;
use axum::{routing::post, Router};
use std::{net::SocketAddr, sync::Arc, time::Duration};
use tokio::signal;
use tower_http::{
    cors::{Any, CorsLayer},
    limit::RequestBodyLimitLayer,
    timeout::TimeoutLayer,
    trace::TraceLayer,
};
use tracing::{error, info, warn};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

use crate::{
    api::{handlers, health},
    config::{AppConfig, ConfigManager},
    grpc::EventBusService,
    routing::EventRouter,
};

#[derive(Clone)]
pub struct AppState {
    pub router: Arc<EventRouter>,
    pub config: Arc<AppConfig>,
}

#[tokio::main]
async fn main() -> Result<()> {
    // Load configuration first
    let mut config_manager = ConfigManager::load()?;
    let config = Arc::new(config_manager.get());

    // Initialize metrics subsystem
    metrics::init_metrics();

    // Initialize tracing based on configuration
    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new(&config.logging.level));
    
    // Initialize OpenTelemetry tracing (this also sets up the tracing subscriber)
    let tracer_provider = match tracing_config::init_tracing() {
        Ok(provider) => Some(provider),
        Err(e) => {
            eprintln!("Failed to initialize OpenTelemetry tracing: {}", e);
            // Fall back to basic tracing based on config
            let subscriber = tracing_subscriber::registry().with(filter);
            
            // Configure logging format based on config
            match config.logging.format.as_str() {
                "json" => {
                    subscriber.with(tracing_subscriber::fmt::layer().json()).init();
                }
                "pretty" => {
                    subscriber.with(tracing_subscriber::fmt::layer().pretty()).init();
                }
                _ => {
                    subscriber.with(tracing_subscriber::fmt::layer()).init();
                }
            }
            None
        }
    };
    
    info!(
        "Starting Rust Event Bus in {} environment with enhanced observability",
        config.environment
    );

    // Initialize event router with configuration
    let router = Arc::new(EventRouter::new_with_config(config.clone()));
    let app_state = AppState {
        router: router.clone(),
        config: config.clone(),
    };

    // Build REST API with configuration
    let mut rest_app = Router::new()
        .route("/api/v1/events", post(handlers::handle_single_event))
        .route("/api/v1/events/batch", post(handlers::handle_batch_events))
        .route("/health", axum::routing::get(health::health_check));

    // Add metrics endpoint if enabled
    if config.metrics.enabled {
        rest_app = rest_app.route(
            &config.metrics.prometheus_path,
            axum::routing::get(health::metrics),
        );
    }

    // Configure CORS based on settings
    let cors_layer = if config.server.rest.cors_enabled {
        if config
            .server
            .rest
            .cors_allowed_origins
            .contains(&"*".to_string())
        {
            CorsLayer::permissive()
        } else {
            let origins: Vec<_> = config
                .server
                .rest
                .cors_allowed_origins
                .iter()
                .filter_map(|origin| origin.parse().ok())
                .collect();
            CorsLayer::new()
                .allow_origin(origins)
                .allow_methods(Any)
                .allow_headers(Any)
        }
    } else {
        CorsLayer::new()
    };

    let rest_app = rest_app
        .layer(RequestBodyLimitLayer::new(config.server.rest.max_body_size))
        .layer(TimeoutLayer::new(Duration::from_secs(
            config.server.rest.request_timeout_secs,
        )))
        .layer(cors_layer)
        .layer(TraceLayer::new_for_http())
        .with_state(app_state);

    // Start REST API server with configured address
    let rest_addr: SocketAddr =
        format!("{}:{}", config.server.rest.host, config.server.rest.port).parse()?;
    info!("REST API listening on {}", rest_addr);

    let rest_server = tokio::spawn(async move {
        let listener = tokio::net::TcpListener::bind(&rest_addr)
            .await
            .expect("Failed to bind to address");
        axum::serve(listener, rest_app)
            .await
            .expect("REST server failed");
    });

    // Start gRPC server with configured address
    let grpc_addr: SocketAddr =
        format!("{}:{}", config.server.grpc.host, config.server.grpc.port).parse()?;
    let _grpc_service = EventBusService::new(router);

    info!("gRPC server listening on {}", grpc_addr);

    // Note: For now, we'll just have the gRPC service ready but not start a separate server
    // The actual gRPC service would need a proper proto definition file
    // This is a placeholder for the gRPC functionality
    let grpc_server = tokio::spawn(async move {
        // TODO: Implement proper gRPC server when proto service is defined
        tokio::time::sleep(tokio::time::Duration::from_secs(3600)).await;
    });

    // Enable hot-reload if not in production
    let config_clone = config.clone();
    if config.environment != "prod" {
        match config_manager.enable_hot_reload().await {
            Ok(mut config_rx) => {
                tokio::spawn(async move {
                    while let Some(_new_config) = config_rx.recv().await {
                        info!("Configuration reloaded, some changes may require restart");
                        // Note: Some configuration changes would require server restart
                        // This is a notification mechanism for now
                    }
                });
            }
            Err(e) => {
                warn!("Failed to enable configuration hot-reload: {}", e);
            }
        }
    }

    // Set up graceful shutdown
    let shutdown_timeout = Duration::from_secs(config_clone.server.shutdown_timeout_secs);

    tokio::select! {
        res = rest_server => {
            error!("REST server stopped: {:?}", res);
        }
        res = grpc_server => {
            error!("gRPC server stopped: {:?}", res);
        }
        _ = shutdown_signal() => {
            info!("Shutdown signal received, stopping servers gracefully");
            // Give ongoing requests time to complete
            tokio::time::sleep(shutdown_timeout).await;
        }
    }

    // Shutdown OpenTelemetry
    if let Some(provider) = tracer_provider {
        if let Err(e) = tracing_config::shutdown_tracing(provider) {
            error!("Failed to shutdown tracer provider: {}", e);
        }
    }
    info!("Event Bus shutdown complete");

    Ok(())
}

/// Wait for shutdown signal
async fn shutdown_signal() {
    let ctrl_c = async {
        signal::ctrl_c()
            .await
            .expect("Failed to install Ctrl+C handler");
    };

    #[cfg(unix)]
    let terminate = async {
        signal::unix::signal(signal::unix::SignalKind::terminate())
            .expect("Failed to install signal handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => {},
        _ = terminate => {},
    }
}
