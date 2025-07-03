use criterion::{black_box, criterion_group, criterion_main, Criterion, Throughput};
use event_bus_rust::proto::{Event, EventType};
use event_bus_rust::routing::EventRouter;
use std::sync::Arc;
use tokio::runtime::Runtime;

fn create_test_event() -> Event {
    Event {
        event_id: "test-123".to_string(),
        timestamp: 1704067200000,
        r#type: EventType::EventTypeGameState as i32,
        source: "benchmark".to_string(),
        version: 1,
        payload: None,
    }
}

fn benchmark_single_event_routing(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();
    let router = Arc::new(EventRouter::new());

    let mut group = c.benchmark_group("event_routing");
    group.throughput(Throughput::Elements(1));

    group.bench_function("single_event", |b| {
        b.to_async(&rt).iter(|| async {
            let event = create_test_event();
            router.route_event(black_box(event)).await.unwrap();
        });
    });

    group.finish();
}

fn benchmark_batch_event_routing(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();
    let router = Arc::new(EventRouter::new());

    let mut group = c.benchmark_group("batch_routing");

    for batch_size in [10, 100, 1000].iter() {
        group.throughput(Throughput::Elements(*batch_size as u64));
        group.bench_with_input(format!("batch_{}", batch_size), batch_size, |b, &size| {
            b.to_async(&rt).iter(|| async {
                for _ in 0..size {
                    let event = create_test_event();
                    router.route_event(black_box(event)).await.unwrap();
                }
            });
        });
    }

    group.finish();
}

fn benchmark_pattern_matching(c: &mut Criterion) {
    let router = EventRouter::new();

    c.bench_function("pattern_matching", |b| {
        b.iter(|| {
            let _matches = black_box(router.matches_pattern("game.state.update", "game.*.*"));
        });
    });
}

criterion_group!(
    benches,
    benchmark_single_event_routing,
    benchmark_batch_event_routing,
    benchmark_pattern_matching
);
criterion_main!(benches);
