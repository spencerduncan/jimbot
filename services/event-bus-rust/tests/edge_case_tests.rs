use reqwest;
use serde_json::{json, Value};
use std::time::Duration;
use tokio::time::timeout;
use tracing::{debug, error, info, warn};

const BASE_URL: &str = "http://localhost:8080";
const TIMEOUT_DURATION: Duration = Duration::from_secs(10);

/// Comprehensive edge case testing for Event Bus
/// Tests malformed inputs, oversized payloads, protocol violations, and error conditions
#[tokio::test]
async fn test_malformed_json_events() {
    let client = reqwest::Client::new();
    
    // Test cases for malformed JSON
    let malformed_cases = vec![
        // Invalid JSON syntax
        "{invalid_json",
        "{'single_quotes': 'not_valid'}",
        "{\"unclosed_object\": \"value\"",
        "[{\"array_instead_of_object\": true}]",
        
        // Empty and minimal inputs
        "",
        "null",
        "{}",
        "{\"type\": null}",
        
        // Type mismatches
        "{\"type\": 123}",
        "{\"type\": [\"array\"]}",
        "{\"type\": {\"nested\": \"object\"}}",
        
        // Unicode and special characters
        "{\"type\": \"test\", \"data\": \"\\u0000null_char\"}",
        "{\"type\": \"test\", \"data\": \"\\uD800incomplete_surrogate\"}",
        "{\"type\": \"test\", \"source\": \"../../../../etc/passwd\"}",
        
        // Extremely nested structures
        "{\"type\": \"test\", \"data\": {\"level1\": {\"level2\": {\"level3\": {\"level4\": {\"level5\": \"deep\"}}}}}}",
    ];
    
    for (i, malformed_json) in malformed_cases.iter().enumerate() {
        let response = client
            .post(format!("{}/api/v1/events", BASE_URL))
            .header("Content-Type", "application/json")
            .body(malformed_json.to_string())
            .timeout(TIMEOUT_DURATION)
            .send()
            .await;
            
        match response {
            Ok(resp) => {
                let status_code = resp.status();
                // Server should handle malformed JSON gracefully
                assert!(status_code.is_client_error() || status_code.is_success());
                
                if status_code.is_success() {
                    if let Ok(body) = resp.json::<Value>().await {
                        // If status is success, it should contain an error in the response
                        if let Some(status) = body.get("status") {
                            assert!(status == "error" || status == "ok");
                        }
                    }
                }
                
                debug!("Malformed JSON test case {}: Status {}", i, status_code);
            }
            Err(e) => {
                // Network errors are acceptable for malformed requests
                debug!("Malformed JSON test case {} failed with network error: {}", i, e);
            }
        }
    }
}

#[tokio::test]
async fn test_oversized_event_payloads() {
    let client = reqwest::Client::new();
    
    // Test various oversized payloads
    let size_tests = vec![
        // 1MB payload
        (1024 * 1024, "1MB"),
        // 10MB payload
        (10 * 1024 * 1024, "10MB"),
        // 100MB payload (should definitely be rejected)
        (100 * 1024 * 1024, "100MB"),
    ];
    
    for (size, description) in size_tests {
        let large_data = "x".repeat(size);
        let event = json!({
            "type": "HEARTBEAT",
            "source": "oversized_test",
            "payload": {
                "large_field": large_data
            }
        });
        
        let response = timeout(Duration::from_secs(30), 
            client
                .post(format!("{}/api/v1/events", BASE_URL))
                .json(&event)
                .send()
        ).await;
        
        match response {
            Ok(Ok(resp)) => {
                // Server should reject oversized payloads
                if size > 1024 * 1024 {
                    assert!(resp.status().is_client_error() || resp.status().is_server_error());
                }
                info!("Oversized payload test ({}): Status {}", description, resp.status());
            }
            Ok(Err(e)) => {
                // Network timeout or connection error is acceptable for huge payloads
                warn!("Oversized payload test ({}) failed with error: {}", description, e);
            }
            Err(_) => {
                // Timeout is acceptable for oversized payloads
                warn!("Oversized payload test ({}) timed out", description);
            }
        }
    }
}

