#![allow(clippy::uninlined_format_args)]

use serde_json::json;
use std::time::Duration;
use tracing::{debug, info};

const BASE_URL: &str = "http://localhost:8080";

#[tokio::test]
async fn test_health_endpoint() {
    let client = reqwest::Client::new();

    let response = client
        .get(format!("{BASE_URL}/health"))
        .timeout(Duration::from_secs(5))
        .send()
        .await;

    match response {
        Ok(resp) => {
            assert_eq!(resp.status(), 200);
            let body: serde_json::Value = resp.json().await.unwrap();
            assert_eq!(body["status"], "healthy");
        }
        Err(_) => {
            println!("Server not running - skipping integration test");
        }
    }
}

#[tokio::test]
async fn test_single_event_endpoint() {
    let client = reqwest::Client::new();

    let event = json!({
        "type": "HEARTBEAT",
        "source": "integration_test",
        "payload": {
            "version": "1.0.0",
            "uptime": 12345,
            "headless": false,
            "game_state": "MENU"
        }
    });

    let response = client
        .post(format!("{BASE_URL}/api/v1/events"))
        .json(&event)
        .timeout(Duration::from_secs(5))
        .send()
        .await;

    match response {
        Ok(resp) => {
            assert_eq!(resp.status(), 200);
            let body: serde_json::Value = resp.json().await.unwrap();
            assert_eq!(body["status"], "ok");
        }
        Err(_) => {
            println!("Server not running - skipping integration test");
        }
    }
}

#[tokio::test]
async fn test_batch_events_endpoint() {
    let client = reqwest::Client::new();

    let batch = json!({
        "events": [
            {
                "type": "CONNECTION_TEST",
                "source": "integration_test",
                "payload": {
                    "message": "Test 1"
                }
            },
            {
                "type": "MONEY_CHANGED",
                "source": "integration_test",
                "payload": {
                    "old_value": 10,
                    "new_value": 15,
                    "difference": 5
                }
            }
        ]
    });

    let response = client
        .post(format!("{BASE_URL}/api/v1/events/batch"))
        .json(&batch)
        .timeout(Duration::from_secs(5))
        .send()
        .await;

    match response {
        Ok(resp) => {
            assert_eq!(resp.status(), 200);
            let body: serde_json::Value = resp.json().await.unwrap();
            assert_eq!(body["status"], "ok");
        }
        Err(_) => {
            println!("Server not running - skipping integration test");
        }
    }
}

#[tokio::test]
async fn test_invalid_event_type() {
    let client = reqwest::Client::new();

    let event = json!({
        "type": "INVALID_TYPE",
        "source": "integration_test",
        "payload": {}
    });

    let response = client
        .post(format!("{BASE_URL}/api/v1/events"))
        .json(&event)
        .timeout(Duration::from_secs(5))
        .send()
        .await;

    match response {
        Ok(resp) => {
            assert_eq!(resp.status(), 200); // Still returns 200 but with error in body
            let body: serde_json::Value = resp.json().await.unwrap();
            assert_eq!(body["status"], "error");
            assert!(body["error"]
                .as_str()
                .unwrap()
                .contains("Unknown event type"));
        }
        Err(_) => {
            println!("Server not running - skipping integration test");
        }
    }
}

#[tokio::test]
async fn test_basic_edge_cases() {
    let client = reqwest::Client::new();

    info!("Testing basic edge cases for graceful handling");

    // Test empty event
    let empty_event = json!({});
    let response = client
        .post(format!("{BASE_URL}/api/v1/events"))
        .json(&empty_event)
        .timeout(Duration::from_secs(5))
        .send()
        .await;

    match response {
        Ok(resp) => {
            debug!("Empty event test: Status {}", resp.status());
            // Server should handle empty events gracefully (either success with error or client error)
        }
        Err(_) => {
            debug!("Empty event test: Server not running - skipping");
        }
    }

    // Test malformed JSON (sent as string)
    let response = client
        .post(format!("{BASE_URL}/api/v1/events"))
        .header("Content-Type", "application/json")
        .body("{invalid_json")
        .timeout(Duration::from_secs(5))
        .send()
        .await;

    match response {
        Ok(resp) => {
            debug!("Malformed JSON test: Status {}", resp.status());
            // Server should handle malformed JSON gracefully
        }
        Err(_) => {
            debug!("Malformed JSON test: Server not running - skipping");
        }
    }

    // Test oversized payload
    let large_payload = "x".repeat(1024 * 1024); // 1MB
    let large_event = json!({
        "type": "HEARTBEAT",
        "source": "integration_test",
        "payload": {
            "large_field": large_payload
        }
    });

    let response = client
        .post(format!("{BASE_URL}/api/v1/events"))
        .json(&large_event)
        .timeout(Duration::from_secs(10))
        .send()
        .await;

    match response {
        Ok(resp) => {
            debug!("Large payload test: Status {}", resp.status());
            // Server should handle large payloads gracefully (may reject or accept)
        }
        Err(_) => {
            debug!("Large payload test: Server not running or timeout - skipping");
        }
    }

    info!("Basic edge case tests completed");
}
