use crate::{
    allocator::{AllocationRequest, ResourceAllocator, ResourceType},
    config::ResourceCoordinatorConfig,
    metrics::MetricsCollector,
    rate_limiter::{MultiTierRateLimiter, RateLimiterBuilder},
};
use axum::{
    extract::{Json, State},
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post},
    Router,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::net::TcpListener;
use tokio::time::Duration;
use tower::ServiceBuilder;
use tower_http::{
    cors::CorsLayer,
    timeout::TimeoutLayer,
    trace::{DefaultMakeSpan, DefaultOnResponse, TraceLayer},
};
use tracing::{info, Level};

/// Server state shared across handlers
#[derive(Clone)]
pub struct ServerState {
    pub allocator: Arc<ResourceAllocator>,
    pub rate_limiter: Arc<MultiTierRateLimiter>,
    pub metrics: Arc<MetricsCollector>,
    pub config: Arc<ResourceCoordinatorConfig>,
}

/// Request to allocate resources
#[derive(Debug, Deserialize)]
pub struct AllocateRequest {
    pub component_id: String,
    pub resource_type: String,
    pub duration_secs: Option<u64>,
    pub priority: Option<u8>,
    
    // Resource-specific parameters
    pub cpu_cores: Option<u32>,
    pub memory_mb: Option<u64>,
    pub api_name: Option<String>,
}

/// Response from allocation request
#[derive(Debug, Serialize)]
pub struct AllocateResponse {
    pub success: bool,
    pub message: String,
    pub allocation_id: Option<String>,
}

/// Request to release resources
#[derive(Debug, Deserialize)]
pub struct ReleaseRequest {
    pub component_id: String,
    pub resource_type: String,
}

/// Health check response
#[derive(Debug, Serialize)]
pub struct HealthResponse {
    pub status: String,
    pub version: String,
    pub uptime_secs: u64,
}

/// Resource usage statistics
#[derive(Debug, Serialize)]
pub struct UsageStats {
    pub resource_usage: std::collections::HashMap<String, f64>,
    pub allocation_stats: crate::metrics::AllocationStats,
}

/// Start the resource coordinator server
pub async fn start_server(config: ResourceCoordinatorConfig) -> Result<(), Box<dyn std::error::Error>> {
    let config = Arc::new(config);
    
    // Initialize components
    let memory_bytes = config.resources.memory_mb * 1024 * 1024;
    let allocator = Arc::new(ResourceAllocator::new(
        config.resources.cpu_cores,
        memory_bytes,
    ));
    
    // Setup rate limiter with tiers
    let rate_limiter = Arc::new(
        RateLimiterBuilder::new("basic".to_string())
            .add_basic_tier(100)   // 100 requests per hour
            .add_premium_tier(1000) // 1000 requests per hour
            .add_tier("unlimited".to_string(), 100000, 100.0) // Effectively unlimited
            .build()
    );
    
    let metrics = Arc::new(MetricsCollector::new());
    
    // Start metrics export
    if config.monitoring.enabled {
        metrics.start_export(Duration::from_secs(config.monitoring.export_interval_secs));
    }
    
    let state = ServerState {
        allocator,
        rate_limiter,
        metrics,
        config: config.clone(),
    };
    
    // Build the application
    let app = Router::new()
        .route("/allocate", post(handle_allocate))
        .route("/release", post(handle_release))
        .route("/stats", get(handle_stats))
        .route("/health", get(handle_health))
        .route("/metrics", get(handle_metrics))
        .layer(
            ServiceBuilder::new()
                .layer(
                    TraceLayer::new_for_http()
                        .make_span_with(DefaultMakeSpan::new().level(Level::INFO))
                        .on_response(DefaultOnResponse::new().level(Level::INFO)),
                )
                .layer(TimeoutLayer::new(Duration::from_secs(
                    config.server.request_timeout_secs,
                )))
                .layer(CorsLayer::permissive()),
        )
        .with_state(state);
    
    // Start the server
    let addr = format!("{}:{}", config.server.host, config.server.port);
    info!("Starting resource coordinator server on {}", addr);
    
    let listener = TcpListener::bind(&addr).await?;
    axum::serve(listener, app).await?;
    
    Ok(())
}

