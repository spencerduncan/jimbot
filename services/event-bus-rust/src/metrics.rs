use lazy_static::lazy_static;
use metrics::{counter, gauge, histogram, register_counter, register_gauge, register_histogram, Unit};
use std::time::Instant;

lazy_static! {
    /// Total number of events received by type
    static ref EVENTS_RECEIVED: metrics::Counter = {
        register_counter!("event_bus_events_received_total", Unit::Count, "Total number of events received by type")
    };
    
    /// Total number of events processed successfully by type  
    static ref EVENTS_PROCESSED: metrics::Counter = {
        register_counter!("event_bus_events_processed_total", Unit::Count, "Total number of events processed successfully by type")
    };
    
    /// Total number of events failed by type and error
    static ref EVENTS_FAILED: metrics::Counter = {
        register_counter!("event_bus_events_failed_total", Unit::Count, "Total number of events failed by type and error")
    };
    
    /// Event processing latency histogram in milliseconds
    static ref PROCESSING_LATENCY: metrics::Histogram = {
        register_histogram!("event_bus_processing_latency_ms", Unit::Milliseconds, "Event processing latency in milliseconds")
    };
    
    /// Current number of active subscribers by topic pattern
    static ref ACTIVE_SUBSCRIBERS: metrics::Gauge = {
        register_gauge!("event_bus_active_subscribers", Unit::Count, "Current number of active subscribers by topic pattern")
    };
    
    /// Current queue depth by event type
    static ref QUEUE_DEPTH: metrics::Gauge = {
        register_gauge!("event_bus_queue_depth", Unit::Count, "Current queue depth by event type")
    };
    
    /// Number of events routed to subscribers
    static ref EVENTS_ROUTED: metrics::Counter = {
        register_counter!("event_bus_events_routed_total", Unit::Count, "Total number of events routed to subscribers")
    };
    
    /// Batch size histogram
    static ref BATCH_SIZE: metrics::Histogram = {
        register_histogram!("event_bus_batch_size", Unit::Count, "Batch size distribution")
    };
}

pub struct EventMetrics;

impl EventMetrics {
    /// Record that an event was received
    pub fn record_event_received(event_type: &str, source: &str) {
        counter!("event_bus_events_received_total", "event_type" => event_type.to_string(), "source" => source.to_string()).increment(1);
    }
    
    /// Record that an event was processed successfully
    pub fn record_event_processed(event_type: &str, topic: &str) {
        counter!("event_bus_events_processed_total", "event_type" => event_type.to_string(), "topic" => topic.to_string()).increment(1);
    }
    
    /// Record that an event failed processing
    pub fn record_event_failed(event_type: &str, error_type: &str) {
        counter!("event_bus_events_failed_total", "event_type" => event_type.to_string(), "error_type" => error_type.to_string()).increment(1);
    }
    
    /// Record event processing latency
    pub fn record_processing_latency(event_type: &str, latency_ms: f64) {
        histogram!("event_bus_processing_latency_ms", "event_type" => event_type.to_string()).record(latency_ms);
    }
    
    /// Update the number of active subscribers for a topic pattern
    pub fn update_active_subscribers(pattern: &str, count: f64) {
        gauge!("event_bus_active_subscribers", "pattern" => pattern.to_string()).set(count);
    }
    
    /// Update queue depth for an event type
    pub fn update_queue_depth(event_type: &str, depth: f64) {
        gauge!("event_bus_queue_depth", "event_type" => event_type.to_string()).set(depth);
    }
    
    /// Record that events were routed to subscribers
    pub fn record_events_routed(topic: &str, count: u64) {
        counter!("event_bus_events_routed_total", "topic" => topic.to_string()).increment(count);
    }
    
    /// Record batch size
    pub fn record_batch_size(size: f64) {
        histogram!("event_bus_batch_size").record(size);
    }
}

/// Timer for measuring event processing duration
pub struct ProcessingTimer {
    start: Instant,
    event_type: String,
}

impl ProcessingTimer {
    pub fn new(event_type: String) -> Self {
        Self {
            start: Instant::now(),
            event_type,
        }
    }
    
    pub fn finish(self) {
        let duration_ms = self.start.elapsed().as_millis() as f64;
        EventMetrics::record_processing_latency(&self.event_type, duration_ms);
    }
}

/// Initialize the metrics subsystem
pub fn init_metrics() {
    // Initialize Prometheus exporter
    let builder = metrics_exporter_prometheus::PrometheusBuilder::new();
    builder
        .with_http_listener(([0, 0, 0, 0], 9090))
        .install()
        .expect("Failed to install Prometheus exporter");
        
    tracing::info!("Metrics server listening on :9090/metrics");
}