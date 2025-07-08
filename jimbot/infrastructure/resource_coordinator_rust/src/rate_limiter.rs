use std::collections::{HashMap, VecDeque};
use std::sync::Arc;
use tokio::sync::{Mutex, Semaphore};
use tokio::time::{Duration, Instant};
use tracing::{debug, info, warn};

/// Token bucket rate limiter for API quotas
#[derive(Debug)]
pub struct RateLimiter {
    /// Maximum tokens in the bucket
    capacity: u32,
    
    /// Tokens refill rate per second
    refill_rate: f64,
    
    /// Current tokens available
    tokens: Arc<Mutex<f64>>,
    
    /// Last refill timestamp
    last_refill: Arc<Mutex<Instant>>,
    
    /// Semaphore for concurrent access control
    semaphore: Arc<Semaphore>,
}

impl RateLimiter {
    /// Create a new rate limiter
    pub fn new(capacity: u32, refill_rate: f64) -> Self {
        Self {
            capacity,
            refill_rate,
            tokens: Arc::new(Mutex::new(capacity as f64)),
            last_refill: Arc::new(Mutex::new(Instant::now())),
            semaphore: Arc::new(Semaphore::new(capacity as usize)),
        }
    }
    
    /// Try to acquire tokens
    pub async fn try_acquire(&self, tokens_needed: u32) -> Result<(), String> {
        if tokens_needed > self.capacity {
            return Err(format!("Requested {} tokens exceeds capacity {}", tokens_needed, self.capacity));
        }
        
        let mut tokens = self.tokens.lock().await;
        let mut last_refill = self.last_refill.lock().await;
        
        // Refill tokens based on elapsed time
        let now = Instant::now();
        let elapsed = now.duration_since(*last_refill).as_secs_f64();
        let tokens_to_add = elapsed * self.refill_rate;
        
        if tokens_to_add > 0.0 {
            *tokens = (*tokens + tokens_to_add).min(self.capacity as f64);
            *last_refill = now;
        }
        
        // Check if enough tokens available
        if *tokens >= tokens_needed as f64 {
            *tokens -= tokens_needed as f64;
            debug!("Acquired {} tokens, {} remaining", tokens_needed, *tokens);
            Ok(())
        } else {
            Err(format!("Insufficient tokens: need {}, have {}", tokens_needed, *tokens))
        }
    }
    
    /// Wait until tokens are available
    pub async fn acquire(&self, tokens_needed: u32) -> Result<(), String> {
        if tokens_needed > self.capacity {
            return Err(format!("Requested {} tokens exceeds capacity {}", tokens_needed, self.capacity));
        }
        
        loop {
            match self.try_acquire(tokens_needed).await {
                Ok(()) => return Ok(()),
                Err(_) => {
                    // Calculate wait time
                    let tokens = self.tokens.lock().await;
                    let tokens_short = tokens_needed as f64 - *tokens;
                    let wait_seconds = tokens_short / self.refill_rate;
                    drop(tokens);
                    
                    debug!("Waiting {:.2}s for {} tokens", wait_seconds, tokens_needed);
                    tokio::time::sleep(Duration::from_secs_f64(wait_seconds)).await;
                }
            }
        }
    }
    
    /// Get current token count
    pub async fn available_tokens(&self) -> f64 {
        let mut tokens = self.tokens.lock().await;
        let mut last_refill = self.last_refill.lock().await;
        
        // Refill before returning count
        let now = Instant::now();
        let elapsed = now.duration_since(*last_refill).as_secs_f64();
        let tokens_to_add = elapsed * self.refill_rate;
        
        if tokens_to_add > 0.0 {
            *tokens = (*tokens + tokens_to_add).min(self.capacity as f64);
            *last_refill = now;
        }
        
        *tokens
    }
}

/// Sliding window rate limiter for more accurate rate limiting
#[derive(Debug)]
pub struct SlidingWindowLimiter {
    /// Maximum requests per window
    max_requests: u32,
    
    /// Window duration
    window_duration: Duration,
    
    /// Request timestamps
    requests: Arc<Mutex<VecDeque<Instant>>>,
}

impl SlidingWindowLimiter {
    pub fn new(max_requests: u32, window_duration: Duration) -> Self {
        Self {
            max_requests,
            window_duration,
            requests: Arc::new(Mutex::new(VecDeque::new())),
        }
    }
    
    /// Try to record a request
    pub async fn try_acquire(&self) -> Result<(), String> {
        let mut requests = self.requests.lock().await;
        let now = Instant::now();
        
        // Remove old requests outside the window
        while let Some(&front) = requests.front() {
            if now.duration_since(front) > self.window_duration {
                requests.pop_front();
            } else {
                break;
            }
        }
        
        // Check if we can add a new request
        if requests.len() < self.max_requests as usize {
            requests.push_back(now);
            Ok(())
        } else {
            Err(format!("Rate limit exceeded: {} requests in {:?}", self.max_requests, self.window_duration))
        }
    }
    
    /// Get current request count in window
    pub async fn current_count(&self) -> usize {
        let mut requests = self.requests.lock().await;
        let now = Instant::now();
        
        // Remove old requests
        while let Some(&front) = requests.front() {
            if now.duration_since(front) > self.window_duration {
                requests.pop_front();
            } else {
                break;
            }
        }
        
        requests.len()
    }
    
    /// Time until next available slot
    pub async fn time_until_available(&self) -> Option<Duration> {
        let requests = self.requests.lock().await;
        
        if requests.len() < self.max_requests as usize {
            return None; // Available now
        }
        
        // Find the oldest request
        if let Some(&oldest) = requests.front() {
            let elapsed = Instant::now().duration_since(oldest);
            if elapsed < self.window_duration {
                Some(self.window_duration - elapsed)
            } else {
                None // Should be available after cleanup
            }
        } else {
            None
        }
    }
}

