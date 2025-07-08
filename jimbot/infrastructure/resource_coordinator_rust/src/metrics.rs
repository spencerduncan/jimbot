use metrics::{counter, gauge, histogram, Unit};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tokio::time::{interval, Duration};

/// Metrics collector for resource coordinator
pub struct MetricsCollector {
    /// Current resource utilization
    utilization: Arc<RwLock<HashMap<String, f64>>>,
    
    /// Allocation success/failure counts
    allocation_counts: Arc<RwLock<HashMap<String, u64>>>,
}

impl MetricsCollector {
    pub fn new() -> Self {
        // Register metrics
        metrics::describe_counter!(
            "resource_allocation_total",
            Unit::Count,
            "Total number of resource allocation attempts"
        );
        
        metrics::describe_counter!(
            "resource_allocation_success",
            Unit::Count,
            "Number of successful resource allocations"
        );
        
        metrics::describe_counter!(
            "resource_allocation_failure",
            Unit::Count,
            "Number of failed resource allocations"
        );
        
        metrics::describe_gauge!(
            "resource_utilization",
            Unit::Percent,
            "Current resource utilization percentage"
        );
        
        metrics::describe_histogram!(
            "resource_allocation_duration",
            Unit::Milliseconds,
            "Duration of resource allocations"
        );
        
        metrics::describe_gauge!(
            "resource_queue_depth",
            Unit::Count,
            "Number of pending resource requests"
        );
        
        Self {
            utilization: Arc::new(RwLock::new(HashMap::new())),
            allocation_counts: Arc::new(RwLock::new(HashMap::new())),
        }
    }
    
    /// Record a resource allocation attempt
    pub async fn record_allocation_attempt(&self, resource_type: &str, component: &str, success: bool) {
        let labels = [
            ("resource_type", resource_type.to_string()),
            ("component", component.to_string()),
        ];
        
        counter!("resource_allocation_total", &labels).increment(1);
        
        if success {
            counter!("resource_allocation_success", &labels).increment(1);
        } else {
            counter!("resource_allocation_failure", &labels).increment(1);
        }
        
        // Update internal counts
        let mut counts = self.allocation_counts.write().await;
        let key = format!("{}:{}", resource_type, if success { "success" } else { "failure" });
        *counts.entry(key).or_insert(0) += 1;
    }
    
    /// Record resource utilization
    pub async fn record_utilization(&self, resource_type: &str, utilization_percent: f64) {
        let labels = [("resource_type", resource_type.to_string())];
        gauge!("resource_utilization", &labels).set(utilization_percent);
        
        // Update internal state
        let mut util = self.utilization.write().await;
        util.insert(resource_type.to_string(), utilization_percent);
    }
    
    /// Record allocation duration
    pub fn record_allocation_duration(&self, resource_type: &str, duration_ms: f64) {
        let labels = [("resource_type", resource_type.to_string())];
        histogram!("resource_allocation_duration", &labels).record(duration_ms);
    }
    
    /// Record queue depth
    pub fn record_queue_depth(&self, resource_type: &str, depth: u64) {
        let labels = [("resource_type", resource_type.to_string())];
        gauge!("resource_queue_depth", &labels).set(depth as f64);
    }
    
    /// Get current utilization for all resources
    pub async fn get_utilization(&self) -> HashMap<String, f64> {
        self.utilization.read().await.clone()
    }
    
    /// Get allocation statistics
    pub async fn get_allocation_stats(&self) -> AllocationStats {
        let counts = self.allocation_counts.read().await;
        
        let mut stats = AllocationStats::default();
        
        for (key, count) in counts.iter() {
            let parts: Vec<&str> = key.split(':').collect();
            if parts.len() == 2 {
                let resource_type = parts[0];
                let status = parts[1];
                
                match status {
                    "success" => {
                        stats.success_by_type.insert(resource_type.to_string(), *count);
                        stats.total_success += count;
                    }
                    "failure" => {
                        stats.failure_by_type.insert(resource_type.to_string(), *count);
                        stats.total_failures += count;
                    }
                    _ => {}
                }
            }
        }
        
        stats
    }
    
    /// Start periodic metrics export
    pub fn start_export(&self, export_interval: Duration) {
        let utilization = self.utilization.clone();
        
        tokio::spawn(async move {
            let mut interval = interval(export_interval);
            
            loop {
                interval.tick().await;
                
                // Export current utilization
                let util = utilization.read().await;
                for (resource_type, percent) in util.iter() {
                    tracing::info!(
                        resource_type = resource_type,
                        utilization_percent = percent,
                        "Resource utilization"
                    );
                }
            }
        });
    }
}

/// Allocation statistics
#[derive(Debug, Default, Clone, serde::Serialize)]
pub struct AllocationStats {
    pub total_success: u64,
    pub total_failures: u64,
    pub success_by_type: HashMap<String, u64>,
    pub failure_by_type: HashMap<String, u64>,
}

impl AllocationStats {
    /// Get success rate
    pub fn success_rate(&self) -> f64 {
        let total = self.total_success + self.total_failures;
        if total == 0 {
            0.0
        } else {
            self.total_success as f64 / total as f64
        }
    }
    
    /// Get success rate for specific resource type
    pub fn success_rate_by_type(&self, resource_type: &str) -> f64 {
        let success = self.success_by_type.get(resource_type).unwrap_or(&0);
        let failure = self.failure_by_type.get(resource_type).unwrap_or(&0);
        let total = success + failure;
        
        if total == 0 {
            0.0
        } else {
            *success as f64 / total as f64
        }
    }
}

/// Helper to time resource allocation operations
pub struct AllocationTimer {
    resource_type: String,
    start_time: std::time::Instant,
}

impl AllocationTimer {
    pub fn new(resource_type: &str) -> Self {
        Self {
            resource_type: resource_type.to_string(),
            start_time: std::time::Instant::now(),
        }
    }
    
    pub fn record(self, collector: &MetricsCollector) {
        let duration_ms = self.start_time.elapsed().as_secs_f64() * 1000.0;
        collector.record_allocation_duration(&self.resource_type, duration_ms);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_metrics_recording() {
        let collector = MetricsCollector::new();
        
        // Record some allocations
        collector.record_allocation_attempt("gpu", "training", true).await;
        collector.record_allocation_attempt("gpu", "inference", false).await;
        collector.record_allocation_attempt("cpu", "analytics", true).await;
        
        // Check stats
        let stats = collector.get_allocation_stats().await;
        assert_eq!(stats.total_success, 2);
        assert_eq!(stats.total_failures, 1);
        assert_eq!(stats.success_rate(), 2.0 / 3.0);
    }
    
    #[tokio::test]
    async fn test_utilization_tracking() {
        let collector = MetricsCollector::new();
        
        // Record utilization
        collector.record_utilization("gpu", 0.75).await;
        collector.record_utilization("cpu", 0.5).await;
        collector.record_utilization("memory", 0.9).await;
        
        // Check utilization
        let util = collector.get_utilization().await;
        assert_eq!(util.get("gpu"), Some(&0.75));
        assert_eq!(util.get("cpu"), Some(&0.5));
        assert_eq!(util.get("memory"), Some(&0.9));
    }
    
    #[test]
    fn test_allocation_timer() {
        let collector = MetricsCollector::new();
        let timer = AllocationTimer::new("gpu");
        
        // Simulate some work
        std::thread::sleep(std::time::Duration::from_millis(10));
        
        // Record duration
        timer.record(&collector);
        // Note: We can't easily test the actual metric recording without a metrics backend
    }
}