use anyhow::{Context, Result};
use config::{Config, Environment, File};
use notify::{RecommendedWatcher, RecursiveMode, Watcher};
use serde::{Deserialize, Serialize};
use std::path::Path;
use std::sync::{Arc, RwLock};
use tokio::sync::mpsc;
use tracing::{error, info, warn};
use validator::{Validate, ValidationError};

/// Application configuration root
#[derive(Debug, Clone, Deserialize, Serialize, Validate)]
pub struct AppConfig {
    /// Server configuration
    #[validate(nested)]
    pub server: ServerConfig,
    
    /// Event routing configuration
    #[validate(nested)]
    pub routing: RoutingConfig,
    
    /// Logging configuration
    #[validate(nested)]
    pub logging: LoggingConfig,
    
    /// Metrics configuration
    #[validate(nested)]
    pub metrics: MetricsConfig,
    
    /// Security configuration
    #[validate(nested)]
    pub security: SecurityConfig,
    
    /// Environment name (dev, staging, prod)
    #[validate(length(min = 1))]
    pub environment: String,
}

/// Server configuration
#[derive(Debug, Clone, Deserialize, Serialize, Validate)]
pub struct ServerConfig {
    /// REST API configuration
    #[validate(nested)]
    pub rest: RestConfig,
    
    /// gRPC configuration
    #[validate(nested)]
    pub grpc: GrpcConfig,
    
    /// General server settings
    #[validate(range(min = 1, max = 10000))]
    pub worker_threads: Option<usize>,
    
    /// Graceful shutdown timeout in seconds
    #[validate(range(min = 1, max = 300))]
    pub shutdown_timeout_secs: u64,
}

/// REST API configuration
#[derive(Debug, Clone, Deserialize, Serialize, Validate)]
pub struct RestConfig {
    /// Host to bind to
    pub host: String,
    
    /// Port to bind to
    #[validate(range(min = 1, max = 65535))]
    pub port: u16,
    
    /// Request timeout in seconds
    #[validate(range(min = 1, max = 300))]
    pub request_timeout_secs: u64,
    
    /// Maximum request body size in bytes
    #[validate(range(min = 1024, max = 104857600))] // 1KB to 100MB
    pub max_body_size: usize,
    
    /// CORS configuration
    pub cors_enabled: bool,
    
    /// Allowed CORS origins
    pub cors_allowed_origins: Vec<String>,
}

/// gRPC configuration
#[derive(Debug, Clone, Deserialize, Serialize, Validate)]
pub struct GrpcConfig {
    /// Host to bind to
    pub host: String,
    
    /// Port to bind to
    #[validate(range(min = 1, max = 65535))]
    pub port: u16,
    
    /// Maximum message size in bytes
    #[validate(range(min = 1024, max = 104857600))] // 1KB to 100MB
    pub max_message_size: usize,
    
    /// Connection timeout in seconds
    #[validate(range(min = 1, max = 300))]
    pub connection_timeout_secs: u64,
    
    /// Enable reflection for debugging
    pub reflection_enabled: bool,
}

/// Event routing configuration
#[derive(Debug, Clone, Deserialize, Serialize, Validate)]
pub struct RoutingConfig {
    /// Event queue buffer size
    #[validate(range(min = 10, max = 100000))]
    pub event_buffer_size: usize,
    
    /// Maximum subscribers per topic
    #[validate(range(min = 1, max = 10000))]
    pub max_subscribers_per_topic: usize,
    
    /// Event TTL in seconds (0 = no expiry)
    #[validate(range(min = 0, max = 86400))] // Max 24 hours
    pub event_ttl_secs: u64,
    
    /// Dead letter queue settings
    pub dead_letter_enabled: bool,
    
    /// Maximum retry attempts for failed events
    #[validate(range(min = 0, max = 10))]
    pub max_retry_attempts: u32,
    
    /// Retry backoff configuration
    #[validate(nested)]
    pub retry_backoff: BackoffConfig,
}

/// Backoff configuration for retries
#[derive(Debug, Clone, Deserialize, Serialize, Validate)]
pub struct BackoffConfig {
    /// Initial backoff duration in milliseconds
    #[validate(range(min = 100, max = 60000))]
    pub initial_ms: u64,
    
    /// Maximum backoff duration in milliseconds
    #[validate(range(min = 1000, max = 300000))]
    pub max_ms: u64,
    
    /// Backoff multiplier
    #[validate(range(min = 1.0, max = 10.0))]
    pub multiplier: f64,
}

