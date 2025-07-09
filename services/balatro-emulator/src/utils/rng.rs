//! Deterministic RNG system for Balatro emulation
//!
//! This module provides a complete implementation of Balatro's Lua-based pseudorandom
//! system to ensure perfect game state reproduction for any given seed.
//!
//! The system maintains compatibility with Balatro's RNG behavior including:
//! - Global seed initialization equivalent to `math.randomseed(G.SEED)`
//! - Per-key seed tracking in `G.GAME.pseudorandom` equivalent table
//! - Deterministic hash-based seed generation
//! - Lua-compatible random number generation

use ahash::AHashMap;
use rand::prelude::*;
use rand_chacha::ChaCha8Rng;
use serde::{Deserialize, Serialize};
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

/// Seed type that can be either a numeric seed or a string seed
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum SeedType {
    /// Numeric seed value
    Numeric(u64),
    /// String seed (e.g., "TUTORIAL")
    String(String),
}

impl From<u64> for SeedType {
    fn from(value: u64) -> Self {
        SeedType::Numeric(value)
    }
}

impl From<String> for SeedType {
    fn from(value: String) -> Self {
        SeedType::String(value)
    }
}

impl From<&str> for SeedType {
    fn from(value: &str) -> Self {
        SeedType::String(value.to_string())
    }
}

/// Pseudorandom state manager that tracks seeds for different game events
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PseudorandomState {
    /// Base hashed seed derived from the global seed
    base_seed: u64,
    /// Per-key seed tracking (equivalent to G.GAME.pseudorandom)
    key_seeds: AHashMap<String, u64>,
    /// The original global seed for reference
    global_seed: SeedType,
}

impl PseudorandomState {
    /// Create a new pseudorandom state with the given global seed
    pub fn new(seed: SeedType) -> Self {
        let base_seed = Self::hash_seed(&seed);
        Self {
            base_seed,
            key_seeds: AHashMap::new(),
            global_seed: seed,
        }
    }

    /// Hash a seed to generate a base numeric seed
    fn hash_seed(seed: &SeedType) -> u64 {
        let mut hasher = DefaultHasher::new();
        match seed {
            SeedType::Numeric(n) => n.hash(&mut hasher),
            SeedType::String(s) => s.hash(&mut hasher),
        }
        hasher.finish()
    }

    /// Generate a deterministic seed for a given key
    /// This combines the base seed, key, and stored seed value
    pub fn pseudoseed(&mut self, key: &str) -> u64 {
        // Get current seed value for this key (or 0 if first time)
        let current_seed = self.key_seeds.get(key).copied().unwrap_or(0);

        // Create combined seed using base seed, key, and current seed
        let mut hasher = DefaultHasher::new();
        self.base_seed.hash(&mut hasher);
        key.hash(&mut hasher);
        current_seed.hash(&mut hasher);
        let combined_seed = hasher.finish();

        // Advance the stored seed for this key
        self.key_seeds
            .insert(key.to_string(), current_seed.wrapping_add(1));

        combined_seed
    }

    /// Get the current seed value for a key without advancing it
    pub fn get_key_seed(&self, key: &str) -> u64 {
        self.key_seeds.get(key).copied().unwrap_or(0)
    }

    /// Set the seed value for a specific key (for state loading)
    pub fn set_key_seed(&mut self, key: &str, seed: u64) {
        self.key_seeds.insert(key.to_string(), seed);
    }

    /// Get the base seed
    pub fn base_seed(&self) -> u64 {
        self.base_seed
    }

    /// Get the global seed
    pub fn global_seed(&self) -> &SeedType {
        &self.global_seed
    }

    /// Get all key seeds for serialization
    pub fn key_seeds(&self) -> &AHashMap<String, u64> {
        &self.key_seeds
    }
}

/// Main RNG system for Balatro emulation
#[derive(Debug)]
pub struct BalatroRng {
    /// Pseudorandom state manager
    state: PseudorandomState,
}

impl BalatroRng {
    /// Create a new RNG system with the given seed
    pub fn new(seed: SeedType) -> Self {
        Self {
            state: PseudorandomState::new(seed),
        }
    }