/// Multi-tier rate limiter supporting different limits for different clients
pub struct MultiTierRateLimiter {
    /// Rate limiters by tier
    tiers: HashMap<String, Arc<RateLimiter>>,
    
    /// Client to tier mapping
    client_tiers: Arc<Mutex<HashMap<String, String>>>,
    
    /// Default tier for unknown clients
    default_tier: String,
}

impl MultiTierRateLimiter {
    pub fn new(default_tier: String) -> Self {
        Self {
            tiers: HashMap::new(),
            client_tiers: Arc::new(Mutex::new(HashMap::new())),
            default_tier,
        }
    }
    
    /// Add a rate limiting tier
    pub fn add_tier(&mut self, tier_name: String, capacity: u32, refill_rate: f64) {
        self.tiers.insert(tier_name, Arc::new(RateLimiter::new(capacity, refill_rate)));
    }
    
    /// Assign a client to a tier
    pub async fn assign_client_tier(&self, client_id: String, tier: String) -> Result<(), String> {
        if !self.tiers.contains_key(&tier) {
            return Err(format!("Unknown tier: {}", tier));
        }
        
        let mut client_tiers = self.client_tiers.lock().await;
        client_tiers.insert(client_id, tier);
        Ok(())
    }
    
    /// Try to acquire tokens for a client
    pub async fn try_acquire(&self, client_id: &str, tokens: u32) -> Result<(), String> {
        let client_tiers = self.client_tiers.lock().await;
        let tier = client_tiers.get(client_id).unwrap_or(&self.default_tier);
        
        if let Some(limiter) = self.tiers.get(tier) {
            limiter.try_acquire(tokens).await
        } else {
            Err(format!("No rate limiter found for tier: {}", tier))
        }
    }
    
    /// Get client's current tier
    pub async fn get_client_tier(&self, client_id: &str) -> String {
        let client_tiers = self.client_tiers.lock().await;
        client_tiers.get(client_id).cloned().unwrap_or_else(|| self.default_tier.clone())
    }
}

/// Builder for creating multi-tier rate limiters with common configurations
pub struct RateLimiterBuilder {
    limiters: HashMap<String, (u32, f64)>,
    default_tier: String,
}

impl RateLimiterBuilder {
    pub fn new(default_tier: String) -> Self {
        Self {
            limiters: HashMap::new(),
            default_tier,
        }
    }
    
    /// Add a basic tier (requests per hour)
    pub fn add_basic_tier(mut self, requests_per_hour: u32) -> Self {
        let refill_rate = requests_per_hour as f64 / 3600.0;
        self.limiters.insert("basic".to_string(), (requests_per_hour, refill_rate));
        self
    }
    
    /// Add a premium tier (requests per hour)
    pub fn add_premium_tier(mut self, requests_per_hour: u32) -> Self {
        let refill_rate = requests_per_hour as f64 / 3600.0;
        self.limiters.insert("premium".to_string(), (requests_per_hour, refill_rate));
        self
    }
    
    /// Add a custom tier
    pub fn add_tier(mut self, name: String, capacity: u32, refill_rate: f64) -> Self {
        self.limiters.insert(name, (capacity, refill_rate));
        self
    }
    
    /// Build the multi-tier rate limiter
    pub fn build(self) -> MultiTierRateLimiter {
        let mut limiter = MultiTierRateLimiter::new(self.default_tier);
        
        for (name, (capacity, refill_rate)) in self.limiters {
            limiter.add_tier(name, capacity, refill_rate);
        }
        
        limiter
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_token_bucket() {
        let limiter = RateLimiter::new(10, 1.0); // 10 tokens, 1 per second
        
        // Should be able to acquire 5 tokens
        assert!(limiter.try_acquire(5).await.is_ok());
        assert_eq!(limiter.available_tokens().await as u32, 5);
        
        // Should be able to acquire 5 more
        assert!(limiter.try_acquire(5).await.is_ok());
        assert_eq!(limiter.available_tokens().await as u32, 0);
        
        // Should fail to acquire more
        assert!(limiter.try_acquire(1).await.is_err());
        
        // Wait for refill
        tokio::time::sleep(Duration::from_secs(2)).await;
        
        // Should have ~2 tokens now
        let tokens = limiter.available_tokens().await;
        assert!(tokens >= 1.5 && tokens <= 2.5);
    }
    
    #[tokio::test]
    async fn test_sliding_window() {
        let limiter = SlidingWindowLimiter::new(3, Duration::from_secs(1));
        
        // Should allow 3 requests
        assert!(limiter.try_acquire().await.is_ok());
        assert!(limiter.try_acquire().await.is_ok());
        assert!(limiter.try_acquire().await.is_ok());
        
        // 4th should fail
        assert!(limiter.try_acquire().await.is_err());
        
        // Wait for window to slide
        tokio::time::sleep(Duration::from_secs(1)).await;
        
        // Should allow again
        assert!(limiter.try_acquire().await.is_ok());
    }
    
    #[tokio::test]
    async fn test_multi_tier() {
        let limiter = RateLimiterBuilder::new("basic".to_string())
            .add_basic_tier(100)   // 100 per hour
            .add_premium_tier(1000) // 1000 per hour
            .build();
        
        // Assign clients to tiers
        limiter.assign_client_tier("client1".to_string(), "basic".to_string()).await.unwrap();
        limiter.assign_client_tier("client2".to_string(), "premium".to_string()).await.unwrap();
        
        // Test tier assignment
        assert_eq!(limiter.get_client_tier("client1").await, "basic");
        assert_eq!(limiter.get_client_tier("client2").await, "premium");
        assert_eq!(limiter.get_client_tier("unknown").await, "basic"); // default
    }
}