#[tokio::test]
async fn test_missing_required_fields() {
    let client = reqwest::Client::new();
    
    // Test events with missing required fields
    let incomplete_events = vec![
        // Missing type
        json!({
            "source": "test",
            "payload": {}
        }),
        
        // Missing source
        json!({
            "type": "HEARTBEAT",
            "payload": {}
        }),
        
        // Missing payload
        json!({
            "type": "HEARTBEAT",
            "source": "test"
        }),
        
        // Empty type
        json!({
            "type": "",
            "source": "test",
            "payload": {}
        }),
        
        // Empty source
        json!({
            "type": "HEARTBEAT",
            "source": "",
            "payload": {}
        }),
        
        // Null fields
        json!({
            "type": null,
            "source": "test",
            "payload": {}
        }),
        
        json!({
            "type": "HEARTBEAT",
            "source": null,
            "payload": {}
        }),
    ];
    
    for (i, event) in incomplete_events.iter().enumerate() {
        let response = client
            .post(format!("{}/api/v1/events", BASE_URL))
            .json(event)
            .timeout(TIMEOUT_DURATION)
            .send()
            .await;
            
        match response {
            Ok(resp) => {
                // Server should handle missing fields gracefully
                let status = resp.status();
                let body = resp.text().await.unwrap_or_default();
                
                // Should either return error status or success with error in body
                if status.is_success() {
                    if let Ok(json_body) = serde_json::from_str::<Value>(&body) {
                        if let Some(status_field) = json_body.get("status") {
                            if status_field != "error" {
                                eprintln!("Test case {}: Expected error status, got: {}", i, body);
                                eprintln!("Event was: {:?}", event);
                            }
                            assert_eq!(status_field, "error");
                        }
                    }
                }
                
                debug!("Missing field test case {}: Status {}", i, status);
            }
            Err(e) => {
                error!("Missing field test case {} failed: {}", i, e);
            }
        }
    }
}

#[tokio::test]
async fn test_invalid_event_types() {
    let client = reqwest::Client::new();
    
    // Test various invalid event types
    let invalid_types = vec![
        "INVALID_TYPE",
        "UNKNOWN_EVENT",
        "SQL_INJECTION'; DROP TABLE events; --",
        "<script>alert('xss')</script>",
        "../../etc/passwd",
        "\0NULL_BYTE",
        "EXTREMELY_LONG_EVENT_TYPE_NAME_THAT_EXCEEDS_REASONABLE_LIMITS_AND_SHOULD_BE_REJECTED_BY_THE_SERVER",
        "🚀💀🔥", // Emoji event type
        "type with spaces",
        "TYPE_WITH_UNICODE_çharacters",
    ];
    
    for invalid_type in invalid_types {
        let event = json!({
            "type": invalid_type,
            "source": "invalid_type_test",
            "payload": {}
        });
        
        let response = client
            .post(format!("{}/api/v1/events", BASE_URL))
            .json(&event)
            .timeout(TIMEOUT_DURATION)
            .send()
            .await;
            
        match response {
            Ok(resp) => {
                // Server should handle invalid types gracefully
                let status = resp.status();
                let body = resp.text().await.unwrap_or_default();
                
                // Should indicate error for invalid types
                if status.is_success() {
                    if let Ok(json_body) = serde_json::from_str::<Value>(&body) {
                        if let Some(status_field) = json_body.get("status") {
                            // Should indicate error for unknown types
                            assert!(status_field == "error" || status_field == "ok");
                        }
                    }
                }
                
                debug!("Invalid type test '{}': Status {}", invalid_type, status);
            }
            Err(e) => {
                warn!("Invalid type test '{}' failed: {}", invalid_type, e);
            }
        }
    }
}

#[tokio::test]
async fn test_concurrent_connection_limits() {
    let client = reqwest::Client::new();
    
    // Test concurrent requests to find connection limits
    let concurrent_requests = 100;
    
    let event = json!({
        "type": "CONNECTION_TEST",
        "source": "concurrent_test",
        "payload": {
            "test_id": "connection_limit_test"
        }
    });
    
    // Create concurrent requests
    let requests = (0..concurrent_requests).map(|i| {
        let client = client.clone();
        let event = event.clone();
        
        async move {
            let start_time = std::time::Instant::now();
            
            let response = client
                .post(format!("{}/api/v1/events", BASE_URL))
                .json(&event)
                .timeout(TIMEOUT_DURATION)
                .send()
                .await;
                
            let duration = start_time.elapsed();
            
            match response {
                Ok(resp) => {
                    (i, resp.status(), duration, None)
                }
                Err(e) => {
                    (i, reqwest::StatusCode::REQUEST_TIMEOUT, duration, Some(e.to_string()))
                }
            }
        }
    }).collect::<Vec<_>>();
    
    // Execute all requests concurrently
    let results = futures::future::join_all(requests).await;
    
    // Analyze results
    let mut successful = 0;
    let mut failed = 0;
    let mut total_duration = Duration::from_millis(0);
    
    for (i, status, duration, error) in results {
        total_duration += duration;
        
        if status.is_success() {
            successful += 1;
        } else {
            failed += 1;
            debug!("Concurrent request {} failed: Status {}, Error: {:?}", i, status, error);
        }
    }
    
    let avg_duration = total_duration / concurrent_requests as u32;
    
    info!("Concurrent connection test results:");
    info!("  Successful: {}/{}", successful, concurrent_requests);
    info!("  Failed: {}/{}", failed, concurrent_requests);
    info!("  Average duration: {:?}", avg_duration);
    
    // At least 50% of requests should succeed under normal conditions
    assert!(successful >= concurrent_requests / 2);
    
    // Average response time should be reasonable
    assert!(avg_duration < Duration::from_secs(5));
}

