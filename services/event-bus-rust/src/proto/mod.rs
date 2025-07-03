pub mod converter;

// Include the generated protobuf code
pub mod jimbot {
    tonic::include_proto!("jimbot");
}

// Re-export commonly used types
pub use jimbot::*;

// gRPC service definitions
use tonic::{Request, Response, Status};

#[derive(Debug, Clone)]
pub struct PublishResponse {
    pub success: bool,
    pub message: String,
}

#[derive(Debug, Clone)]
pub struct SubscribeRequest {
    pub topic_pattern: String,
    pub subscriber_id: String,
}

// Custom trait for Event Bus gRPC service
#[tonic::async_trait]
pub trait EventBusGrpc: Send + Sync + 'static {
    async fn publish_event(
        &self,
        request: Request<Event>,
    ) -> Result<Response<PublishResponse>, Status>;

    async fn publish_batch(
        &self,
        request: Request<EventBatch>,
    ) -> Result<Response<PublishResponse>, Status>;

    async fn subscribe(
        &self,
        request: Request<SubscribeRequest>,
    ) -> Result<Response<tonic::Streaming<Event>>, Status>;
}