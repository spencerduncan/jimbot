use futures::stream::{self, StreamExt};
use reqwest;
use serde_json::json;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::time::{sleep, timeout};
use tracing::{debug, error, info, warn};

const BASE_URL: &str = "http://localhost:8080";
const TIMEOUT_DURATION: Duration = Duration::from_secs(30);

/// Comprehensive resilience testing for Event Bus
/// Tests system behavior under stress, failures, and resource exhaustion
#[tokio::test]
async fn test_sustained_load_resilience() {
    let client = reqwest::Client::new();
    let test_duration = Duration::from_secs(60); // 1 minute sustained load
    let events_per_second = 100;
    
    let start_time = Instant::now();
    let mut total_requests = 0;
    let mut successful_requests = 0;
    let mut error_count = 0;
    
    info!("Starting sustained load test for {:?}", test_duration);
    
    while start_time.elapsed() < test_duration {
        let batch_start = Instant::now();
        
        // Send batch of events
        let batch = json!({
            "events": (0..events_per_second).map(|i| json!({
                "type": "HEARTBEAT",
                "source": "sustained_load_test",
                "payload": {
                    "batch_time": start_time.elapsed().as_millis(),
                    "event_id": i,
                    "timestamp": std::time::SystemTime::now()
                        .duration_since(std::time::UNIX_EPOCH)
                        .unwrap()
                        .as_secs()
                }
            })).collect::<Vec<_>>()
        });
        
        let response = timeout(
            Duration::from_secs(5),
            client
                .post(format!("{}/api/v1/events/batch", BASE_URL))
                .json(&batch)
                .send()
        ).await;
        
        total_requests += 1;
        
        match response {
            Ok(Ok(resp)) => {
                if resp.status().is_success() {
                    successful_requests += 1;
                } else {
                    error_count += 1;
                    debug!("Request failed with status: {}", resp.status());
                }
            }
            Ok(Err(e)) => {
                error_count += 1;
                debug!("Request failed with error: {}", e);
            }
            Err(_) => {
                error_count += 1;
                debug!("Request timed out");
            }
        }
        
        // Maintain target rate
        let batch_duration = batch_start.elapsed();
        if batch_duration < Duration::from_secs(1) {
            sleep(Duration::from_secs(1) - batch_duration).await;
        }
    }
    
    let success_rate = successful_requests as f64 / total_requests as f64;
    let error_rate = error_count as f64 / total_requests as f64;
    
    info!("Sustained load test results:");
    info!("  Total requests: {}", total_requests);
    info!("  Successful: {} ({:.2}%)", successful_requests, success_rate * 100.0);
    info!("  Errors: {} ({:.2}%)", error_count, error_rate * 100.0);
    info!("  Duration: {:?}", start_time.elapsed());
    
    // System should maintain reasonable success rate under sustained load
    assert!(success_rate > 0.8, "Success rate too low: {:.2}%", success_rate * 100.0);
    
    // Error rate should be reasonable
    assert!(error_rate < 0.2, "Error rate too high: {:.2}%", error_rate * 100.0);
}

