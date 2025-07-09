//! Balatro Emulator Library
//!
//! A high-performance Rust implementation of the Balatro card game that provides
//! deterministic game emulation for reinforcement learning and game analysis.
//!
//! The emulator maintains complete compatibility with Balatro's game mechanics,
//! including:
//! - Deterministic RNG system that matches Lua's pseudorandom behavior
//! - Complete card and joker system implementation
//! - Accurate scoring and game state management
//! - Event emission compatible with existing infrastructure
//!
//! # Example
//!
//! ```rust
//! use balatro_emulator::utils::{BalatroRng, SeedType};
//!
//! // Create a new RNG system with a specific seed
//! let mut rng = BalatroRng::new(SeedType::String("TUTORIAL".to_string()));
//!
//! // Generate deterministic random values
//! let value = rng.pseudorandom(SeedType::Numeric(999), Some(1), Some(10));
//! println!("Random value: {}", value);
//!
//! // Generate seeds for game events
//! let card_seed = rng.pseudoseed("rarity1");
//! println!("Card generation seed: {}", card_seed);
//! ```

pub mod utils;

// Re-export commonly used types for convenience
pub use utils::{BalatroRng, PseudorandomState, SeedType};
