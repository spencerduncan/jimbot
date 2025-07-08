use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use validator::{Validate, ValidationError};

/// Main configuration for the resource coordinator
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct ResourceCoordinatorConfig {
    /// Server configuration
    #[validate(nested)]
    pub server: ServerConfig,
    
    /// Resource pools configuration
    #[validate(nested)]
    pub resources: ResourceConfig,
    
    /// API rate limits configuration
    #[validate(nested)]
    pub api_limits: ApiLimitsConfig,
    
    /// Monitoring configuration
    #[validate(nested)]
    pub monitoring: MonitoringConfig,
}

/// Server configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct ServerConfig {
    /// Host to bind to
    #[validate(length(min = 1))]
    pub host: String,
    
    /// Port to bind to
    #[validate(range(min = 1, max = 65535))]
    pub port: u16,
    
    /// Max concurrent connections
    #[validate(range(min = 1, max = 10000))]
    pub max_connections: usize,
    
    /// Request timeout in seconds
    #[validate(range(min = 1, max = 300))]
    pub request_timeout_secs: u64,
}

/// Resource pools configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct ResourceConfig {
    /// Number of CPU cores available
    #[validate(range(min = 1, max = 256))]
    pub cpu_cores: u32,
    
    /// Memory pool size in MB
    #[validate(range(min = 128, max = 1048576))] // 128MB to 1TB
    pub memory_mb: u64,
    
    /// Number of GPUs available
    #[validate(range(min = 0, max = 8))]
    pub gpu_count: u8,
    
    /// Default allocation duration in seconds
    #[validate(range(min = 1, max = 86400))] // 1 second to 24 hours
    pub default_duration_secs: u64,
    
    /// Priority levels for different components
    pub component_priorities: HashMap<String, u8>,
}

/// API rate limits configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct ApiLimitsConfig {
    /// Claude API hourly limit
    #[validate(range(min = 1, max = 10000))]
    pub claude_hourly_limit: u32,
    
    /// QuestDB writes per second
    #[validate(range(min = 1, max = 100000))]
    pub questdb_writes_per_second: u32,
    
    /// EventStore writes per second
    #[validate(range(min = 1, max = 100000))]
    pub eventstore_writes_per_second: u32,
    
    /// Custom API limits
    pub custom_limits: HashMap<String, ApiLimit>,
}

/// Individual API limit configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct ApiLimit {
    /// Requests per time window
    #[validate(range(min = 1))]
    pub requests: u32,
    
    /// Time window in seconds
    #[validate(range(min = 1, max = 86400))]
    pub window_secs: u64,
    
    /// Burst capacity (optional)
    pub burst_capacity: Option<u32>,
}

/// Monitoring configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct MonitoringConfig {
    /// Enable metrics collection
    pub enabled: bool,
    
    /// Metrics export interval in seconds
    #[validate(range(min = 1, max = 3600))]
    pub export_interval_secs: u64,
    
    /// Prometheus metrics endpoint
    #[validate(length(min = 1))]
    pub prometheus_endpoint: String,
    
    /// OpenTelemetry configuration
    pub otel: Option<OtelConfig>,
}

/// OpenTelemetry configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct OtelConfig {
    /// OTLP endpoint
    #[validate(url)]
    pub endpoint: String,
    
    /// Service name
    #[validate(length(min = 1, max = 128))]
    pub service_name: String,
    
    /// Trace sample rate (0.0 to 1.0)
    #[validate(range(min = 0.0, max = 1.0))]
    pub sample_rate: f64,
}

impl Default for ResourceCoordinatorConfig {
    fn default() -> Self {
        Self {
            server: ServerConfig {
                host: "127.0.0.1".to_string(),
                port: 50052,
                max_connections: 100,
                request_timeout_secs: 30,
            },
            resources: ResourceConfig {
                cpu_cores: 4,
                memory_mb: 8192, // 8GB
                gpu_count: 1,
                default_duration_secs: 300, // 5 minutes
                component_priorities: HashMap::from([
                    ("training".to_string(), 200),
                    ("inference".to_string(), 150),
                    ("analytics".to_string(), 100),
                    ("claude".to_string(), 180),
                ]),
            },
            api_limits: ApiLimitsConfig {
                claude_hourly_limit: 100,
                questdb_writes_per_second: 10000,
                eventstore_writes_per_second: 5000,
                custom_limits: HashMap::new(),
            },
            monitoring: MonitoringConfig {
                enabled: true,
                export_interval_secs: 60,
                prometheus_endpoint: "/metrics".to_string(),
                otel: None,
            },
        }
    }
}