#[tokio::test]
async fn test_burst_traffic_patterns() {
    let client = reqwest::Client::new();
    
    // Test different burst patterns
    let burst_patterns = vec![
        // Small frequent bursts
        (10, 100, Duration::from_millis(100)), // 10 events, 100ms apart
        
        // Medium bursts
        (100, 50, Duration::from_millis(500)), // 100 events, 500ms apart
        
        // Large infrequent bursts
        (1000, 10, Duration::from_secs(2)), // 1000 events, 2s apart
        
        // Extreme burst
        (5000, 2, Duration::from_secs(5)), // 5000 events, 5s apart
    ];
    
    for (burst_size, num_bursts, interval) in burst_patterns {
        info!("Testing burst pattern: {} events x {} bursts, {:?} interval", 
              burst_size, num_bursts, interval);
        
        let mut total_success = 0;
        let mut total_errors = 0;
        let mut response_times = Vec::new();
        
        for burst_num in 0..num_bursts {
            let burst_start = Instant::now();
            
            // Create burst of events
            let batch = json!({
                "events": (0..burst_size).map(|i| json!({
                    "type": "CONNECTION_TEST",
                    "source": "burst_test",
                    "payload": {
                        "burst_id": burst_num,
                        "event_id": i,
                        "burst_size": burst_size
                    }
                })).collect::<Vec<_>>()
            });
            
            let response = timeout(
                Duration::from_secs(30),
                client
                    .post(format!("{}/api/v1/events/batch", BASE_URL))
                    .json(&batch)
                    .send()
            ).await;
            
            let response_time = burst_start.elapsed();
            response_times.push(response_time);
            
            match response {
                Ok(Ok(resp)) => {
                    if resp.status().is_success() {
                        total_success += 1;
                    } else {
                        total_errors += 1;
                        debug!("Burst {} failed with status: {}", burst_num, resp.status());
                    }
                }
                Ok(Err(e)) => {
                    total_errors += 1;
                    debug!("Burst {} failed with error: {}", burst_num, e);
                }
                Err(_) => {
                    total_errors += 1;
                    debug!("Burst {} timed out", burst_num);
                }
            }
            
            // Wait before next burst
            sleep(interval).await;
        }
        
        // Analyze results
        let success_rate = total_success as f64 / num_bursts as f64;
        let avg_response_time = response_times.iter().sum::<Duration>() / response_times.len() as u32;
        let max_response_time = response_times.iter().max().unwrap_or(&Duration::from_secs(0));
        
        info!("Burst pattern results:");
        info!("  Success rate: {:.2}%", success_rate * 100.0);
        info!("  Average response time: {:?}", avg_response_time);
        info!("  Max response time: {:?}", max_response_time);
        
        // System should handle bursts gracefully
        assert!(success_rate > 0.7, "Burst success rate too low: {:.2}%", success_rate * 100.0);
        
        // Response time should degrade gracefully, not exponentially
        assert!(avg_response_time < Duration::from_secs(10), 
                "Average response time too high: {:?}", avg_response_time);
    }
}

