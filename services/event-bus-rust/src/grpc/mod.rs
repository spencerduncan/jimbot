use std::sync::Arc;
use tokio::sync::mpsc;
use tokio_stream::wrappers::UnboundedReceiverStream;
use tonic::{Request, Response, Status};
use tracing::{error, info};

use crate::{
    proto::{Event, EventBatch, EventBusGrpc, PublishResponse, SubscribeRequest},
    routing::EventRouter,
};

pub struct EventBusService {
    router: Arc<EventRouter>,
}

impl EventBusService {
    pub fn new(router: Arc<EventRouter>) -> Self {
        Self { router }
    }
}

#[tonic::async_trait]
impl EventBusGrpc for EventBusService {
    async fn publish_event(
        &self,
        request: Request<Event>,
    ) -> Result<Response<PublishResponse>, Status> {
        let event = request.into_inner();
        info!("gRPC: Received event from {}", event.source);

        match self.router.route_event(event).await {
            Ok(_) => Ok(Response::new(PublishResponse {
                success: true,
                message: "Event published successfully".to_string(),
            })),
            Err(e) => {
                error!("Failed to route event: {}", e);
                Ok(Response::new(PublishResponse {
                    success: false,
                    message: format!("Failed to route event: {}", e),
                }))
            }
        }
    }

    async fn publish_batch(
        &self,
        request: Request<EventBatch>,
    ) -> Result<Response<PublishResponse>, Status> {
        let batch = request.into_inner();
        let event_count = batch.events.len();
        info!(
            "gRPC: Received batch with {} events from {}",
            event_count, batch.source
        );

        let mut errors = Vec::new();
        for (idx, event) in batch.events.into_iter().enumerate() {
            if let Err(e) = self.router.route_event(event).await {
                errors.push(format!("Event {}: {}", idx, e));
            }
        }

        if errors.is_empty() {
            Ok(Response::new(PublishResponse {
                success: true,
                message: format!("All {} events published successfully", event_count),
            }))
        } else {
            Ok(Response::new(PublishResponse {
                success: false,
                message: format!("Failed to publish some events: {}", errors.join(", ")),
            }))
        }
    }

    async fn subscribe(
        &self,
        request: Request<SubscribeRequest>,
    ) -> Result<Response<tonic::Streaming<Event>>, Status> {
        let req = request.into_inner();
        info!(
            "gRPC: New subscription for pattern '{}' from subscriber '{}'",
            req.topic_pattern, req.subscriber_id
        );

        // Create channel for this subscriber
        let (tx, rx) = mpsc::unbounded_channel();

        // Register the channel with the router
        self.router.subscribe_channel(req.topic_pattern.clone(), tx);

        // Convert to streaming response
        let stream = UnboundedReceiverStream::new(rx);
        Ok(Response::new(Box::pin(stream) as tonic::Streaming<Event>))
    }
}
