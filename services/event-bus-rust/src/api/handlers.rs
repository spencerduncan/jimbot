use axum::{
    extract::State,
    http::StatusCode,
    response::Json,
};
use tracing::{debug, error, info};

use crate::{
    api::models::{ApiResponse, BatchEventRequest, JsonEvent},
    proto::converter::json_to_proto_event,
    AppState,
};

/// Handle single event endpoint
pub async fn handle_single_event(
    State(state): State<AppState>,
    Json(event): Json<JsonEvent>,
) -> Result<Json<ApiResponse>, StatusCode> {
    debug!("Received single event: type={}, source={}", event.event_type, event.source);
    
    // Convert JSON to Protocol Buffer
    match json_to_proto_event(event) {
        Ok(proto_event) => {
            // Route the event
            if let Err(e) = state.router.route_event(proto_event).await {
                error!("Failed to route event: {}", e);
                return Ok(Json(ApiResponse::error(format!("Routing failed: {}", e))));
            }
            
            info!("Successfully processed single event");
            Ok(Json(ApiResponse::ok()))
        }
        Err(e) => {
            error!("Failed to convert JSON to protobuf: {}", e);
            Ok(Json(ApiResponse::error(format!("Invalid event format: {}", e))))
        }
    }
}

/// Handle batch events endpoint
pub async fn handle_batch_events(
    State(state): State<AppState>,
    Json(batch): Json<BatchEventRequest>,
) -> Result<Json<ApiResponse>, StatusCode> {
    let event_count = batch.events.len();
    info!("Received batch with {} events", event_count);
    
    let mut processed = 0;
    let mut errors = Vec::new();
    
    for (idx, event) in batch.events.into_iter().enumerate() {
        match json_to_proto_event(event) {
            Ok(proto_event) => {
                if let Err(e) = state.router.route_event(proto_event).await {
                    error!("Failed to route event {}: {}", idx, e);
                    errors.push(format!("Event {}: {}", idx, e));
                } else {
                    processed += 1;
                }
            }
            Err(e) => {
                error!("Failed to convert event {} to protobuf: {}", idx, e);
                errors.push(format!("Event {}: Invalid format - {}", idx, e));
            }
        }
    }
    
    if errors.is_empty() {
        info!("Successfully processed all {} events", processed);
        Ok(Json(ApiResponse::ok()))
    } else {
        let error_msg = format!(
            "Processed {}/{} events. Errors: {}",
            processed,
            event_count,
            errors.join(", ")
        );
        Ok(Json(ApiResponse::error(error_msg)))
    }
}