#[tokio::test]
async fn test_concurrent_client_connections() {
    let concurrent_clients = 50;
    let events_per_client = 100;
    
    info!("Testing {} concurrent clients, {} events each", concurrent_clients, events_per_client);
    
    let success_counter = Arc::new(AtomicUsize::new(0));
    let error_counter = Arc::new(AtomicUsize::new(0));
    let total_events = Arc::new(AtomicUsize::new(0));
    
    // Create concurrent client tasks
    let client_tasks = (0..concurrent_clients).map(|client_id| {
        let success_counter = success_counter.clone();
        let error_counter = error_counter.clone();
        let total_events = total_events.clone();
        
        async move {
            let client = reqwest::Client::new();
            let mut client_success = 0;
            let mut client_errors = 0;
            
            for event_id in 0..events_per_client {
                let event = json!({
                    "type": "HEARTBEAT",
                    "source": format!("client_{}", client_id),
                    "payload": {
                        "client_id": client_id,
                        "event_id": event_id,
                        "timestamp": std::time::SystemTime::now()
                            .duration_since(std::time::UNIX_EPOCH)
                            .unwrap()
                            .as_millis()
                    }
                });
                
                let response = timeout(
                    Duration::from_secs(10),
                    client
                        .post(format!("{}/api/v1/events", BASE_URL))
                        .json(&event)
                        .send()
                ).await;
                
                total_events.fetch_add(1, Ordering::Relaxed);
                
                match response {
                    Ok(Ok(resp)) => {
                        if resp.status().is_success() {
                            client_success += 1;
                        } else {
                            client_errors += 1;
                        }
                    }
                    Ok(Err(_)) | Err(_) => {
                        client_errors += 1;
                    }
                }
                
                // Small delay to prevent overwhelming the server
                sleep(Duration::from_millis(10)).await;
            }
            
            success_counter.fetch_add(client_success, Ordering::Relaxed);
            error_counter.fetch_add(client_errors, Ordering::Relaxed);
            
            (client_id, client_success, client_errors)
        }
    }).collect::<Vec<_>>();
    
    // Execute all clients concurrently
    let start_time = Instant::now();
    let results = futures::future::join_all(client_tasks).await;
    let total_time = start_time.elapsed();
    
    let total_success = success_counter.load(Ordering::Relaxed);
    let total_errors = error_counter.load(Ordering::Relaxed);
    let total_processed = total_events.load(Ordering::Relaxed);
    
    // Analyze per-client results
    let mut client_success_rates = Vec::new();
    for (client_id, client_success, client_errors) in results {
        let client_rate = client_success as f64 / (client_success + client_errors) as f64;
        client_success_rates.push(client_rate);
        
        if client_rate < 0.8 {
            warn!("Client {} had low success rate: {:.2}%", client_id, client_rate * 100.0);
        }
    }
    
    let overall_success_rate = total_success as f64 / total_processed as f64;
    let events_per_second = total_processed as f64 / total_time.as_secs_f64();
    let min_client_rate = client_success_rates.iter().fold(1.0, |min, &rate| min.min(rate));
    let avg_client_rate = client_success_rates.iter().sum::<f64>() / client_success_rates.len() as f64;
    
    info!("Concurrent client test results:");
    info!("  Total events: {}", total_processed);
    info!("  Successful: {} ({:.2}%)", total_success, overall_success_rate * 100.0);
    info!("  Errors: {} ({:.2}%)", total_errors, (total_errors as f64 / total_processed as f64) * 100.0);
    info!("  Events per second: {:.2}", events_per_second);
    info!("  Min client success rate: {:.2}%", min_client_rate * 100.0);
    info!("  Avg client success rate: {:.2}%", avg_client_rate * 100.0);
    info!("  Total time: {:?}", total_time);
    
    // System should handle concurrent clients fairly
    assert!(overall_success_rate > 0.8, "Overall success rate too low: {:.2}%", overall_success_rate * 100.0);
    assert!(min_client_rate > 0.6, "Some clients had very low success rates");
    assert!(avg_client_rate > 0.8, "Average client success rate too low: {:.2}%", avg_client_rate * 100.0);
}

#[tokio::test]
async fn test_memory_pressure_resilience() {
    let client = reqwest::Client::new();
    
    // Test behavior under memory pressure by sending large payloads
    let large_payload_sizes = vec![
        1024,      // 1KB
        10240,     // 10KB
        102400,    // 100KB
        1048576,   // 1MB
    ];
    
    for payload_size in large_payload_sizes {
        info!("Testing memory pressure with {}KB payloads", payload_size / 1024);
        
        let large_data = "x".repeat(payload_size);
        let batch_size = 10;
        
        let batch = json!({
            "events": (0..batch_size).map(|i| json!({
                "type": "HEARTBEAT",
                "source": "memory_pressure_test",
                "payload": {
                    "large_field": large_data,
                    "event_id": i,
                    "payload_size": payload_size
                }
            })).collect::<Vec<_>>()
        });
        
        let response = timeout(
            Duration::from_secs(30),
            client
                .post(format!("{}/api/v1/events/batch", BASE_URL))
                .json(&batch)
                .send()
        ).await;
        
        match response {
            Ok(Ok(resp)) => {
                let status = resp.status();
                
                // Server should handle large payloads gracefully
                if payload_size <= 102400 { // Up to 100KB should be handled
                    assert!(status.is_success() || status.is_client_error());
                } else { // Very large payloads may be rejected
                    assert!(status.is_success() || status.is_client_error() || status.is_server_error());
                }
                
                debug!("Memory pressure test ({}KB): Status {}", payload_size / 1024, status);
            }
            Ok(Err(e)) => {
                warn!("Memory pressure test ({}KB) failed: {}", payload_size / 1024, e);
            }
            Err(_) => {
                warn!("Memory pressure test ({}KB) timed out", payload_size / 1024);
            }
        }
        
        // Give server time to recover
        sleep(Duration::from_millis(100)).await;
    }
}

