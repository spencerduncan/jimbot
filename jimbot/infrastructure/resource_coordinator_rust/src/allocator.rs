use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::{Mutex, Semaphore};
use tokio::time::{Duration, Instant};
use tracing::{debug, info, warn};

/// Resource types that can be allocated
#[derive(Debug, Clone, Hash, Eq, PartialEq)]
pub enum ResourceType {
    Gpu,
    CpuCores(u32),
    Memory(u64), // in bytes
    ApiQuota(String), // API name
}

/// Allocation request from a component
#[derive(Debug, Clone)]
pub struct AllocationRequest {
    pub component_id: String,
    pub resource_type: ResourceType,
    pub duration: Duration,
    pub priority: u8, // 0 = lowest, 255 = highest
}

/// Represents an active allocation
#[derive(Debug, Clone)]
struct Allocation {
    component_id: String,
    resource_type: ResourceType,
    started_at: Instant,
    expires_at: Instant,
}

/// Resource allocator managing different resource types
pub struct ResourceAllocator {
    /// GPU semaphore (single GPU)
    gpu_semaphore: Arc<Semaphore>,
    
    /// CPU cores available
    cpu_cores: u32,
    cpu_allocations: Arc<Mutex<HashMap<String, u32>>>,
    
    /// Memory pool in bytes
    memory_pool: u64,
    memory_allocations: Arc<Mutex<HashMap<String, u64>>>,
    
    /// API rate limiters
    api_limiters: Arc<Mutex<HashMap<String, Arc<Semaphore>>>>,
    
    /// Active allocations tracking
    active_allocations: Arc<Mutex<Vec<Allocation>>>,
}

impl ResourceAllocator {
    pub fn new(cpu_cores: u32, memory_bytes: u64) -> Self {
        Self {
            gpu_semaphore: Arc::new(Semaphore::new(1)),
            cpu_cores,
            cpu_allocations: Arc::new(Mutex::new(HashMap::new())),
            memory_pool: memory_bytes,
            memory_allocations: Arc::new(Mutex::new(HashMap::new())),
            api_limiters: Arc::new(Mutex::new(HashMap::new())),
            active_allocations: Arc::new(Mutex::new(Vec::new())),
        }
    }
    
    /// Allocate a resource for a component
    pub async fn allocate(&self, request: AllocationRequest) -> Result<(), String> {
        // Clean up expired allocations first
        self.cleanup_expired_allocations().await;
        
        match request.resource_type.clone() {
            ResourceType::Gpu => self.allocate_gpu(request).await,
            ResourceType::CpuCores(cores) => self.allocate_cpu(request, cores).await,
            ResourceType::Memory(bytes) => self.allocate_memory(request, bytes).await,
            ResourceType::ApiQuota(api_name) => self.allocate_api_quota(request, &api_name).await,
        }
    }
    
    /// Release resources allocated to a component
    pub async fn release(&self, component_id: &str, resource_type: &ResourceType) -> Result<(), String> {
        match resource_type {
            ResourceType::Gpu => {
                // GPU is released automatically when permit is dropped
            }
            ResourceType::CpuCores(_) => {
                let mut allocations = self.cpu_allocations.lock().await;
                allocations.remove(component_id);
                info!("Released CPU cores for component: {}", component_id);
            }
            ResourceType::Memory(_) => {
                let mut allocations = self.memory_allocations.lock().await;
                allocations.remove(component_id);
                info!("Released memory for component: {}", component_id);
            }
            ResourceType::ApiQuota(_) => {
                // API quota is managed by rate limiter
            }
        }
        
        // Remove from active allocations
        let mut active = self.active_allocations.lock().await;
        active.retain(|alloc| alloc.component_id != component_id);
        
        Ok(())
    }
    
    /// Get current resource usage statistics
    pub async fn get_usage_stats(&self) -> HashMap<String, f64> {
        let mut stats = HashMap::new();
        
        // GPU usage (0 or 1)
        let gpu_available = self.gpu_semaphore.available_permits();
        stats.insert("gpu_usage".to_string(), if gpu_available > 0 { 0.0 } else { 1.0 });
        
        // CPU usage
        let cpu_allocations = self.cpu_allocations.lock().await;
        let used_cores: u32 = cpu_allocations.values().sum();
        stats.insert("cpu_usage".to_string(), used_cores as f64 / self.cpu_cores as f64);
        
        // Memory usage
        let memory_allocations = self.memory_allocations.lock().await;
        let used_memory: u64 = memory_allocations.values().sum();
        stats.insert("memory_usage".to_string(), used_memory as f64 / self.memory_pool as f64);
        
        stats
    }
    
    async fn allocate_gpu(&self, request: AllocationRequest) -> Result<(), String> {
        let permit = self.gpu_semaphore
            .clone()
            .try_acquire_owned()
            .map_err(|_| "GPU not available".to_string())?;
        
        info!("Allocated GPU to component: {}", request.component_id);
        
        // Track allocation
        let allocation = Allocation {
            component_id: request.component_id.clone(),
            resource_type: request.resource_type,
            started_at: Instant::now(),
            expires_at: Instant::now() + request.duration,
        };
        
        let mut active = self.active_allocations.lock().await;
        active.push(allocation);
        
        // Spawn task to hold permit for duration
        let component_id = request.component_id.clone();
        let duration = request.duration;
        let active_allocations = self.active_allocations.clone();
        
        tokio::spawn(async move {
            tokio::time::sleep(duration).await;
            drop(permit); // Release GPU
            
            // Remove from active allocations
            let mut active = active_allocations.lock().await;
            active.retain(|alloc| alloc.component_id != component_id);
            
            info!("GPU allocation expired for component: {}", component_id);
        });
        
        Ok(())
    }
    
