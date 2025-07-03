use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// JSON event structure received from BalatroMCP
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonEvent {
    #[serde(rename = "type")]
    pub event_type: String,
    pub source: String,
    pub timestamp: Option<i64>,
    pub version: Option<i32>,
    pub payload: serde_json::Value,
}

/// Batch event request
#[derive(Debug, Deserialize)]
pub struct BatchEventRequest {
    pub events: Vec<JsonEvent>,
}

/// API response
#[derive(Debug, Serialize)]
pub struct ApiResponse {
    pub status: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

impl ApiResponse {
    pub fn ok() -> Self {
        Self {
            status: "ok".to_string(),
            message: None,
            error: None,
        }
    }

    pub fn error(msg: String) -> Self {
        Self {
            status: "error".to_string(),
            message: None,
            error: Some(msg),
        }
    }
}

/// Health check response
#[derive(Debug, Serialize)]
pub struct HealthResponse {
    pub status: String,
    pub version: String,
    pub uptime_seconds: u64,
    pub metadata: HashMap<String, String>,
}

/// Metrics response
#[derive(Debug, Serialize)]
pub struct MetricsResponse {
    pub events_received: u64,
    pub events_processed: u64,
    pub events_failed: u64,
    pub current_subscribers: usize,
    pub avg_processing_time_ms: f64,
}