/// Logging configuration
#[derive(Debug, Clone, Deserialize, Serialize, Validate)]
pub struct LoggingConfig {
    /// Log level (trace, debug, info, warn, error)
    #[validate(length(min = 1))]
    pub level: String,
    
    /// Log format (json, pretty)
    #[validate(custom(function = "validate_log_format"))]
    pub format: String,
    
    /// Enable file logging
    pub file_enabled: bool,
    
    /// Log file path
    pub file_path: Option<String>,
    
    /// Log file rotation size in MB
    #[validate(range(min = 1, max = 1000))]
    pub rotation_size_mb: Option<u64>,
    
    /// Number of log files to keep
    #[validate(range(min = 1, max = 100))]
    pub rotation_keep: Option<u32>,
}

/// Metrics configuration
#[derive(Debug, Clone, Deserialize, Serialize, Validate)]
pub struct MetricsConfig {
    /// Enable metrics collection
    pub enabled: bool,
    
    /// Metrics export interval in seconds
    #[validate(range(min = 1, max = 300))]
    pub export_interval_secs: u64,
    
    /// Prometheus endpoint path
    pub prometheus_path: String,
}

/// Security configuration
#[derive(Debug, Clone, Deserialize, Serialize, Validate)]
pub struct SecurityConfig {
    /// Enable API authentication
    pub auth_enabled: bool,
    
    /// API key header name
    pub api_key_header: Option<String>,
    
    /// Rate limiting configuration
    #[validate(nested)]
    pub rate_limit: Option<RateLimitConfig>,
    
    /// TLS configuration
    #[validate(nested)]
    pub tls: Option<TlsConfig>,
}

/// Rate limiting configuration
#[derive(Debug, Clone, Deserialize, Serialize, Validate)]
pub struct RateLimitConfig {
    /// Requests per second
    #[validate(range(min = 1, max = 10000))]
    pub requests_per_second: u32,
    
    /// Burst size
    #[validate(range(min = 1, max = 100000))]
    pub burst_size: u32,
    
    /// Per-IP rate limiting
    pub per_ip_enabled: bool,
}

/// TLS configuration
#[derive(Debug, Clone, Deserialize, Serialize, Validate)]
pub struct TlsConfig {
    /// Certificate file path
    #[validate(length(min = 1))]
    pub cert_path: String,
    
    /// Private key file path
    #[validate(length(min = 1))]
    pub key_path: String,
    
    /// CA certificate path for mutual TLS
    pub ca_path: Option<String>,
    
    /// Enable mutual TLS
    pub mutual_tls: bool,
}

/// Validation helpers
fn validate_log_format(format: &str) -> Result<(), ValidationError> {
    match format {
        "json" | "pretty" => Ok(()),
        _ => Err(ValidationError::new("invalid_log_format")),
    }
}

/// Configuration manager with hot-reload support
pub struct ConfigManager {
    config: Arc<RwLock<AppConfig>>,
    watchers: Vec<RecommendedWatcher>,
}

impl ConfigManager {
    /// Load configuration from multiple sources
    pub fn load() -> Result<Self> {
        let environment = std::env::var("ENVIRONMENT").unwrap_or_else(|_| "dev".to_string());
        
        let config = Config::builder()
            // Start with default configuration
            .add_source(File::with_name("config/default").required(false))
            // Add environment-specific configuration
            .add_source(File::with_name(&format!("config/{}", environment)).required(false))
            // Add local configuration (not in version control)
            .add_source(File::with_name("config/local").required(false))
            // Override with environment variables
            // Environment variables use double underscore as separator
            // e.g., EVENT_BUS__SERVER__REST__PORT=8080
            .add_source(
                Environment::with_prefix("EVENT_BUS")
                    .separator("__")
                    .try_parsing(true),
            )
            .build()
            .context("Failed to build configuration")?;

        let app_config: AppConfig = config
            .try_deserialize()
            .context("Failed to deserialize configuration")?;
        
        // Validate configuration
        app_config
            .validate()
            .context("Configuration validation failed")?;
        
        info!("Configuration loaded for environment: {}", environment);
        
        Ok(Self {
            config: Arc::new(RwLock::new(app_config)),
            watchers: Vec::new(),
        })
    }
    
    /// Get current configuration
    pub fn get(&self) -> AppConfig {
        self.config.read().unwrap().clone()
    }
    