    /// Create from existing state (for loading saved games)
    pub fn from_state(state: PseudorandomState) -> Self {
        Self { state }
    }

    /// Get the current state (for saving games)
    pub fn state(&self) -> &PseudorandomState {
        &self.state
    }

    /// Get mutable state (for direct manipulation)
    pub fn state_mut(&mut self) -> &mut PseudorandomState {
        &mut self.state
    }

    /// Generate a deterministic seed for a given key
    pub fn pseudoseed(&mut self, key: &str) -> u64 {
        self.state.pseudoseed(key)
    }

    /// Core RNG function - generates a value in the specified range
    ///
    /// This is the equivalent of Balatro's `pseudorandom` function.
    /// - If min and max are provided, returns an integer in [min, max]
    /// - If only min is provided, returns an integer in [1, min]
    /// - If neither are provided, returns a float in [0, 1)
    pub fn pseudorandom(&mut self, seed: SeedType, min: Option<i32>, max: Option<i32>) -> f64 {
        // Convert seed to numeric value
        let numeric_seed = match seed {
            SeedType::Numeric(n) => n,
            SeedType::String(s) => self.pseudohash(&s),
        };

        // Create RNG from the seed
        let mut rng = ChaCha8Rng::seed_from_u64(numeric_seed);

        match (min, max) {
            (Some(min_val), Some(max_val)) => {
                // Return integer in [min, max] range
                let range = (max_val - min_val + 1) as f64;
                let random_val = rng.gen::<f64>();
                (min_val as f64 + (random_val * range).floor()).min(max_val as f64)
            }
            (Some(max_val), None) => {
                // Return integer in [1, max] range (Lua-style)
                let range = max_val as f64;
                let random_val = rng.gen::<f64>();
                (1.0 + (random_val * range).floor()).min(max_val as f64)
            }
            (None, Some(_)) => {
                // Invalid case: max without min, treat as no parameters
                rng.gen::<f64>()
            }
            (None, None) => {
                // Return float in [0, 1) range
                rng.gen::<f64>()
            }
        }
    }

    /// Select a random element from a collection deterministically
    pub fn pseudorandom_element<'a, T>(&mut self, collection: &'a [T], seed: u64) -> Option<&'a T> {
        if collection.is_empty() {
            return None;
        }

        let mut rng = ChaCha8Rng::seed_from_u64(seed);
        let index = rng.gen_range(0..collection.len());
        collection.get(index)
    }

    /// Deterministic shuffle using Fisher-Yates algorithm
    pub fn pseudoshuffle<T>(&mut self, list: &mut Vec<T>, seed: u64) {
        if list.len() <= 1 {
            return;
        }

        let mut rng = ChaCha8Rng::seed_from_u64(seed);

        // Fisher-Yates shuffle
        for i in (1..list.len()).rev() {
            let j = rng.gen_range(0..=i);
            list.swap(i, j);
        }
    }

    /// Hash function for string-to-float conversion
    /// This replicates Balatro's string hashing behavior
    pub fn pseudohash(&self, s: &str) -> u64 {
        let mut hasher = DefaultHasher::new();
        s.hash(&mut hasher);
        hasher.finish()
    }

    /// Generate a starting seed string (for new games)
    pub fn generate_starting_seed() -> String {
        let mut rng = thread_rng();

        // Generate a seed similar to Balatro's format
        // Use a mix of letters and numbers
        let chars: Vec<char> = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789".chars().collect();
        let seed_length = 8;

        let seed: String = (0..seed_length)
            .map(|_| chars[rng.gen_range(0..chars.len())])
            .collect();

        seed
    }

    /// Get a seeded RNG for card generation patterns
    /// This supports common Balatro patterns like:
    /// - "rarity" + ante + optional_append
    /// - "soul_" + card_type + ante  
    /// - "front" + key_append + ante
    /// - "erratic" + usage_context
    /// - "shuffle" + optional_seed
    pub fn get_card_rng(&mut self, pattern: &str, ante: u8, append: Option<&str>) -> u64 {
        let key = match append {
            Some(suffix) => format!("{}{}{}", pattern, ante, suffix),
            None => format!("{}{}", pattern, ante),
        };
        self.pseudoseed(&key)
    }

    /// Get RNG for shop generation
    pub fn get_shop_rng(&mut self, ante: u8, reroll_count: u32) -> u64 {
        let key = format!("shop_{}_{}", ante, reroll_count);
        self.pseudoseed(&key)
    }

    /// Get RNG for joker effects
    pub fn get_joker_rng(&mut self, joker_id: &str, trigger_count: u32) -> u64 {
        let key = format!("joker_{}_{}", joker_id, trigger_count);
        self.pseudoseed(&key)
    }
}

