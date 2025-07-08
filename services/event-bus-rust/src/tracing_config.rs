use opentelemetry::propagation::TextMapPropagator;
use opentelemetry::global;
use opentelemetry_otlp::WithExportConfig;
use opentelemetry_sdk::propagation::TraceContextPropagator;
use opentelemetry_sdk::{trace as sdktrace, Resource};
use std::time::Duration;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

/// Initialize OpenTelemetry tracing
pub fn init_tracing() -> Result<sdktrace::SdkTracerProvider, Box<dyn std::error::Error>> {
    // Create OTLP exporter
    let otlp_endpoint = std::env::var("OTEL_EXPORTER_OTLP_ENDPOINT")
        .unwrap_or_else(|_| "http://localhost:4317".to_string());

    let exporter = opentelemetry_otlp::SpanExporter::builder()
        .with_tonic()
        .with_endpoint(otlp_endpoint)
        .with_timeout(Duration::from_secs(3))
        .build()?;

    // Create resource with service information
    let resource = Resource::builder()
        .with_service_name("event-bus-rust")
        .build();

    // Create trace provider with service information
    let tracer_provider = sdktrace::SdkTracerProvider::builder()
        .with_batch_exporter(exporter)
        .with_resource(resource)
        .build();

    // Set global tracer provider
    global::set_tracer_provider(tracer_provider.clone());

    // Configure tracing subscriber with OpenTelemetry layer
    // TODO: Fix opentelemetry version mismatch
    // let telemetry_layer = tracing_opentelemetry::layer().with_tracer(tracer_provider.tracer("event-bus-rust"));

    let fmt_layer = tracing_subscriber::fmt::layer()
        .json()
        .with_target(true)
        .with_thread_ids(true)
        .with_thread_names(true);

    let filter_layer = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| "event_bus_rust=debug,tower_http=debug".into());

    tracing_subscriber::registry()
        .with(filter_layer)
        .with(fmt_layer)
        // .with(telemetry_layer)
        .init();

    Ok(tracer_provider)
}

/// Extract trace context from incoming event headers
#[allow(dead_code)]
pub fn extract_trace_context(
    headers: &std::collections::HashMap<String, String>,
) -> opentelemetry::Context {
    let mut carrier = std::collections::HashMap::new();

    // Copy relevant trace headers
    if let Some(traceparent) = headers.get("traceparent") {
        carrier.insert("traceparent".to_string(), traceparent.clone());
    }
    if let Some(tracestate) = headers.get("tracestate") {
        carrier.insert("tracestate".to_string(), tracestate.clone());
    }

    // Extract context using W3C Trace Context propagator
    let propagator = TraceContextPropagator::new();
    let extractor = HeaderExtractor(&carrier);
    propagator.extract(&extractor)
}

/// Inject trace context into outgoing event headers
#[allow(dead_code)]
pub fn inject_trace_context(
    context: &opentelemetry::Context,
    headers: &mut std::collections::HashMap<String, String>,
) {
    let propagator = TraceContextPropagator::new();
    let mut injector = HeaderInjector(headers);
    propagator.inject_context(context, &mut injector);
}

/// Helper struct for extracting headers
#[allow(dead_code)]
struct HeaderExtractor<'a>(&'a std::collections::HashMap<String, String>);

impl<'a> opentelemetry::propagation::Extractor for HeaderExtractor<'a> {
    fn get(&self, key: &str) -> Option<&str> {
        self.0.get(key).map(|v| v.as_str())
    }

    fn keys(&self) -> Vec<&str> {
        self.0.keys().map(|k| k.as_str()).collect()
    }
}

/// Helper struct for injecting headers
#[allow(dead_code)]
struct HeaderInjector<'a>(&'a mut std::collections::HashMap<String, String>);

impl<'a> opentelemetry::propagation::Injector for HeaderInjector<'a> {
    fn set(&mut self, key: &str, value: String) {
        self.0.insert(key.to_string(), value);
    }
}

/// Shutdown OpenTelemetry providers
pub fn shutdown_tracing(tracer_provider: sdktrace::SdkTracerProvider) -> Result<(), Box<dyn std::error::Error>> {
    tracer_provider.shutdown()?;
    Ok(())
}
