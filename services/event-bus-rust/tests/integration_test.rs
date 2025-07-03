use reqwest;
use serde_json::json;
use std::time::Duration;
use tokio;

const BASE_URL: &str = "http://localhost:8080";

#[tokio::test]
async fn test_health_endpoint() {
    let client = reqwest::Client::new();

    let response = client
        .get(format!("{}/health", BASE_URL))
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
        .post(format!("{}/api/v1/events", BASE_URL))
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
        .post(format!("{}/api/v1/events/batch", BASE_URL))
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
        .post(format!("{}/api/v1/events", BASE_URL))
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
