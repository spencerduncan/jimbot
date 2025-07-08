use resource_coordinator::{config_from_env, start_server};
use tracing::info;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize tracing
    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("info,resource_coordinator=debug"));
    
    tracing_subscriber::registry()
        .with(tracing_subscriber::fmt::layer())
        .with(filter)
        .init();
    
    info!("Starting Resource Coordinator");
    
    // Load configuration
    let config = config_from_env();
    
    // Validate configuration
    if let Err(e) = resource_coordinator::config::validate_config(&config) {
        eprintln!("Configuration validation failed: {}", e);
        std::process::exit(1);
    }
    
    info!(
        "Configuration loaded: {} CPUs, {} MB memory, {} GPUs",
        config.resources.cpu_cores,
        config.resources.memory_mb,
        config.resources.gpu_count
    );
    
    // Start the server
    start_server(config).await?;
    
    Ok(())
}