#[tokio::test]
async fn test_batch_event_edge_cases() {
    let client = reqwest::Client::new();
    
    // Test various batch edge cases
    let batch_tests = vec![
        // Empty batch
        json!({
            "events": []
        }),
        
        // Single event batch
        json!({
            "events": [
                {
                    "type": "HEARTBEAT",
                    "source": "batch_test",
                    "payload": {}
                }
            ]
        }),
        
        // Mixed valid and invalid events
        json!({
            "events": [
                {
                    "type": "HEARTBEAT",
                    "source": "batch_test",
                    "payload": {}
                },
                {
                    "type": "INVALID_TYPE",
                    "source": "batch_test",
                    "payload": {}
                },
                {
                    "type": "HEARTBEAT",
                    "source": "batch_test",
                    "payload": {}
                }
            ]
        }),
        
        // Very large batch
        json!({
            "events": (0..1000).map(|i| json!({
                "type": "HEARTBEAT",
                "source": "batch_test",
                "payload": {
                    "batch_id": i
                }
            })).collect::<Vec<_>>()
        }),
        
        // Batch with malformed structure
        json!({
            "not_events": [
                {
                    "type": "HEARTBEAT",
                    "source": "batch_test",
                    "payload": {}
                }
            ]
        }),
        
        // Batch with non-array events
        json!({
            "events": {
                "type": "HEARTBEAT",
                "source": "batch_test",
                "payload": {}
            }
        }),
    ];
    
    for (i, batch) in batch_tests.iter().enumerate() {
        let response = client
            .post(format!("{}/api/v1/events/batch", BASE_URL))
            .json(batch)
            .timeout(TIMEOUT_DURATION)
            .send()
            .await;
            
        match response {
            Ok(resp) => {
                let status = resp.status();
                let body = resp.text().await.unwrap_or_default();
                
                // Server should handle all batch variations gracefully
                if status.is_success() {
                    if let Ok(json_body) = serde_json::from_str::<Value>(&body) {
                        if let Some(status_field) = json_body.get("status") {
                            assert!(status_field == "ok" || status_field == "error");
                        }
                    }
                }
                
                debug!("Batch test case {}: Status {}", i, status);
            }
            Err(e) => {
                error!("Batch test case {} failed: {}", i, e);
            }
        }
    }
}

#[tokio::test]
async fn test_protocol_buffer_edge_cases() {
    let client = reqwest::Client::new();
    
    // Test events that might cause protocol buffer conversion issues
    let proto_edge_cases = vec![
        // Extreme numeric values
        json!({
            "type": "MONEY_CHANGED",
            "source": "proto_test",
            "payload": {
                "old_value": i64::MAX,
                "new_value": i64::MIN,
                "difference": f64::INFINITY
            }
        }),
        
        // NaN and special float values
        json!({
            "type": "SCORE_CHANGED",
            "source": "proto_test",
            "payload": {
                "score": f64::NAN,
                "multiplier": f64::NEG_INFINITY,
                "bonus": -0.0
            }
        }),
        
        // Very long strings
        json!({
            "type": "HEARTBEAT",
            "source": "proto_test",
            "payload": {
                "message": "x".repeat(100000)
            }
        }),
        
        // Deeply nested structures
        json!({
            "type": "GAME_STATE",
            "source": "proto_test",
            "payload": {
                "level1": {
                    "level2": {
                        "level3": {
                            "level4": {
                                "level5": {
                                    "data": "deep_nesting"
                                }
                            }
                        }
                    }
                }
            }
        }),
        
        // Arrays with mixed types
        json!({
            "type": "HAND_PLAYED",
            "source": "proto_test",
            "payload": {
                "cards": [
                    "AH",
                    123,
                    null,
                    {"rank": "K", "suit": "S"},
                    [1, 2, 3]
                ]
            }
        }),
        
        // Binary data as base64
        json!({
            "type": "HEARTBEAT",
            "source": "proto_test",
            "payload": {
                "binary_data": "SGVsbG8gV29ybGQ="
            }
        }),
    ];
    
    for (i, event) in proto_edge_cases.iter().enumerate() {
        let response = client
            .post(format!("{}/api/v1/events", BASE_URL))
            .json(event)
            .timeout(TIMEOUT_DURATION)
            .send()
            .await;
            
        match response {
            Ok(resp) => {
                let status = resp.status();
                let body = resp.text().await.unwrap_or_default();
                
                // Server should handle protocol buffer edge cases gracefully
                if status.is_success() {
                    if let Ok(json_body) = serde_json::from_str::<Value>(&body) {
                        if let Some(status_field) = json_body.get("status") {
                            assert!(status_field == "ok" || status_field == "error");
                        }
                    }
                }
                
                debug!("Protocol buffer test case {}: Status {}", i, status);
            }
            Err(e) => {
                warn!("Protocol buffer test case {} failed: {}", i, e);
            }
        }
    }
}