/// Load configuration from environment variables
pub fn from_env() -> ResourceCoordinatorConfig {
    let mut config = ResourceCoordinatorConfig::default();
    
    // Override from environment variables
    if let Ok(host) = std::env::var("RESOURCE_COORDINATOR_HOST") {
        config.server.host = host;
    }
    
    if let Ok(port) = std::env::var("RESOURCE_COORDINATOR_PORT") {
        if let Ok(port_num) = port.parse::<u16>() {
            config.server.port = port_num;
        }
    }
    
    if let Ok(cpu_cores) = std::env::var("RESOURCE_CPU_CORES") {
        if let Ok(cores) = cpu_cores.parse::<u32>() {
            config.resources.cpu_cores = cores;
        }
    }
    
    if let Ok(memory_mb) = std::env::var("RESOURCE_MEMORY_MB") {
        if let Ok(memory) = memory_mb.parse::<u64>() {
            config.resources.memory_mb = memory;
        }
    }
    
    if let Ok(gpu_count) = std::env::var("RESOURCE_GPU_COUNT") {
        if let Ok(gpus) = gpu_count.parse::<u8>() {
            config.resources.gpu_count = gpus;
        }
    }
    
    if let Ok(claude_limit) = std::env::var("CLAUDE_HOURLY_LIMIT") {
        if let Ok(limit) = claude_limit.parse::<u32>() {
            config.api_limits.claude_hourly_limit = limit;
        }
    }
    
    config
}

/// Validate configuration
pub fn validate_config(config: &ResourceCoordinatorConfig) -> Result<(), ValidationError> {
    config.validate().map_err(|_| ValidationError::new("validation_failed"))?;
    
    // Additional custom validation
    if config.resources.memory_mb < 1024 {
        return Err(ValidationError::new("insufficient_memory"));
    }
    
    if config.server.port < 1024 && config.server.port != 80 && config.server.port != 443 {
        return Err(ValidationError::new("privileged_port"));
    }
    
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_default_config() {
        let config = ResourceCoordinatorConfig::default();
        assert_eq!(config.server.host, "127.0.0.1");
        assert_eq!(config.server.port, 50052);
        assert_eq!(config.resources.cpu_cores, 4);
        assert_eq!(config.resources.memory_mb, 8192);
    }
    
    #[test]
    fn test_config_validation() {
        let mut config = ResourceCoordinatorConfig::default();
        
        // Valid config should pass
        assert!(config.validate().is_ok());
        
        // Invalid port
        config.server.port = 0;
        assert!(config.validate().is_err());
        config.server.port = 50052;
        
        // Invalid CPU cores
        config.resources.cpu_cores = 0;
        assert!(config.validate().is_err());
        config.resources.cpu_cores = 4;
        
        // Invalid memory
        config.resources.memory_mb = 0;
        assert!(config.validate().is_err());
    }
    
    #[test]
    fn test_env_override() {
        std::env::set_var("RESOURCE_COORDINATOR_HOST", "0.0.0.0");
        std::env::set_var("RESOURCE_COORDINATOR_PORT", "8080");
        std::env::set_var("RESOURCE_CPU_CORES", "8");
        
        let config = from_env();
        assert_eq!(config.server.host, "0.0.0.0");
        assert_eq!(config.server.port, 8080);
        assert_eq!(config.resources.cpu_cores, 8);
        
        // Clean up
        std::env::remove_var("RESOURCE_COORDINATOR_HOST");
        std::env::remove_var("RESOURCE_COORDINATOR_PORT");
        std::env::remove_var("RESOURCE_CPU_CORES");
    }
}