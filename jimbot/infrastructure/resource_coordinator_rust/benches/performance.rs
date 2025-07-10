use criterion::{black_box, criterion_group, criterion_main, Criterion};
use std::sync::Arc;
use std::time::Duration;
use tokio::runtime::Runtime;

use resource_coordinator::{
    allocator::{AllocationRequest, Priority, ResourceAllocator, ResourceType},
    config::Config,
    metrics::MetricsRegistry,
    rate_limiter::ClaudeRateLimiter,
};

fn benchmark_gpu_allocation(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();
    let config = Arc::new(Config::default());
    let metrics = Arc::new(MetricsRegistry::new());
    let allocator = Arc::new(ResourceAllocator::new(config, metrics));

    c.bench_function("gpu_allocation", |b| {
        b.to_async(&rt).iter(|| async {
            let request = AllocationRequest {
                request_id: "bench-1".to_string(),
                component: "benchmark".to_string(),
                resource_type: ResourceType::Gpu,
                quantity: 1,
                priority: Priority::Normal,
                timeout: Duration::from_secs(5),
                duration: Duration::from_secs(60),
            };

            let result = allocator.request_allocation(request).await;
            black_box(result)
        })
    });
}

fn benchmark_memory_allocation(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();
    let config = Arc::new(Config::default());
    let metrics = Arc::new(MetricsRegistry::new());
    let allocator = Arc::new(ResourceAllocator::new(config, metrics));

    c.bench_function("memory_allocation_1gb", |b| {
        b.to_async(&rt).iter(|| async {
            let request = AllocationRequest {
                request_id: "bench-mem-1".to_string(),
                component: "benchmark".to_string(),
                resource_type: ResourceType::Memory,
                quantity: 1024, // 1GB
                priority: Priority::Normal,
                timeout: Duration::from_secs(5),
                duration: Duration::from_secs(60),
            };

            let result = allocator.request_allocation(request).await;
            if let Ok((token, _)) = &result {
                // Clean up
                let _ = allocator.release_allocation(token, "benchmark").await;
            }
            black_box(result)
        })
    });
}

fn benchmark_rate_limiter(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();
    let config = Arc::new(Config::default());
    let metrics = Arc::new(MetricsRegistry::new());
    let rate_limiter = Arc::new(ClaudeRateLimiter::new(config, metrics));

    c.bench_function("claude_rate_limit_check", |b| {
        b.to_async(&rt).iter(|| async {
            let result = rate_limiter.acquire("benchmark").await;
            black_box(result)
        })
    });
}

fn benchmark_concurrent_allocations(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();
    let config = Arc::new(Config::default());
    let metrics = Arc::new(MetricsRegistry::new());
    let allocator = Arc::new(ResourceAllocator::new(config, metrics));

    c.bench_function("concurrent_memory_allocations_10", |b| {
        b.to_async(&rt).iter(|| async {
            let handles: Vec<_> = (0..10)
                .map(|i| {
                    let allocator = allocator.clone();
                    tokio::spawn(async move {
                        let request = AllocationRequest {
                            request_id: format!("bench-concurrent-{}", i),
                            component: "benchmark".to_string(),
                            resource_type: ResourceType::Memory,
                            quantity: 512, // 512MB each
                            priority: Priority::Normal,
                            timeout: Duration::from_secs(5),
                            duration: Duration::from_secs(10),
                        };

                        allocator.request_allocation(request).await
                    })
                })
                .collect();

            // Wait for all allocations
            let results = futures::future::join_all(handles).await;

            // Clean up
            for (i, result) in results.iter().enumerate() {
                if let Ok(Ok((token, _))) = result {
                    let _ = allocator.release_allocation(token, "benchmark").await;
                }
            }

            black_box(results)
        })
    });
}

fn benchmark_resource_status(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();
    let config = Arc::new(Config::default());
    let metrics = Arc::new(MetricsRegistry::new());
    let allocator = Arc::new(ResourceAllocator::new(config, metrics));

    c.bench_function("get_resource_status", |b| {
        b.iter(|| {
            let gpu_status = allocator.get_gpu_status();
            let memory_status = allocator.get_memory_status();
            black_box((gpu_status, memory_status))
        })
    });
}

criterion_group!(
    benches,
    benchmark_gpu_allocation,
    benchmark_memory_allocation,
    benchmark_rate_limiter,
    benchmark_concurrent_allocations,
    benchmark_resource_status
);

criterion_main!(benches);