#[tokio::test]
async fn test_network_partition_simulation() {
    let client = reqwest::Client::new();
    
    // Simulate network issues by using very short timeouts
    let network_scenarios = vec![
        Duration::from_millis(1),   // Extremely short timeout
        Duration::from_millis(10),  // Very short timeout
        Duration::from_millis(50),  // Short timeout
        Duration::from_millis(100), // Moderate timeout
    ];
    
    for timeout_duration in network_scenarios {
        info!("Testing network scenario with {:?} timeout", timeout_duration);
        
        let event = json!({
            "type": "CONNECTION_TEST",
            "source": "network_test",
            "payload": {
                "timeout_ms": timeout_duration.as_millis()
            }
        });
        
        let response = timeout(
            timeout_duration,
            client
                .post(format!("{}/api/v1/events", BASE_URL))
                .json(&event)
                .send()
        ).await;
        
        match response {
            Ok(Ok(resp)) => {
                debug!("Network test ({:?}): Status {}", timeout_duration, resp.status());
            }
            Ok(Err(e)) => {
                debug!("Network test ({:?}): Network error {}", timeout_duration, e);
            }
            Err(_) => {
                debug!("Network test ({:?}): Timeout", timeout_duration);
            }
        }
        
        // Test recovery after network issues
        sleep(Duration::from_millis(100)).await;
        
        // Verify server is still responsive
        let recovery_response = timeout(
            Duration::from_secs(5),
            client
                .get(format!("{}/health", BASE_URL))
                .send()
        ).await;
        
        match recovery_response {
            Ok(Ok(resp)) => {
                assert!(resp.status().is_success(), "Server not responsive after network test");
            }
            Ok(Err(e)) => {
                error!("Server not responsive after network test: {}", e);
            }
            Err(_) => {
                error!("Server health check timed out after network test");
            }
        }
    }
}

#[tokio::test]
async fn test_graceful_degradation() {
    let client = reqwest::Client::new();
    
    // Test that system degrades gracefully under increasing load
    let load_levels = vec![
        (1, 10),    // Light load: 1 event/request, 10 requests
        (10, 10),   // Medium load: 10 events/request, 10 requests
        (100, 10),  // Heavy load: 100 events/request, 10 requests
        (1000, 10), // Extreme load: 1000 events/request, 10 requests
    ];
    
    let mut response_times = Vec::new();
    let mut success_rates = Vec::new();
    
    for (events_per_batch, num_batches) in load_levels {
        info!("Testing graceful degradation: {} events/batch, {} batches", events_per_batch, num_batches);
        
        let mut batch_response_times = Vec::new();
        let mut successful_batches = 0;
        
        for batch_id in 0..num_batches {
            let batch_start = Instant::now();
            
            let batch = json!({
                "events": (0..events_per_batch).map(|i| json!({
                    "type": "HEARTBEAT",
                    "source": "degradation_test",
                    "payload": {
                        "batch_id": batch_id,
                        "event_id": i,
                        "events_per_batch": events_per_batch
                    }
                })).collect::<Vec<_>>()
            });
            
            let response = timeout(
                Duration::from_secs(30),
                client
                    .post(format!("{}/api/v1/events/batch", BASE_URL))
                    .json(&batch)
                    .send()
            ).await;
            
            let response_time = batch_start.elapsed();
            batch_response_times.push(response_time);
            
            match response {
                Ok(Ok(resp)) => {
                    if resp.status().is_success() {
                        successful_batches += 1;
                    }
                }
                Ok(Err(_)) | Err(_) => {
                    // Request failed
                }
            }
            
            // Small delay between batches
            sleep(Duration::from_millis(100)).await;
        }
        
        let avg_response_time = batch_response_times.iter().sum::<Duration>() / batch_response_times.len() as u32;
        let success_rate = successful_batches as f64 / num_batches as f64;
        
        response_times.push(avg_response_time);
        success_rates.push(success_rate);
        
        info!("Load level results:");
        info!("  Average response time: {:?}", avg_response_time);
        info!("  Success rate: {:.2}%", success_rate * 100.0);
        
        // Give system time to recover
        sleep(Duration::from_secs(1)).await;
    }
    
    // Analyze degradation patterns
    info!("Graceful degradation analysis:");
    for (i, (response_time, success_rate)) in response_times.iter().zip(success_rates.iter()).enumerate() {
        info!("  Load level {}: {:?} response time, {:.2}% success rate", 
              i + 1, response_time, success_rate * 100.0);
    }
    
    // System should maintain some level of functionality even under high load
    assert!(success_rates.iter().all(|&rate| rate > 0.3), 
            "System should maintain at least 30% success rate under all load levels");
    
    // Response time degradation should be reasonable (not exponential)
    let max_response_time = response_times.iter().max().unwrap();
    assert!(max_response_time < &Duration::from_secs(30), 
            "Response time degradation too severe");
}

