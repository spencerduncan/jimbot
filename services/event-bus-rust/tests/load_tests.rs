use futures::stream::{self, StreamExt};
use reqwest;
use serde_json::json;
use std::collections::HashMap;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::time::{sleep, timeout};
use tracing::{debug, error, info, warn};

const BASE_URL: &str = "http://localhost:8080";

/// Comprehensive load testing for Event Bus
/// Tests sustained loads, burst patterns, mixed distributions, and connection churn
#[tokio::test]
async fn test_sustained_load_24_hours() {
    // This is a simplified version for CI - in production this would run for 24 hours
    let client = reqwest::Client::new();
    let test_duration = Duration::from_secs(300); // 5 minutes for CI testing
    let target_rps = 50; // 50 requests per second
    
    info!("Starting sustained load test for {:?} at {} RPS", test_duration, target_rps);
    
    let start_time = Instant::now();
    let mut total_requests = 0;
    let mut successful_requests = 0;
    let mut error_count = 0;
    let mut response_times = Vec::new();
    
    // Track performance over time
    let mut minute_stats = Vec::new();
    let mut last_minute_check = start_time;
    let mut minute_requests = 0;
    let mut minute_successes = 0;
    
    while start_time.elapsed() < test_duration {
        let request_start = Instant::now();
        
        let event = json!({
            "type": "HEARTBEAT",
            "source": "sustained_load_test",
            "payload": {
                "request_id": total_requests,
                "elapsed_seconds": start_time.elapsed().as_secs(),
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
        
        let response_time = request_start.elapsed();
        response_times.push(response_time);
        
        total_requests += 1;
        minute_requests += 1;
        
        match response {
            Ok(Ok(resp)) => {
                if resp.status().is_success() {
                    successful_requests += 1;
                    minute_successes += 1;
                } else {
                    error_count += 1;
                }
            }
            Ok(Err(e)) => {
                error_count += 1;
                debug!("Request failed: {}", e);
            }
            Err(_) => {
                error_count += 1;
                debug!("Request timed out");
            }
        }
        
        // Record minute-by-minute stats
        if last_minute_check.elapsed() >= Duration::from_secs(60) {
            let minute_success_rate = minute_successes as f64 / minute_requests as f64;
            minute_stats.push((
                (start_time.elapsed().as_secs() / 60) + 1,
                minute_requests,
                minute_successes,
                minute_success_rate,
            ));
            
            info!("Minute {}: {} requests, {:.2}% success rate", 
                  minute_stats.len(), minute_requests, minute_success_rate * 100.0);
            
            minute_requests = 0;
            minute_successes = 0;
            last_minute_check = Instant::now();
        }
        
        // Maintain target rate
        let target_interval = Duration::from_millis(1000 / target_rps);
        if response_time < target_interval {
            sleep(target_interval - response_time).await;
        }
    }
    
    // Calculate final statistics
    let total_duration = start_time.elapsed();
    let actual_rps = total_requests as f64 / total_duration.as_secs_f64();
    let success_rate = successful_requests as f64 / total_requests as f64;
    let error_rate = error_count as f64 / total_requests as f64;
    
    // Response time statistics
    response_times.sort();
    let avg_response_time = response_times.iter().sum::<Duration>() / response_times.len() as u32;
    let p50 = response_times[response_times.len() / 2];
    let p95 = response_times[response_times.len() * 95 / 100];
    let p99 = response_times[response_times.len() * 99 / 100];
    let max_response_time = response_times.iter().max().unwrap();
    
    info!("Sustained load test results:");
    info!("  Duration: {:?}", total_duration);
    info!("  Total requests: {}", total_requests);
    info!("  Target RPS: {}, Actual RPS: {:.2}", target_rps, actual_rps);
    info!("  Success rate: {:.2}%", success_rate * 100.0);
    info!("  Error rate: {:.2}%", error_rate * 100.0);
    info!("  Response times:");
    info!("    Average: {:?}", avg_response_time);
    info!("    P50: {:?}", p50);
    info!("    P95: {:?}", p95);
    info!("    P99: {:?}", p99);
    info!("    Max: {:?}", max_response_time);
    
    // Performance should remain stable over time
    assert!(success_rate > 0.95, "Success rate too low: {:.2}%", success_rate * 100.0);
    assert!(error_rate < 0.05, "Error rate too high: {:.2}%", error_rate * 100.0);
    assert!(p95 < Duration::from_secs(2), "P95 response time too high: {:?}", p95);
    
    // Check for performance degradation over time
    if minute_stats.len() > 2 {
        let first_minute_rate = minute_stats[0].3;
        let last_minute_rate = minute_stats[minute_stats.len() - 1].3;
        let degradation = (first_minute_rate - last_minute_rate) / first_minute_rate;
        
        assert!(degradation < 0.1, "Performance degraded by {:.2}% over time", degradation * 100.0);
    }
}

#[tokio::test]
async fn test_burst_traffic_patterns() {
    let client = reqwest::Client::new();
    
    info!("Testing various burst traffic patterns");
    
    // Define different burst patterns
    let burst_patterns = vec![
        // Pattern: (events_per_burst, bursts_count, interval_between_bursts, description)
        (50, 20, Duration::from_millis(100), "High frequency small bursts"),
        (200, 10, Duration::from_millis(500), "Medium frequency medium bursts"),
        (1000, 5, Duration::from_secs(2), "Low frequency large bursts"),
        (2000, 3, Duration::from_secs(5), "Very low frequency huge bursts"),
    ];
    
    for (events_per_burst, burst_count, interval, description) in burst_patterns {
        info!("Testing pattern: {}", description);
        info!("  {} events per burst, {} bursts, {:?} interval", 
              events_per_burst, burst_count, interval);
        
        let pattern_start = Instant::now();
        let mut total_events = 0;
        let mut successful_events = 0;
        let mut burst_response_times = Vec::new();
        
        for burst_id in 0..burst_count {
            let burst_start = Instant::now();
            
            // Create batch of events for this burst
            let batch = json!({
                "events": (0..events_per_burst).map(|i| json!({
                    "type": if i % 3 == 0 { "HEARTBEAT" } 
                          else if i % 3 == 1 { "CONNECTION_TEST" } 
                          else { "MONEY_CHANGED" },
                    "source": format!("burst_pattern_test_{}", burst_id),
                    "payload": {
                        "burst_id": burst_id,
                        "event_in_burst": i,
                        "burst_size": events_per_burst,
                        "pattern": description
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
            
            let burst_response_time = burst_start.elapsed();
            burst_response_times.push(burst_response_time);
            
            total_events += events_per_burst;
            
            match response {
                Ok(Ok(resp)) => {
                    if resp.status().is_success() {
                        successful_events += events_per_burst;
                    }
                    debug!("Burst {} completed in {:?}: Status {}", 
                           burst_id, burst_response_time, resp.status());
                }
                Ok(Err(e)) => {
                    warn!("Burst {} failed: {}", burst_id, e);
                }
                Err(_) => {
                    warn!("Burst {} timed out", burst_id);
                }
            }
            
            // Wait before next burst
            if burst_id < burst_count - 1 {
                sleep(interval).await;
            }
        }
        
        let pattern_duration = pattern_start.elapsed();
        let success_rate = successful_events as f64 / total_events as f64;
        let avg_burst_time = burst_response_times.iter().sum::<Duration>() / burst_response_times.len() as u32;
        let max_burst_time = burst_response_times.iter().max().unwrap_or(&Duration::from_secs(0));
        
        info!("Pattern results:");
        info!("  Total duration: {:?}", pattern_duration);
        info!("  Events processed: {}/{}", successful_events, total_events);
        info!("  Success rate: {:.2}%", success_rate * 100.0);
        info!("  Average burst time: {:?}", avg_burst_time);
        info!("  Max burst time: {:?}", max_burst_time);
        
        // Each pattern should handle bursts effectively
        assert!(success_rate > 0.8, 
                "Pattern '{}' had low success rate: {:.2}%", description, success_rate * 100.0);
        
        // Response times should scale reasonably with burst size
        let expected_max_time = Duration::from_millis(events_per_burst as u64 * 2); // 2ms per event max
        assert!(avg_burst_time < expected_max_time.min(Duration::from_secs(15)), 
                "Pattern '{}' response time too high: {:?}", description, avg_burst_time);
        
        // Allow system to recover between patterns
        sleep(Duration::from_secs(2)).await;
    }
}

#[tokio::test]
async fn test_mixed_event_type_distributions() {
    let client = reqwest::Client::new();
    
    info!("Testing mixed event type distributions");
    
    // Define different event type distributions
    let distributions = vec![
        // (distribution_weights, description)
        (vec![("HEARTBEAT", 70), ("CONNECTION_TEST", 20), ("MONEY_CHANGED", 10)], "Heartbeat heavy"),
        (vec![("HEARTBEAT", 25), ("CONNECTION_TEST", 25), ("MONEY_CHANGED", 25), ("SCORE_CHANGED", 25)], "Uniform distribution"),
        (vec![("GAME_STATE", 60), ("ROUND_CHANGED", 30), ("PHASE_CHANGED", 10)], "Game state heavy"),
        (vec![("HAND_PLAYED", 40), ("CARDS_DISCARDED", 30), ("JOKERS_CHANGED", 20), ("ROUND_COMPLETE", 10)], "Gameplay events"),
    ];
    
    for (distribution, description) in distributions {
        info!("Testing distribution: {}", description);
        
        let test_duration = Duration::from_secs(60);
        let events_per_second = 20;
        let start_time = Instant::now();
        
        let mut total_events = 0;
        let mut successful_events = 0;
        let mut event_type_counts: HashMap<String, usize> = HashMap::new();
        let mut response_times = Vec::new();
        
        // Calculate cumulative weights for random selection
        let total_weight: u32 = distribution.iter().map(|(_, weight)| *weight).sum();
        let mut cumulative_weights = Vec::new();
        let mut sum = 0;
        for (event_type, weight) in &distribution {
            sum += weight;
            cumulative_weights.push((event_type, sum));
        }
        
        while start_time.elapsed() < test_duration {
            let batch_start = Instant::now();
            
            // Generate batch with mixed event types
            let batch_events: Vec<_> = (0..events_per_second).map(|i| {
                // Select event type based on distribution
                let random_value = (total_events + i) % total_weight as usize;
                let selected_type = cumulative_weights.iter()
                    .find(|(_, cumulative)| random_value < *cumulative as usize)
                    .map(|(event_type, _)| *event_type)
                    .unwrap_or("HEARTBEAT");
                
                *event_type_counts.entry(selected_type.to_string()).or_insert(0) += 1;
                
                json!({
                    "type": selected_type,
                    "source": "mixed_distribution_test",
                    "payload": {
                        "event_id": total_events + i,
                        "distribution": description,
                        "selected_type": selected_type,
                        "timestamp": std::time::SystemTime::now()
                            .duration_since(std::time::UNIX_EPOCH)
                            .unwrap()
                            .as_millis()
                    }
                })
            }).collect();
            
            let batch = json!({
                "events": batch_events
            });
            
            let response = timeout(
                Duration::from_secs(10),
                client
                    .post(format!("{}/api/v1/events/batch", BASE_URL))
                    .json(&batch)
                    .send()
            ).await;
            
            let response_time = batch_start.elapsed();
            response_times.push(response_time);
            
            total_events += events_per_second;
            
            match response {
                Ok(Ok(resp)) => {
                    if resp.status().is_success() {
                        successful_events += events_per_second;
                    }
                }
                Ok(Err(e)) => {
                    debug!("Batch failed: {}", e);
                }
                Err(_) => {
                    debug!("Batch timed out");
                }
            }
            
            // Maintain rate
            if response_time < Duration::from_secs(1) {
                sleep(Duration::from_secs(1) - response_time).await;
            }
        }
        
        let success_rate = successful_events as f64 / total_events as f64;
        let avg_response_time = response_times.iter().sum::<Duration>() / response_times.len() as u32;
        
        info!("Distribution '{}' results:", description);
        info!("  Total events: {}", total_events);
        info!("  Success rate: {:.2}%", success_rate * 100.0);
        info!("  Average response time: {:?}", avg_response_time);
        info!("  Event type distribution:");
        
        for (event_type, count) in &event_type_counts {
            let percentage = *count as f64 / total_events as f64 * 100.0;
            info!("    {}: {} ({:.1}%)", event_type, count, percentage);
        }
        
        // Verify distribution handled well
        assert!(success_rate > 0.9, 
                "Distribution '{}' had low success rate: {:.2}%", description, success_rate * 100.0);
        
        assert!(avg_response_time < Duration::from_secs(2), 
                "Distribution '{}' had high response time: {:?}", description, avg_response_time);
        
        // Verify event types were distributed as expected
        for (expected_type, expected_weight) in &distribution {
            let actual_count = event_type_counts.get(*expected_type).unwrap_or(&0);
            let expected_percentage = *expected_weight as f64 / total_weight as f64;
            let actual_percentage = *actual_count as f64 / total_events as f64;
            let deviation = (expected_percentage - actual_percentage).abs();
            
            assert!(deviation < 0.05, 
                    "Event type '{}' distribution deviated too much: expected {:.1}%, got {:.1}%",
                    expected_type, expected_percentage * 100.0, actual_percentage * 100.0);
        }
        
        // Recovery time between distributions
        sleep(Duration::from_secs(1)).await;
    }
}

#[tokio::test]
async fn test_client_connection_churn() {
    info!("Testing client connection churn");
    
    let churn_duration = Duration::from_secs(120);
    let max_concurrent_clients = 20;
    let client_lifetime_range = (5, 15); // 5-15 seconds per client
    
    let start_time = Instant::now();
    let successful_requests = Arc::new(AtomicUsize::new(0));
    let failed_requests = Arc::new(AtomicUsize::new(0));
    let total_clients_created = Arc::new(AtomicUsize::new(0));
    
    let mut active_clients = Vec::new();
    
    while start_time.elapsed() < churn_duration {
        // Remove completed clients
        active_clients.retain(|handle: &tokio::task::JoinHandle<_>| !handle.is_finished());
        
        // Create new clients if under limit
        while active_clients.len() < max_concurrent_clients {
            let client_id = total_clients_created.fetch_add(1, Ordering::Relaxed);
            let successful_requests = successful_requests.clone();
            let failed_requests = failed_requests.clone();
            
            // Random lifetime for this client
            let lifetime_seconds = client_lifetime_range.0 + 
                (client_id % (client_lifetime_range.1 - client_lifetime_range.0 + 1));
            let client_lifetime = Duration::from_secs(lifetime_seconds as u64);
            
            let client_task = tokio::spawn(async move {
                let client = reqwest::Client::new();
                let client_start = Instant::now();
                let mut requests_sent = 0;
                let mut requests_succeeded = 0;
                
                while client_start.elapsed() < client_lifetime {
                    let event = json!({
                        "type": "CONNECTION_TEST",
                        "source": format!("churn_client_{}", client_id),
                        "payload": {
                            "client_id": client_id,
                            "request_id": requests_sent,
                            "client_age_ms": client_start.elapsed().as_millis()
                        }
                    });
                    
                    let response = timeout(
                        Duration::from_secs(5),
                        client
                            .post(format!("{}/api/v1/events", BASE_URL))
                            .json(&event)
                            .send()
                    ).await;
                    
                    requests_sent += 1;
                    
                    match response {
                        Ok(Ok(resp)) => {
                            if resp.status().is_success() {
                                requests_succeeded += 1;
                            }
                        }
                        Ok(Err(_)) | Err(_) => {
                            // Request failed
                        }
                    }
                    
                    // Random delay between requests (0.1-1.0 seconds)
                    let delay_ms = 100 + (requests_sent % 900);
                    sleep(Duration::from_millis(delay_ms as u64)).await;
                }
                
                successful_requests.fetch_add(requests_succeeded, Ordering::Relaxed);
                failed_requests.fetch_add(requests_sent - requests_succeeded, Ordering::Relaxed);
                
                (client_id, requests_sent, requests_succeeded)
            });
            
            active_clients.push(client_task);
        }
        
        // Check every second
        sleep(Duration::from_secs(1)).await;
    }
    
    // Wait for remaining clients to complete
    info!("Waiting for remaining {} clients to complete", active_clients.len());
    let remaining_results = futures::future::join_all(active_clients).await;
    
    let total_successful = successful_requests.load(Ordering::Relaxed);
    let total_failed = failed_requests.load(Ordering::Relaxed);
    let total_requests = total_successful + total_failed;
    let total_clients = total_clients_created.load(Ordering::Relaxed);
    
    let success_rate = total_successful as f64 / total_requests as f64;
    let requests_per_client = total_requests as f64 / total_clients as f64;
    
    info!("Client connection churn results:");
    info!("  Test duration: {:?}", churn_duration);
    info!("  Total clients created: {}", total_clients);
    info!("  Total requests: {}", total_requests);
    info!("  Successful requests: {} ({:.2}%)", total_successful, success_rate * 100.0);
    info!("  Failed requests: {} ({:.2}%)", total_failed, (total_failed as f64 / total_requests as f64) * 100.0);
    info!("  Average requests per client: {:.1}", requests_per_client);
    
    // System should handle connection churn gracefully
    assert!(success_rate > 0.85, "Success rate too low with connection churn: {:.2}%", success_rate * 100.0);
    assert!(total_clients > 20, "Not enough clients created during test");
    assert!(requests_per_client > 2.0, "Clients didn't generate enough requests");
}

#[tokio::test]
async fn test_progressive_load_scaling() {
    let client = reqwest::Client::new();
    
    info!("Testing progressive load scaling");
    
    // Progressively increase load to find breaking points
    let load_steps = vec![
        (10, "Light load"),
        (25, "Moderate load"),
        (50, "Heavy load"),
        (100, "Extreme load"),
        (200, "Breaking point test"),
    ];
    
    let mut results = Vec::new();
    
    for (target_rps, description) in load_steps {
        info!("Testing {}: {} RPS", description, target_rps);
        
        let step_duration = Duration::from_secs(30);
        let step_start = Instant::now();
        
        let mut step_requests = 0;
        let mut step_successes = 0;
        let mut step_response_times = Vec::new();
        
        while step_start.elapsed() < step_duration {
            let batch_start = Instant::now();
            
            // Calculate batch size to achieve target RPS
            let batch_size = target_rps;
            
            let batch = json!({
                "events": (0..batch_size).map(|i| json!({
                    "type": "HEARTBEAT",
                    "source": "scaling_test",
                    "payload": {
                        "target_rps": target_rps,
                        "batch_id": step_requests,
                        "event_id": i,
                        "step": description
                    }
                })).collect::<Vec<_>>()
            });
            
            let response = timeout(
                Duration::from_secs(10),
                client
                    .post(format!("{}/api/v1/events/batch", BASE_URL))
                    .json(&batch)
                    .send()
            ).await;
            
            let response_time = batch_start.elapsed();
            step_response_times.push(response_time);
            
            step_requests += 1;
            
            match response {
                Ok(Ok(resp)) => {
                    if resp.status().is_success() {
                        step_successes += 1;
                    }
                }
                Ok(Err(_)) | Err(_) => {
                    // Request failed
                }
            }
            
            // Try to maintain 1 second intervals
            if response_time < Duration::from_secs(1) {
                sleep(Duration::from_secs(1) - response_time).await;
            }
        }
        
        let step_duration_actual = step_start.elapsed();
        let step_success_rate = step_successes as f64 / step_requests as f64;
        let step_actual_rps = (step_requests * batch_size) as f64 / step_duration_actual.as_secs_f64();
        let step_avg_response_time = step_response_times.iter().sum::<Duration>() / step_response_times.len() as u32;
        
        results.push((target_rps, step_success_rate, step_actual_rps, step_avg_response_time));
        
        info!("Step results for {}:", description);
        info!("  Target RPS: {}, Actual RPS: {:.1}", target_rps, step_actual_rps);
        info!("  Success rate: {:.2}%", step_success_rate * 100.0);
        info!("  Average response time: {:?}", step_avg_response_time);
        
        // Allow recovery between steps
        sleep(Duration::from_secs(5)).await;
    }
    
    // Analyze scaling behavior
    info!("Progressive load scaling analysis:");
    for (i, (target_rps, success_rate, actual_rps, avg_response_time)) in results.iter().enumerate() {
        info!("  Step {}: {} target RPS -> {:.1} actual RPS, {:.2}% success, {:?} avg response", 
              i + 1, target_rps, actual_rps, success_rate * 100.0, avg_response_time);
    }
    
    // System should handle reasonable loads gracefully
    let reasonable_load_results: Vec<_> = results.iter().take(3).collect(); // First 3 loads
    for (target_rps, success_rate, _, _) in reasonable_load_results {
        assert!(*success_rate > 0.9, 
                "Success rate too low at {} RPS: {:.2}%", target_rps, success_rate * 100.0);
    }
    
    // Response time should degrade gracefully, not exponentially
    let first_response_time = results[0].3;
    let last_response_time = results[results.len() - 1].3;
    let response_time_ratio = last_response_time.as_millis() as f64 / first_response_time.as_millis() as f64;
    
    assert!(response_time_ratio < 100.0, 
            "Response time degradation too severe: {}x increase", response_time_ratio);
}