/// Handle resource allocation requests
async fn handle_allocate(
    State(state): State<ServerState>,
    Json(request): Json<AllocateRequest>,
) -> impl IntoResponse {
    // Check rate limit
    if let Err(e) = state.rate_limiter.try_acquire(&request.component_id, 1).await {
        return (
            StatusCode::TOO_MANY_REQUESTS,
            Json(AllocateResponse {
                success: false,
                message: format!("Rate limit exceeded: {}", e),
                allocation_id: None,
            }),
        );
    }
    
    // Parse resource type
    let resource_type = match request.resource_type.as_str() {
        "gpu" => ResourceType::Gpu,
        "cpu" => match request.cpu_cores {
            Some(cores) => ResourceType::CpuCores(cores),
            None => {
                return (
                    StatusCode::BAD_REQUEST,
                    Json(AllocateResponse {
                        success: false,
                        message: "CPU allocation requires cpu_cores parameter".to_string(),
                        allocation_id: None,
                    }),
                );
            }
        },
        "memory" => match request.memory_mb {
            Some(mb) => ResourceType::Memory(mb * 1024 * 1024),
            None => {
                return (
                    StatusCode::BAD_REQUEST,
                    Json(AllocateResponse {
                        success: false,
                        message: "Memory allocation requires memory_mb parameter".to_string(),
                        allocation_id: None,
                    }),
                );
            }
        },
        "api" => match request.api_name {
            Some(api) => ResourceType::ApiQuota(api),
            None => {
                return (
                    StatusCode::BAD_REQUEST,
                    Json(AllocateResponse {
                        success: false,
                        message: "API allocation requires api_name parameter".to_string(),
                        allocation_id: None,
                    }),
                );
            }
        },
        _ => {
            return (
                StatusCode::BAD_REQUEST,
                Json(AllocateResponse {
                    success: false,
                    message: format!("Unknown resource type: {}", request.resource_type),
                    allocation_id: None,
                }),
            );
        }
    };
    
    // Create allocation request
    let duration = Duration::from_secs(
        request.duration_secs.unwrap_or(state.config.resources.default_duration_secs)
    );
    let priority = request.priority.unwrap_or(100);
    
    let alloc_request = AllocationRequest {
        component_id: request.component_id.clone(),
        resource_type: resource_type.clone(),
        duration,
        priority,
    };
    
    // Try to allocate
    let timer = crate::metrics::AllocationTimer::new(&request.resource_type);
    
    match state.allocator.allocate(alloc_request).await {
        Ok(()) => {
            timer.record(&state.metrics);
            state.metrics.record_allocation_attempt(
                &request.resource_type,
                &request.component_id,
                true,
            ).await;
            
            let allocation_id = format!("{}:{}:{}", 
                request.component_id,
                request.resource_type,
                chrono::Utc::now().timestamp()
            );
            
            (
                StatusCode::OK,
                Json(AllocateResponse {
                    success: true,
                    message: "Resource allocated successfully".to_string(),
                    allocation_id: Some(allocation_id),
                }),
            )
        }
        Err(e) => {
            timer.record(&state.metrics);
            state.metrics.record_allocation_attempt(
                &request.resource_type,
                &request.component_id,
                false,
            ).await;
            
            (
                StatusCode::CONFLICT,
                Json(AllocateResponse {
                    success: false,
                    message: e,
                    allocation_id: None,
                }),
            )
        }
    }
}

/// Handle resource release requests
async fn handle_release(
    State(state): State<ServerState>,
    Json(request): Json<ReleaseRequest>,
) -> impl IntoResponse {
    // Parse resource type for release
    let resource_type = match request.resource_type.as_str() {
        "gpu" => ResourceType::Gpu,
        "cpu" => ResourceType::CpuCores(0), // Cores not needed for release
        "memory" => ResourceType::Memory(0), // Bytes not needed for release
        "api" => ResourceType::ApiQuota(String::new()), // API name not needed for release
        _ => {
            return (
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({
                    "success": false,
                    "message": format!("Unknown resource type: {}", request.resource_type)
                })),
            );
        }
    };
    
    match state.allocator.release(&request.component_id, &resource_type).await {
        Ok(()) => (
            StatusCode::OK,
            Json(serde_json::json!({
                "success": true,
                "message": "Resource released successfully"
            })),
        ),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({
                "success": false,
                "message": e
            })),
        ),
    }
}

/// Handle usage statistics requests
async fn handle_stats(State(state): State<ServerState>) -> impl IntoResponse {
    let resource_usage = state.allocator.get_usage_stats().await;
    let allocation_stats = state.metrics.get_allocation_stats().await;
    
    // Update metrics
    for (resource_type, usage) in &resource_usage {
        state.metrics.record_utilization(resource_type, usage * 100.0).await;
    }
    
    Json(UsageStats {
        resource_usage,
        allocation_stats,
    })
}

/// Handle health check requests
async fn handle_health() -> impl IntoResponse {
    Json(HealthResponse {
        status: "healthy".to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
        uptime_secs: 0, // TODO: Track actual uptime
    })
}

/// Handle metrics requests (Prometheus format)
async fn handle_metrics() -> impl IntoResponse {
    // For now, return a simple metrics response
    // TODO: Integrate with actual prometheus metrics
    let metrics = format!(
        "# HELP resource_allocation_total Total number of resource allocation attempts\n\
        # TYPE resource_allocation_total counter\n\
        resource_allocation_total 0\n"
    );
    
    (
        StatusCode::OK,
        [(axum::http::header::CONTENT_TYPE, "text/plain; version=0.0.4")],
        metrics,
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::{Request, StatusCode};
    use tower::ServiceExt;
    
    fn create_test_app() -> Router {
        let config = ResourceCoordinatorConfig::default();
        let allocator = Arc::new(ResourceAllocator::new(4, 1024 * 1024 * 1024));
        let rate_limiter = Arc::new(
            RateLimiterBuilder::new("basic".to_string())
                .add_basic_tier(100)
                .build()
        );
        let metrics = Arc::new(MetricsCollector::new());
        
        let state = ServerState {
            allocator,
            rate_limiter,
            metrics,
            config: Arc::new(config),
        };
        
        Router::new()
            .route("/allocate", post(handle_allocate))
            .route("/health", get(handle_health))
            .with_state(state)
    }
    
    #[tokio::test]
    async fn test_health_endpoint() {
        let app = create_test_app();
        
        let response = app
            .oneshot(
                Request::builder()
                    .uri("/health")
                    .method("GET")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        
        assert_eq!(response.status(), StatusCode::OK);
    }
    
    #[tokio::test]
    async fn test_allocate_gpu() {
        let app = create_test_app();
        
        let request_body = serde_json::json!({
            "component_id": "test_component",
            "resource_type": "gpu",
            "duration_secs": 60,
            "priority": 100
        });
        
        let response = app
            .oneshot(
                Request::builder()
                    .uri("/allocate")
                    .method("POST")
                    .header("content-type", "application/json")
                    .body(Body::from(request_body.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        
        assert_eq!(response.status(), StatusCode::OK);
    }
}