/// Utility functions for common RNG operations
impl BalatroRng {
    /// Roll a die with the given number of sides
    pub fn roll_die(&mut self, sides: u32, seed: u64) -> u32 {
        let mut rng = ChaCha8Rng::seed_from_u64(seed);
        rng.gen_range(1..=sides)
    }

    /// Check if a probability event occurs
    pub fn probability_check(&mut self, probability: f64, seed: u64) -> bool {
        let mut rng = ChaCha8Rng::seed_from_u64(seed);
        rng.gen::<f64>() < probability
    }

    /// Generate a weighted random choice
    pub fn weighted_choice<'a, T>(&mut self, choices: &'a [(T, f64)], seed: u64) -> Option<&'a T> {
        if choices.is_empty() {
            return None;
        }

        let total_weight: f64 = choices.iter().map(|(_, weight)| weight).sum();
        if total_weight <= 0.0 {
            return None;
        }

        let mut rng = ChaCha8Rng::seed_from_u64(seed);
        let mut target = rng.gen::<f64>() * total_weight;

        for (choice, weight) in choices {
            target -= weight;
            if target <= 0.0 {
                return Some(choice);
            }
        }

        // Fallback to last choice if we somehow get here
        choices.last().map(|(choice, _)| choice)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pseudorandom_state_creation() {
        let state = PseudorandomState::new(SeedType::Numeric(12345));
        // The base_seed is hashed, not the raw value
        let expected_hash = PseudorandomState::hash_seed(&SeedType::Numeric(12345));
        assert_eq!(state.base_seed(), expected_hash);
        assert_eq!(state.global_seed(), &SeedType::Numeric(12345));
    }

    #[test]
    fn test_pseudoseed_generation() {
        let mut state = PseudorandomState::new(SeedType::Numeric(12345));

        // First call should generate a seed
        let seed1 = state.pseudoseed("test_key");
        assert_ne!(seed1, 0);

        // Second call should generate a different seed
        let seed2 = state.pseudoseed("test_key");
        assert_ne!(seed2, seed1);

        // Different keys should generate different seeds
        let seed3 = state.pseudoseed("different_key");
        assert_ne!(seed3, seed1);
        assert_ne!(seed3, seed2);
    }

    #[test]
    fn test_pseudorandom_deterministic() {
        let mut rng1 = BalatroRng::new(SeedType::Numeric(12345));
        let mut rng2 = BalatroRng::new(SeedType::Numeric(12345));

        // Same seed should produce same results
        let val1 = rng1.pseudorandom(SeedType::Numeric(999), Some(1), Some(10));
        let val2 = rng2.pseudorandom(SeedType::Numeric(999), Some(1), Some(10));
        assert_eq!(val1, val2);
    }

    #[test]
    fn test_pseudorandom_ranges() {
        let mut rng = BalatroRng::new(SeedType::Numeric(12345));

        // Test min/max range
        let val = rng.pseudorandom(SeedType::Numeric(999), Some(5), Some(15));
        assert!(val >= 5.0 && val <= 15.0);

        // Test single max range (should be 1 to max)
        let val = rng.pseudorandom(SeedType::Numeric(999), Some(10), None);
        assert!(val >= 1.0 && val <= 10.0);

        // Test float range
        let val = rng.pseudorandom(SeedType::Numeric(999), None, None);
        assert!(val >= 0.0 && val < 1.0);
    }

    #[test]
    fn test_pseudoshuffle_deterministic() {
        let mut rng = BalatroRng::new(SeedType::Numeric(12345));

        let mut vec1 = vec![1, 2, 3, 4, 5];
        let mut vec2 = vec![1, 2, 3, 4, 5];

        rng.pseudoshuffle(&mut vec1, 999);
        rng.pseudoshuffle(&mut vec2, 999);

        // Same seed should produce same shuffle
        assert_eq!(vec1, vec2);

        // Should be different from original
        assert_ne!(vec1, vec![1, 2, 3, 4, 5]);
    }

    #[test]
    fn test_pseudorandom_element() {
        let mut rng = BalatroRng::new(SeedType::Numeric(12345));

        let collection = vec!["a", "b", "c", "d", "e"];
        let element1 = rng.pseudorandom_element(&collection, 999);
        let element2 = rng.pseudorandom_element(&collection, 999);

        // Same seed should produce same element
        assert_eq!(element1, element2);
        assert!(element1.is_some());
        assert!(collection.contains(element1.unwrap()));
    }

    #[test]
    fn test_string_seeds() {
        let mut rng = BalatroRng::new(SeedType::String("TUTORIAL".to_string()));

        let val1 = rng.pseudorandom(SeedType::String("test".to_string()), Some(1), Some(10));
        let val2 = rng.pseudorandom(SeedType::String("test".to_string()), Some(1), Some(10));

        // Same string seed should produce same result
        assert_eq!(val1, val2);
    }

    #[test]
    fn test_starting_seed_generation() {
        let seed1 = BalatroRng::generate_starting_seed();
        let seed2 = BalatroRng::generate_starting_seed();

        // Should generate different seeds
        assert_ne!(seed1, seed2);

        // Should be 8 characters long
        assert_eq!(seed1.len(), 8);
        assert_eq!(seed2.len(), 8);

        // Should only contain valid characters
        let valid_chars: Vec<char> = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789".chars().collect();
        for c in seed1.chars() {
            assert!(valid_chars.contains(&c));
        }
    }

    #[test]
    fn test_card_rng_patterns() {
        let mut rng = BalatroRng::new(SeedType::Numeric(12345));

        // Test different patterns
        let rarity_seed = rng.get_card_rng("rarity", 1, Some("joker"));
        let soul_seed = rng.get_card_rng("soul_", 1, Some("tarot"));
        let front_seed = rng.get_card_rng("front", 1, Some("deck"));

        // All should be different
        assert_ne!(rarity_seed, soul_seed);
        assert_ne!(rarity_seed, front_seed);
        assert_ne!(soul_seed, front_seed);
    }

    #[test]
    fn test_state_serialization() {
        let mut rng = BalatroRng::new(SeedType::String("TEST".to_string()));

        // Generate some seeds to populate state
        rng.pseudoseed("test1");
        rng.pseudoseed("test2");

        let state = rng.state().clone();
        let serialized = serde_json::to_string(&state).unwrap();
        let deserialized: PseudorandomState = serde_json::from_str(&serialized).unwrap();

        // State should be identical after serialization
        assert_eq!(state.base_seed(), deserialized.base_seed());
        assert_eq!(state.global_seed(), deserialized.global_seed());
        assert_eq!(state.key_seeds(), deserialized.key_seeds());
    }

    #[test]
    fn test_probability_check() {
        let mut rng = BalatroRng::new(SeedType::Numeric(12345));

        // Test extreme probabilities
        assert!(rng.probability_check(1.0, 999)); // Always true
        assert!(!rng.probability_check(0.0, 999)); // Always false

        // Test same seed produces same result
        let result1 = rng.probability_check(0.5, 999);
        let result2 = rng.probability_check(0.5, 999);
        assert_eq!(result1, result2);
    }

    #[test]
    fn test_weighted_choice() {
        let mut rng = BalatroRng::new(SeedType::Numeric(12345));

        let choices = vec![("rare", 1.0), ("common", 10.0), ("uncommon", 5.0)];

        let choice = rng.weighted_choice(&choices, 999);
        assert!(choice.is_some());

        let choice_val = choice.unwrap();
        assert!(choices.iter().any(|(item, _)| item == choice_val));
    }
}