    /// Enable hot-reload for configuration files
    pub async fn enable_hot_reload(&mut self) -> Result<mpsc::Receiver<AppConfig>> {
        let (tx, rx) = mpsc::channel(10);
        let config = self.config.clone();
        
        // Watch configuration directory
        let (watch_tx, watch_rx) = std::sync::mpsc::channel();
        let mut watcher = notify::recommended_watcher(watch_tx)?;
        
        // Watch the config directory
        if Path::new("config").exists() {
            watcher.watch(Path::new("config"), RecursiveMode::NonRecursive)?;
            self.watchers.push(watcher);
        }
        
        // Spawn task to handle file changes
        tokio::spawn(async move {
            while let Ok(event) = watch_rx.recv() {
                match event {
                    Ok(notify::Event {
                        kind: notify::EventKind::Modify(_),
                        paths,
                        ..
                    }) => {
                        info!("Configuration file changed: {:?}", paths);
                        
                        // Reload configuration
                        match ConfigManager::load() {
                            Ok(new_manager) => {
                                let new_config = new_manager.get();
                                
                                // Validate new configuration
                                if let Err(e) = new_config.validate() {
                                    error!("Invalid configuration after reload: {}", e);
                                    continue;
                                }
                                
                                // Update configuration
                                *config.write().unwrap() = new_config.clone();
                                
                                // Notify subscribers
                                if tx.send(new_config).await.is_err() {
                                    warn!("Failed to send configuration update");
                                    break;
                                }
                                
                                info!("Configuration reloaded successfully");
                            }
                            Err(e) => {
                                error!("Failed to reload configuration: {}", e);
                            }
                        }
                    }
                    Err(e) => {
                        error!("Watch error: {}", e);
                    }
                    _ => {}
                }
            }
        });
        
        Ok(rx)
    }
}

/// Default configuration
impl Default for AppConfig {
    fn default() -> Self {
        Self {
            server: ServerConfig::default(),
            routing: RoutingConfig::default(),
            logging: LoggingConfig::default(),
            metrics: MetricsConfig::default(),
            security: SecurityConfig::default(),
            environment: "dev".to_string(),
        }
    }
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            rest: RestConfig::default(),
            grpc: GrpcConfig::default(),
            worker_threads: None,
            shutdown_timeout_secs: 30,
        }
    }
}

impl Default for RestConfig {
    fn default() -> Self {
        Self {
            host: "0.0.0.0".to_string(),
            port: 8080,
            request_timeout_secs: 30,
            max_body_size: 10 * 1024 * 1024, // 10MB
            cors_enabled: true,
            cors_allowed_origins: vec!["*".to_string()],
        }
    }
}

impl Default for GrpcConfig {
    fn default() -> Self {
        Self {
            host: "0.0.0.0".to_string(),
            port: 50051,
            max_message_size: 4 * 1024 * 1024, // 4MB
            connection_timeout_secs: 10,
            reflection_enabled: false,
        }
    }
}

impl Default for RoutingConfig {
    fn default() -> Self {
        Self {
            event_buffer_size: 1000,
            max_subscribers_per_topic: 100,
            event_ttl_secs: 0,
            dead_letter_enabled: false,
            max_retry_attempts: 3,
            retry_backoff: BackoffConfig::default(),
        }
    }
}

impl Default for BackoffConfig {
    fn default() -> Self {
        Self {
            initial_ms: 1000,
            max_ms: 30000,
            multiplier: 2.0,
        }
    }
}

impl Default for LoggingConfig {
    fn default() -> Self {
        Self {
            level: "info".to_string(),
            format: "json".to_string(),
            file_enabled: false,
            file_path: None,
            rotation_size_mb: Some(100),
            rotation_keep: Some(5),
        }
    }
}

impl Default for MetricsConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            export_interval_secs: 60,
            prometheus_path: "/metrics".to_string(),
        }
    }
}

impl Default for SecurityConfig {
    fn default() -> Self {
        Self {
            auth_enabled: false,
            api_key_header: Some("X-API-Key".to_string()),
            rate_limit: None,
            tls: None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_default_config_validation() {
        let config = AppConfig::default();
        assert!(config.validate().is_ok());
    }
    
    #[test]
    fn test_invalid_port() {
        let mut config = AppConfig::default();
        config.server.rest.port = 0;
        assert!(config.validate().is_err());
    }
    
    #[test]
    fn test_invalid_log_format() {
        let mut config = AppConfig::default();
        config.logging.format = "invalid".to_string();
        assert!(config.validate().is_err());
    }
}