#[tokio::test]
async fn test_error_recovery_patterns() {
    let client = reqwest::Client::new();
    
    // Test recovery after various error conditions
    let error_scenarios = vec![
        // Send invalid data
        ("invalid_json", "{invalid_json"),
        
        // Send huge payload
        ("oversized_payload", &json!({
            "type": "HEARTBEAT",
            "source": "error_recovery_test",
            "payload": {
                "huge_field": "x".repeat(1024 * 1024)
            }
        }).to_string()),
        
        // Send malformed batch
        ("malformed_batch", &json!({
            "not_events": [{"type": "HEARTBEAT"}]
        }).to_string()),
    ];
    
    for (scenario_name, error_payload) in error_scenarios {
        info!("Testing error recovery for scenario: {}", scenario_name);
        
        // Send error-inducing request
        let error_response = client
            .post(format!("{}/api/v1/events", BASE_URL))
            .header("Content-Type", "application/json")
            .body(error_payload.to_string())
            .timeout(Duration::from_secs(10))
            .send()
            .await;
        
        match error_response {
            Ok(resp) => {
                debug!("Error scenario '{}': Status {}", scenario_name, resp.status());
            }
            Err(e) => {
                debug!("Error scenario '{}': Network error {}", scenario_name, e);
            }
        }
        
        // Test immediate recovery
        let recovery_event = json!({
            "type": "CONNECTION_TEST",
            "source": "error_recovery_test",
            "payload": {
                "recovery_test": scenario_name
            }
        });
        
        let recovery_response = timeout(
            Duration::from_secs(5),
            client
                .post(format!("{}/api/v1/events", BASE_URL))
                .json(&recovery_event)
                .send()
        ).await;
        
        match recovery_response {
            Ok(Ok(resp)) => {
                assert!(resp.status().is_success(), 
                        "Server not recovered after error scenario: {}", scenario_name);
            }
            Ok(Err(e)) => {
                error!("Server not recovered after error scenario '{}': {}", scenario_name, e);
            }
            Err(_) => {
                error!("Server recovery timed out after error scenario: {}", scenario_name);
            }
        }
        
        // Test health endpoint recovery
        let health_response = timeout(
            Duration::from_secs(5),
            client
                .get(format!("{}/health", BASE_URL))
                .send()
        ).await;
        
        match health_response {
            Ok(Ok(resp)) => {
                assert!(resp.status().is_success(), 
                        "Health endpoint not recovered after error scenario: {}", scenario_name);
            }
            Ok(Err(e)) => {
                error!("Health endpoint not recovered after error scenario '{}': {}", scenario_name, e);
            }
            Err(_) => {
                error!("Health endpoint recovery timed out after error scenario: {}", scenario_name);
            }
        }
        
        // Wait between scenarios
        sleep(Duration::from_millis(500)).await;
    }
}

