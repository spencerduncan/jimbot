use axum::response::Json;
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

use crate::api::models::HealthResponse;

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
    // Return basic Prometheus format metrics
    // In a real implementation, this would come from the metrics registry
    format!(
        "# HELP event_bus_events_received_total Total number of events received\n\
         # TYPE event_bus_events_received_total counter\n\
         event_bus_events_received_total 0\n\
         \n\
         # HELP event_bus_events_processed_total Total number of events processed\n\
         # TYPE event_bus_events_processed_total counter\n\
         event_bus_events_processed_total 0\n\
         \n\
         # HELP event_bus_processing_latency_seconds Event processing latency\n\
         # TYPE event_bus_processing_latency_seconds histogram\n\
         event_bus_processing_latency_seconds_bucket{{le=\"0.001\"}} 0\n\
         event_bus_processing_latency_seconds_bucket{{le=\"0.01\"}} 0\n\
         event_bus_processing_latency_seconds_bucket{{le=\"0.1\"}} 0\n\
         event_bus_processing_latency_seconds_bucket{{le=\"1\"}} 0\n\
         event_bus_processing_latency_seconds_bucket{{le=\"+Inf\"}} 0\n\
         event_bus_processing_latency_seconds_sum 0\n\
         event_bus_processing_latency_seconds_count 0\n"
    )
}
