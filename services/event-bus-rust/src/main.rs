mod api;
mod grpc;
mod proto;
mod routing;
mod metrics;
mod tracing_config;

use anyhow::Result;
use axum::{routing::post, Router};
use std::{net::SocketAddr, sync::Arc};
use tower_http::{cors::CorsLayer, trace::TraceLayer};
use tracing::{error, info};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

use crate::{
    api::{handlers, health},
    grpc::EventBusService,
    routing::EventRouter,
};

#[derive(Clone)]
pub struct AppState {
    pub router: Arc<EventRouter>,
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize metrics subsystem
    metrics::init_metrics();
    
    // Initialize OpenTelemetry tracing (this also sets up the tracing subscriber)
    if let Err(e) = tracing_config::init_tracing() {
        eprintln!("Failed to initialize OpenTelemetry tracing: {}", e);
        // Fall back to basic tracing
        tracing_subscriber::registry()
            .with(
                tracing_subscriber::EnvFilter::try_from_default_env()
                    .unwrap_or_else(|_| "event_bus_rust=debug,tower_http=debug".into()),
            )
            .with(tracing_subscriber::fmt::layer().json())
            .init();
    }

    info!("Starting Rust Event Bus with enhanced observability");

    // Initialize event router
    let router = Arc::new(EventRouter::new());
    let app_state = AppState {
        router: router.clone(),
    };

    // Build REST API
    let rest_app = Router::new()
        .route("/api/v1/events", post(handlers::handle_single_event))
        .route("/api/v1/events/batch", post(handlers::handle_batch_events))
        .route("/health", axum::routing::get(health::health_check))
        .route("/metrics", axum::routing::get(health::metrics))
        .layer(CorsLayer::permissive())
        .layer(TraceLayer::new_for_http())
        .with_state(app_state);

    // Start REST API server
    let rest_addr = SocketAddr::from(([0, 0, 0, 0], 8080));
    info!("REST API listening on {}", rest_addr);

    let rest_server = tokio::spawn(async move {
        let listener = tokio::net::TcpListener::bind(&rest_addr)
            .await
            .expect("Failed to bind to address");
        axum::serve(listener, rest_app)
            .await
            .expect("REST server failed");
    });

    // Start gRPC server
    let grpc_addr = "[::]:50051";
    let grpc_service = EventBusService::new(router);

    info!("gRPC server listening on {}", grpc_addr);

    // Note: For now, we'll just have the gRPC service ready but not start a separate server
    // The actual gRPC service would need a proper proto definition file
    // This is a placeholder for the gRPC functionality
    let grpc_server = tokio::spawn(async move {
        // TODO: Implement proper gRPC server when proto service is defined
        tokio::time::sleep(tokio::time::Duration::from_secs(3600)).await;
    });

    // Set up graceful shutdown
    let shutdown_signal = async {
        tokio::signal::ctrl_c()
            .await
            .expect("Failed to install Ctrl+C handler");
        info!("Received shutdown signal");
    };

    // Wait for servers or shutdown signal    
    tokio::select! {
        result = async { tokio::try_join!(rest_server, grpc_server) } => {
            match result {
                Ok(_) => info!("Servers terminated successfully"),
                Err(e) => error!("Server error: {}", e),
            }
        }
        _ = shutdown_signal => {
            info!("Shutting down gracefully");
        }
    }

    // Shutdown OpenTelemetry
    tracing_config::shutdown_tracing();
    info!("Event Bus shutdown complete");

    Ok(())
}
