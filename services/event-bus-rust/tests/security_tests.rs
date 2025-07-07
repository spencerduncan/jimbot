use reqwest;
use serde_json::json;
use std::time::Duration;
use tokio::time::timeout;
use tracing::{debug, info, warn};

const BASE_URL: &str = "http://localhost:8080";
const TIMEOUT_DURATION: Duration = Duration::from_secs(10);

/// Basic security testing for Event Bus
/// Tests appropriate for LAN deployment - focusing on input validation and basic security

#[tokio::test]
async fn test_xss_injection_attempts() {
    let client = reqwest::Client::new();
    
    // Basic XSS injection payloads - just ensure they don't break the service
    let xss_payloads = vec![
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert('xss')>",
        "javascript:alert('xss')",
    ];
    
    for (i, payload) in xss_payloads.iter().enumerate() {
        let event = json!({
            "type": "HEARTBEAT",
            "source": payload,
            "payload": {
                "message": payload,
            }
        });
        
        let response = client
            .post(format!("{}/api/v1/events", BASE_URL))
            .json(&event)
            .timeout(TIMEOUT_DURATION)
            .send()
            .await;
            
        match response {
            Ok(resp) => {
                let status = resp.status();
                let body = resp.text().await.unwrap_or_default();
                
                // Server should handle XSS attempts gracefully
                // Response should not contain unescaped script tags
                if body.contains("<script>") {
                    warn!("Potential XSS vulnerability detected in response");
                }
                
                debug!("XSS injection test {}: Status {}", i, status);
            }
            Err(e) => {
                debug!("XSS injection test {} failed: {}", i, e);
            }
        }
    }
}

#[tokio::test]
async fn test_command_injection_attempts() {
    let client = reqwest::Client::new();
    
    // Basic command injection payloads
    let command_injection_payloads = vec![
        "; cat /etc/passwd",
        "| whoami",
        "$(whoami)",
    ];
    
    for (i, payload) in command_injection_payloads.iter().enumerate() {
        let event = json!({
            "type": "HEARTBEAT",
            "source": format!("cmd_test{}", payload),
            "payload": {
                "command": payload,
            }
        });
        
        let response = client
            .post(format!("{}/api/v1/events", BASE_URL))
            .json(&event)
            .timeout(TIMEOUT_DURATION)
            .send()
            .await;
            
        match response {
            Ok(resp) => {
                let status = resp.status();
                
                // Server should handle command injection attempts safely
                debug!("Command injection test {}: Status {}", i, status);
            }
            Err(e) => {
                debug!("Command injection test {} failed: {}", i, e);
            }
        }
    }
}

#[tokio::test]
async fn test_path_traversal_attempts() {
    let client = reqwest::Client::new();
    
    // Basic path traversal payloads
    let path_traversal_payloads = vec![
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
        "/etc/passwd",
    ];
    
    for (i, payload) in path_traversal_payloads.iter().enumerate() {
        let event = json!({
            "type": "HEARTBEAT",
            "source": "path_traversal_test",
            "payload": {
                "filename": payload,
                "path": payload,
            }
        });
        
        let response = client
            .post(format!("{}/api/v1/events", BASE_URL))
            .json(&event)
            .timeout(TIMEOUT_DURATION)
            .send()
            .await;
            
        match response {
            Ok(resp) => {
                let status = resp.status();
                let body = resp.text().await.unwrap_or_default();
                
                // Server should prevent path traversal
                // Should not expose file system contents
                assert!(!body.contains("root:"));
                assert!(!body.contains("/bin/bash"));
                
                debug!("Path traversal test {}: Status {}", i, status);
            }
            Err(e) => {
                debug!("Path traversal test {} failed: {}", i, e);
            }
        }
    }
}

#[tokio::test]
async fn test_input_validation_fuzzing() {
    let client = reqwest::Client::new();
    
    info!("Testing input validation with fuzzing");
    
    // Generate various malformed inputs
    let fuzz_inputs = vec![
        // Invalid UTF-8 sequences
        vec![0xFF, 0xFE, 0xFD],
        vec![0xC0, 0x80], // Overlong encoding
        
        // Control characters
        vec![0x00, 0x01, 0x02, 0x03],
    ];
    
    for (i, fuzz_data) in fuzz_inputs.iter().enumerate() {
        // Try to create a string from the fuzz data
        let fuzz_string = String::from_utf8_lossy(fuzz_data);
        
        let event = json!({
            "type": "HEARTBEAT",
            "source": fuzz_string,
            "payload": {
                "fuzz_data": fuzz_string,
            }
        });
        
        let response = client
            .post(format!("{}/api/v1/events", BASE_URL))
            .json(&event)
            .timeout(TIMEOUT_DURATION)
            .send()
            .await;
            
        match response {
            Ok(resp) => {
                // Server should handle fuzzing gracefully without crashing
                debug!("Fuzz test {}: Status {}", i, resp.status());
            }
            Err(e) => {
                debug!("Fuzz test {} failed: {}", i, e);
            }
        }
    }
}

#[tokio::test]
async fn test_content_type_attacks() {
    let client = reqwest::Client::new();
    
    info!("Testing content-type based attacks");
    
    let malicious_content_types = vec![
        "application/json; charset=utf-7",
        "text/html",
        "../etc/passwd",
    ];
    
    for content_type in malicious_content_types {
        let event = json!({
            "type": "HEARTBEAT",
            "source": "content_type_test",
            "payload": {
                "content_type_test": content_type
            }
        });
        
        let response = client
            .post(format!("{}/api/v1/events", BASE_URL))
            .header("Content-Type", content_type)
            .json(&event)
            .timeout(TIMEOUT_DURATION)
            .send()
            .await;
            
        match response {
            Ok(resp) => {
                let status = resp.status();
                
                // Server should handle various content types securely
                debug!("Content-type test '{}': Status {}", content_type, status);
            }
            Err(e) => {
                debug!("Content-type test '{}' failed: {}", content_type, e);
            }
        }
    }
}

#[tokio::test]
async fn test_information_disclosure() {
    let client = reqwest::Client::new();
    
    info!("Testing information disclosure vulnerabilities");
    
    // Test various endpoints for information leakage
    let test_paths = vec![
        "/",
        "/api",
        "/api/v1",
        "/health",
        "/metrics",
    ];
    
    for path in test_paths {
        let response = client
            .get(format!("{}{}", BASE_URL, path))
            .timeout(TIMEOUT_DURATION)
            .send()
            .await;
            
        match response {
            Ok(resp) => {
                let status = resp.status();
                let body = resp.text().await.unwrap_or_default();
                
                // Check for information disclosure
                if status.is_success() {
                    // Should not expose sensitive information
                    assert!(!body.to_lowercase().contains("password"));
                    assert!(!body.to_lowercase().contains("secret"));
                    assert!(!body.to_lowercase().contains("private"));
                    assert!(!body.to_lowercase().contains("stack trace"));
                }
                
                debug!("Info disclosure test '{}': Status {}", path, status);
            }
            Err(e) => {
                debug!("Info disclosure test '{}' failed: {}", path, e);
            }
        }
    }
}