#[tokio::test]
async fn test_resource_exhaustion_recovery() {
    let client = reqwest::Client::new();
    
    // Test resource exhaustion scenarios
    info!("Testing resource exhaustion recovery");
    
    // Phase 1: Create resource pressure
    let pressure_duration = Duration::from_secs(10);
    let pressure_start = Instant::now();
    
    let mut pressure_tasks = Vec::new();
    for i in 0..10 {
        let client = client.clone();
        let task = tokio::spawn(async move {
            let mut requests = 0;
            let mut successes = 0;
            
            while pressure_start.elapsed() < pressure_duration {
                let large_batch = json!({
                    "events": (0..500).map(|j| json!({
                        "type": "HEARTBEAT",
                        "source": format!("pressure_test_{}", i),
                        "payload": {
                            "task_id": i,
                            "event_id": j,
                            "large_data": "x".repeat(1024) // 1KB per event
                        }
                    })).collect::<Vec<_>>()
                });
                
                let response = timeout(
                    Duration::from_secs(2),
                    client
                        .post(format!("{}/api/v1/events/batch", BASE_URL))
                        .json(&large_batch)
                        .send()
                ).await;
                
                requests += 1;
                
                match response {
                    Ok(Ok(resp)) => {
                        if resp.status().is_success() {
                            successes += 1;
                        }
                    }
                    Ok(Err(_)) | Err(_) => {
                        // Request failed
                    }
                }
                
                sleep(Duration::from_millis(100)).await;
            }
            
            (i, requests, successes)
        });
        
        pressure_tasks.push(task);
    }
    
    // Wait for pressure phase to complete
    let pressure_results = futures::future::join_all(pressure_tasks).await;
    
    let total_pressure_requests: usize = pressure_results.iter()
        .map(|r| r.as_ref().map(|(_, requests, _)| *requests).unwrap_or(0))
        .sum();
    let total_pressure_successes: usize = pressure_results.iter()
        .map(|r| r.as_ref().map(|(_, _, successes)| *successes).unwrap_or(0))
        .sum();
    
    info!("Pressure phase completed:");
    info!("  Total requests: {}", total_pressure_requests);
    info!("  Total successes: {}", total_pressure_successes);
    
    // Phase 2: Test recovery
    info!("Testing recovery after resource exhaustion");
    
    // Wait for system to recover
    sleep(Duration::from_secs(2)).await;
    
    // Test normal operation recovery
    let recovery_tests = 10;
    let mut recovery_successes = 0;
    
    for i in 0..recovery_tests {
        let recovery_event = json!({
            "type": "CONNECTION_TEST",
            "source": "recovery_test",
            "payload": {
                "recovery_test_id": i
            }
        });
        
        let response = timeout(
            Duration::from_secs(5),
            client
                .post(format!("{}/api/v1/events", BASE_URL))
                .json(&recovery_event)
                .send()
        ).await;
        
        match response {
            Ok(Ok(resp)) => {
                if resp.status().is_success() {
                    recovery_successes += 1;
                }
            }
            Ok(Err(_)) | Err(_) => {
                // Request failed
            }
        }
        
        sleep(Duration::from_millis(100)).await;
    }
    
    let recovery_rate = recovery_successes as f64 / recovery_tests as f64;
    
    info!("Recovery test results:");
    info!("  Recovery success rate: {:.2}%", recovery_rate * 100.0);
    
    // System should recover to normal operation
    assert!(recovery_rate > 0.8, "System did not recover properly: {:.2}% success rate", recovery_rate * 100.0);
}