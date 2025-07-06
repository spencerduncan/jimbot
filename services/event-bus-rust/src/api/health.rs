use axum::response::Json;
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

use crate::api::models::{HealthResponse, MetricsResponse};

static START_TIME: std::sync::OnceLock<u64> = std::sync::OnceLock::new();

pub async fn health_check() -> Json<HealthResponse> {
    let start_time = START_TIME.get_or_init(|| {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs()
    });

    let current_time = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs();

    let mut metadata = HashMap::new();
    metadata.insert("service".to_string(), "event-bus-rust".to_string());
    metadata.insert("protocol_version".to_string(), "1.0".to_string());

    Json(HealthResponse {
        status: "healthy".to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
        uptime_seconds: current_time - start_time,
        metadata,
    })
}

pub async fn metrics() -> String {
    // Return Prometheus format metrics
    // The metrics-exporter-prometheus handles this automatically
    // through its HTTP endpoint at :9090/metrics
    // This endpoint is now just a redirect notice
    "Prometheus metrics available at :9090/metrics".to_string()
}