    async fn allocate_cpu(&self, request: AllocationRequest, cores: u32) -> Result<(), String> {
        let mut allocations = self.cpu_allocations.lock().await;
        
        // Check if enough cores available
        let used_cores: u32 = allocations.values().sum();
        if used_cores + cores > self.cpu_cores {
            return Err(format!("Not enough CPU cores available. Requested: {}, Available: {}", 
                cores, self.cpu_cores - used_cores));
        }
        
        allocations.insert(request.component_id.clone(), cores);
        info!("Allocated {} CPU cores to component: {}", cores, request.component_id);
        
        // Track allocation
        let allocation = Allocation {
            component_id: request.component_id.clone(),
            resource_type: request.resource_type,
            started_at: Instant::now(),
            expires_at: Instant::now() + request.duration,
        };
        
        let mut active = self.active_allocations.lock().await;
        active.push(allocation);
        
        Ok(())
    }
    
    async fn allocate_memory(&self, request: AllocationRequest, bytes: u64) -> Result<(), String> {
        let mut allocations = self.memory_allocations.lock().await;
        
        // Check if enough memory available
        let used_memory: u64 = allocations.values().sum();
        if used_memory + bytes > self.memory_pool {
            return Err(format!("Not enough memory available. Requested: {} bytes, Available: {} bytes", 
                bytes, self.memory_pool - used_memory));
        }
        
        allocations.insert(request.component_id.clone(), bytes);
        info!("Allocated {} bytes to component: {}", bytes, request.component_id);
        
        // Track allocation
        let allocation = Allocation {
            component_id: request.component_id.clone(),
            resource_type: request.resource_type,
            started_at: Instant::now(),
            expires_at: Instant::now() + request.duration,
        };
        
        let mut active = self.active_allocations.lock().await;
        active.push(allocation);
        
        Ok(())
    }
    
    async fn allocate_api_quota(&self, request: AllocationRequest, api_name: &str) -> Result<(), String> {
        let mut limiters = self.api_limiters.lock().await;
        
        // Get or create rate limiter for this API
        let limiter = limiters.entry(api_name.to_string())
            .or_insert_with(|| {
                // Default to 100 requests per hour
                Arc::new(Semaphore::new(100))
            });
        
        let permit = limiter
            .clone()
            .try_acquire_owned()
            .map_err(|_| format!("API quota exhausted for: {}", api_name))?;
        
        info!("Allocated API quota for {} to component: {}", api_name, request.component_id);
        
        // Hold permit for duration
        tokio::spawn(async move {
            tokio::time::sleep(Duration::from_secs(3600)).await; // 1 hour
            drop(permit);
        });
        
        Ok(())
    }
    
    async fn cleanup_expired_allocations(&self) {
        let mut active = self.active_allocations.lock().await;
        let now = Instant::now();
        
        // Find expired allocations
        let expired: Vec<_> = active
            .iter()
            .filter(|alloc| alloc.expires_at <= now)
            .cloned()
            .collect();
        
        // Release expired resources
        for alloc in expired {
            debug!("Cleaning up expired allocation for component: {}", alloc.component_id);
            let _ = self.release(&alloc.component_id, &alloc.resource_type).await;
        }
        
        // Remove expired from active list
        active.retain(|alloc| alloc.expires_at > now);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_gpu_allocation() {
        let allocator = ResourceAllocator::new(4, 1024 * 1024 * 1024); // 1GB
        
        let request = AllocationRequest {
            component_id: "test_component".to_string(),
            resource_type: ResourceType::Gpu,
            duration: Duration::from_secs(1),
            priority: 100,
        };
        
        // First allocation should succeed
        assert!(allocator.allocate(request.clone()).await.is_ok());
        
        // Second allocation should fail (only 1 GPU)
        assert!(allocator.allocate(request).await.is_err());
        
        // Wait for first allocation to expire
        tokio::time::sleep(Duration::from_secs(2)).await;
        
        // Now allocation should succeed again
        let request2 = AllocationRequest {
            component_id: "test_component2".to_string(),
            resource_type: ResourceType::Gpu,
            duration: Duration::from_secs(1),
            priority: 100,
        };
        assert!(allocator.allocate(request2).await.is_ok());
    }
    
    #[tokio::test]
    async fn test_cpu_allocation() {
        let allocator = ResourceAllocator::new(4, 1024 * 1024 * 1024);
        
        let request1 = AllocationRequest {
            component_id: "component1".to_string(),
            resource_type: ResourceType::CpuCores(2),
            duration: Duration::from_secs(10),
            priority: 100,
        };
        
        let request2 = AllocationRequest {
            component_id: "component2".to_string(),
            resource_type: ResourceType::CpuCores(2),
            duration: Duration::from_secs(10),
            priority: 100,
        };
        
        let request3 = AllocationRequest {
            component_id: "component3".to_string(),
            resource_type: ResourceType::CpuCores(1),
            duration: Duration::from_secs(10),
            priority: 100,
        };
        
        // Should allocate 2 + 2 cores successfully
        assert!(allocator.allocate(request1).await.is_ok());
        assert!(allocator.allocate(request2).await.is_ok());
        
        // Should fail to allocate 1 more (only 4 total)
        assert!(allocator.allocate(request3).await.is_err());
    }
}