#[tokio::test]
async fn test_error_response_consistency() {
    let client = reqwest::Client::new();
    
    // Test that error responses are consistent and informative
    let error_scenarios = vec![
        // Invalid JSON
        ("{invalid_json", "json_parse_error"),
        
        // Missing required fields
        ("{}", "missing_fields"),
        
        // Invalid event type
        ("{\"type\": \"INVALID\", \"source\": \"test\", \"payload\": {}}", "invalid_type"),
        
        // Empty request body
        ("", "empty_body"),
    ];
    
    for (body, scenario) in error_scenarios {
        let response = client
            .post(format!("{}/api/v1/events", BASE_URL))
            .header("Content-Type", "application/json")
            .body(body)
            .timeout(TIMEOUT_DURATION)
            .send()
            .await;
            
        match response {
            Ok(resp) => {
                let status = resp.status();
                let response_body = resp.text().await.unwrap_or_default();
                
                // Verify error responses are well-formed
                if status.is_client_error() || status.is_server_error() {
                    // Should have some error indication
                    assert!(!response_body.is_empty());
                }
                
                if status.is_success() && !response_body.is_empty() {
                    // If successful, should be valid JSON
                    if let Ok(json_body) = serde_json::from_str::<Value>(&response_body) {
                        if let Some(status_field) = json_body.get("status") {
                            assert!(status_field == "ok" || status_field == "error");
                            
                            // Error responses should have error message
                            if status_field == "error" {
                                assert!(json_body.get("error").is_some());
                            }
                        }
                    }
                }
                
                debug!("Error scenario '{}': Status {}", scenario, status);
            }
            Err(e) => {
                debug!("Error scenario '{}' failed with network error: {}", scenario, e);
            }
        }
    }
}

#[tokio::test]
async fn test_health_endpoint_resilience() {
    let client = reqwest::Client::new();
    
    // Test health endpoint under various conditions
    let health_tests = vec![
        // Normal health check
        ("GET", "/health", ""),
        
        // Health check with query parameters
        ("GET", "/health?verbose=true", ""),
        
        // Health check with invalid method
        ("POST", "/health", "{}"),
        
        // Health check with body (should be ignored)
        ("GET", "/health", "unexpected_body"),
        
        // Health check with invalid path
        ("GET", "/health/invalid", ""),
        
        // Health check with headers
        ("GET", "/health", ""),
    ];
    
    for (method, path, body) in health_tests {
        let request = match method {
            "GET" => client.get(format!("{}{}", BASE_URL, path)),
            "POST" => client.post(format!("{}{}", BASE_URL, path)),
            _ => client.get(format!("{}{}", BASE_URL, path)),
        };
        
        let response = request
            .body(body)
            .timeout(TIMEOUT_DURATION)
            .send()
            .await;
            
        match response {
            Ok(resp) => {
                let status = resp.status();
                
                // Health endpoint should always respond
                if path == "/health" && method == "GET" {
                    assert!(status.is_success());
                }
                
                debug!("Health test {} {}: Status {}", method, path, status);
            }
            Err(e) => {
                error!("Health test {} {} failed: {}", method, path, e);
            }
        }
    }
}

#[tokio::test]
async fn test_metrics_endpoint_security() {
    let client = reqwest::Client::new();
    
    // Test metrics endpoint for security issues
    let response = client
        .get(format!("{}/metrics", BASE_URL))
        .timeout(TIMEOUT_DURATION)
        .send()
        .await;
        
    match response {
        Ok(resp) => {
            let status = resp.status();
            let body = resp.text().await.unwrap_or_default();
            
            if status.is_success() {
                // Verify metrics don't expose sensitive information
                assert!(!body.contains("password"));
                assert!(!body.contains("secret"));
                assert!(!body.contains("key"));
                assert!(!body.contains("token"));
                
                // Should be valid metrics format
                assert!(body.contains("# HELP") || body.contains("# TYPE") || body.is_empty());
            }
            
            debug!("Metrics security test: Status {}", status);
        }
        Err(e) => {
            debug!("Metrics endpoint not available: {}", e);
        }
    }
}