//! Comprehensive tests for the Balatro RNG system
//!
//! These tests verify that the RNG system produces deterministic results
//! that match Balatro's Lua-based pseudorandom behavior.

use balatro_emulator::utils::{BalatroRng, PseudorandomState, SeedType};
use serde_json;

#[test]
fn test_rng_deterministic_behavior() {
    // Test that the same seed produces identical sequences
    let mut rng1 = BalatroRng::new(SeedType::String("TEST_SEED".to_string()));
    let mut rng2 = BalatroRng::new(SeedType::String("TEST_SEED".to_string()));

    // Generate a sequence of values
    let mut values1 = Vec::new();
    let mut values2 = Vec::new();

    for i in 0..100 {
        let seed = SeedType::Numeric(i * 1000);
        values1.push(rng1.pseudorandom(seed.clone(), Some(1), Some(100)));
        values2.push(rng2.pseudorandom(seed, Some(1), Some(100)));
    }

    // Both sequences should be identical
    assert_eq!(values1, values2, "RNG sequences should be deterministic");
}

#[test]
fn test_pseudoseed_key_advancement() {
    let mut rng = BalatroRng::new(SeedType::Numeric(12345));

    // Test that the same key produces different seeds when called multiple times
    let key = "test_key";
    let seeds: Vec<u64> = (0..10).map(|_| rng.pseudoseed(key)).collect();

    // All seeds should be different
    for i in 0..seeds.len() {
        for j in i + 1..seeds.len() {
            assert_ne!(seeds[i], seeds[j], "Seeds should advance with each call");
        }
    }
}

#[test]
fn test_pseudorandom_ranges() {
    let mut rng = BalatroRng::new(SeedType::Numeric(12345));

    // Test min/max range
    for i in 0..100 {
        let val = rng.pseudorandom(SeedType::Numeric(i * 100), Some(5), Some(15));
        assert!(val >= 5.0 && val <= 15.0, "Value {} should be in range [5, 15]", val);
    }

    // Test single max range (1 to max)
    for i in 0..100 {
        let val = rng.pseudorandom(SeedType::Numeric(i * 100), Some(20), None);
        assert!(val >= 1.0 && val <= 20.0, "Value {} should be in range [1, 20]", val);
    }

    // Test float range [0, 1)
    for i in 0..100 {
        let val = rng.pseudorandom(SeedType::Numeric(i * 100), None, None);
        assert!(val >= 0.0 && val < 1.0, "Value {} should be in range [0, 1)", val);
    }
}

#[test]
fn test_card_generation_patterns() {
    let mut rng = BalatroRng::new(SeedType::String("GAME_SEED".to_string()));

    // Test common Balatro patterns
    let rarity_seed = rng.get_card_rng("rarity", 1, Some("joker"));
    let soul_seed = rng.get_card_rng("soul_", 1, Some("tarot"));
    let front_seed = rng.get_card_rng("front", 1, Some("deck"));
    let erratic_seed = rng.get_card_rng("erratic", 1, Some("usage"));

    // All should be different
    let seeds = vec![rarity_seed, soul_seed, front_seed, erratic_seed];
    for i in 0..seeds.len() {
        for j in i + 1..seeds.len() {
            assert_ne!(seeds[i], seeds[j], "Different patterns should produce different seeds");
        }
    }
}

#[test]
fn test_shop_and_joker_rngs() {
    let mut rng = BalatroRng::new(SeedType::Numeric(54321));

    // Test shop RNG with different antes and reroll counts
    let shop_seed_1 = rng.get_shop_rng(1, 0);
    let shop_seed_2 = rng.get_shop_rng(1, 1);
    let shop_seed_3 = rng.get_shop_rng(2, 0);

    assert_ne!(shop_seed_1, shop_seed_2);
    assert_ne!(shop_seed_1, shop_seed_3);
    assert_ne!(shop_seed_2, shop_seed_3);

    // Test joker RNG with different IDs and trigger counts
    let joker_seed_1 = rng.get_joker_rng("joker_1", 0);
    let joker_seed_2 = rng.get_joker_rng("joker_1", 1);
    let joker_seed_3 = rng.get_joker_rng("joker_2", 0);

    assert_ne!(joker_seed_1, joker_seed_2);
    assert_ne!(joker_seed_1, joker_seed_3);
    assert_ne!(joker_seed_2, joker_seed_3);
}

#[test]
fn test_pseudoshuffle_deterministic() {
    let mut rng = BalatroRng::new(SeedType::Numeric(98765));

    // Test that the same seed produces the same shuffle
    let seed = 42;
    let mut deck1 = vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
    let mut deck2 = vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

    rng.pseudoshuffle(&mut deck1, seed);
    rng.pseudoshuffle(&mut deck2, seed);

    assert_eq!(deck1, deck2, "Same seed should produce same shuffle");
    assert_ne!(deck1, vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "Deck should be shuffled");
}

#[test]
fn test_pseudorandom_element_selection() {
    let mut rng = BalatroRng::new(SeedType::Numeric(13579));

    let collection = vec!["ace", "two", "three", "four", "five"];
    let seed = 999;

    // Multiple selections with same seed should return same element
    let element1 = rng.pseudorandom_element(&collection, seed);
    let element2 = rng.pseudorandom_element(&collection, seed);

    assert_eq!(element1, element2);
    assert!(element1.is_some());
    assert!(collection.contains(element1.unwrap()));
}

#[test]
fn test_string_vs_numeric_seeds() {
    let mut rng = BalatroRng::new(SeedType::String("BASE".to_string()));

    // Test that string and numeric seeds produce different results
    let val1 = rng.pseudorandom(SeedType::String("test".to_string()), Some(1), Some(100));
    let val2 = rng.pseudorandom(SeedType::Numeric(12345), Some(1), Some(100));

    // They should be different (very unlikely to be the same)
    assert_ne!(val1, val2, "String and numeric seeds should produce different values");
}

#[test]
fn test_tutorial_seed_behavior() {
    // Test the special "TUTORIAL" seed behavior
    let mut rng = BalatroRng::new(SeedType::String("TUTORIAL".to_string()));

    // The tutorial seed should be deterministic
    let val1 = rng.pseudorandom(SeedType::Numeric(100), Some(1), Some(10));
    
    // Create a new RNG with the same seed
    let mut rng2 = BalatroRng::new(SeedType::String("TUTORIAL".to_string()));
    let val2 = rng2.pseudorandom(SeedType::Numeric(100), Some(1), Some(10));

    assert_eq!(val1, val2, "TUTORIAL seed should be deterministic");
}

#[test]
fn test_state_persistence() {
    // Test that RNG state can be saved and restored
    let mut rng = BalatroRng::new(SeedType::String("PERSISTENT".to_string()));

    // Generate some values to advance the state
    for i in 0..10 {
        rng.pseudoseed(&format!("key_{}", i));
    }

    // Save the state
    let state = rng.state().clone();
    let serialized = serde_json::to_string(&state).unwrap();

    // Generate more values
    let next_seed = rng.pseudoseed("continuation");

    // Restore the state
    let restored_state: PseudorandomState = serde_json::from_str(&serialized).unwrap();
    let mut restored_rng = BalatroRng::from_state(restored_state);

    // Should generate the same next value
    let restored_seed = restored_rng.pseudoseed("continuation");
    assert_eq!(next_seed, restored_seed, "Restored state should continue identically");
}

#[test]
fn test_probability_checks() {
    let mut rng = BalatroRng::new(SeedType::Numeric(24680));

    // Test extreme probabilities
    assert!(rng.probability_check(1.0, 123), "Probability 1.0 should always be true");
    assert!(!rng.probability_check(0.0, 123), "Probability 0.0 should always be false");

    // Test deterministic behavior
    let seed = 456;
    let result1 = rng.probability_check(0.5, seed);
    let result2 = rng.probability_check(0.5, seed);
    assert_eq!(result1, result2, "Same seed should produce same probability result");
}

#[test]
fn test_weighted_choice_distribution() {
    let mut rng = BalatroRng::new(SeedType::Numeric(86420));

    let choices = vec![
        ("common", 70.0),
        ("uncommon", 25.0),
        ("rare", 4.0),
        ("legendary", 1.0),
    ];

    let seed = 789;
    let choice = rng.weighted_choice(&choices, seed);
    assert!(choice.is_some());

    let choice_val = choice.unwrap();
    assert!(choices.iter().any(|(item, _)| item == choice_val));

    // Test empty choices
    let empty_choices: Vec<(&str, f64)> = vec![];
    let empty_result = rng.weighted_choice(&empty_choices, seed);
    assert!(empty_result.is_none());
}

#[test]
fn test_die_rolls() {
    let mut rng = BalatroRng::new(SeedType::Numeric(11111));

    // Test 6-sided die
    for i in 0..100 {
        let roll = rng.roll_die(6, i);
        assert!(roll >= 1 && roll <= 6, "6-sided die should roll 1-6, got {}", roll);
    }

    // Test 20-sided die
    for i in 0..100 {
        let roll = rng.roll_die(20, i);
        assert!(roll >= 1 && roll <= 20, "20-sided die should roll 1-20, got {}", roll);
    }

    // Test deterministic behavior
    let seed = 999;
    let roll1 = rng.roll_die(6, seed);
    let roll2 = rng.roll_die(6, seed);
    assert_eq!(roll1, roll2, "Same seed should produce same die roll");
}

#[test]
fn test_seed_generation() {
    // Test that generated seeds are valid
    let seed1 = BalatroRng::generate_starting_seed();
    let seed2 = BalatroRng::generate_starting_seed();

    assert_ne!(seed1, seed2, "Generated seeds should be different");
    assert_eq!(seed1.len(), 8, "Generated seed should be 8 characters");
    assert_eq!(seed2.len(), 8, "Generated seed should be 8 characters");

    // Test that generated seeds only contain valid characters
    let valid_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    for c in seed1.chars() {
        assert!(valid_chars.contains(c), "Generated seed should only contain valid characters");
    }
}

#[test]
fn test_balatro_specific_scenarios() {
    // Test scenarios that are specific to Balatro's usage patterns
    let mut rng = BalatroRng::new(SeedType::String("BALATRO_TEST".to_string()));

    // Test ante progression
    let mut ante_seeds = Vec::new();
    for ante in 1..=8 {
        let seed = rng.get_card_rng("rarity", ante, Some("joker"));
        ante_seeds.push(seed);
    }

    // All ante seeds should be different
    for i in 0..ante_seeds.len() {
        for j in i + 1..ante_seeds.len() {
            assert_ne!(ante_seeds[i], ante_seeds[j], "Different antes should produce different seeds");
        }
    }

    // Test reroll behavior
    let mut reroll_seeds = Vec::new();
    for reroll in 0..5 {
        let seed = rng.get_shop_rng(1, reroll);
        reroll_seeds.push(seed);
    }

    // All reroll seeds should be different
    for i in 0..reroll_seeds.len() {
        for j in i + 1..reroll_seeds.len() {
            assert_ne!(reroll_seeds[i], reroll_seeds[j], "Different rerolls should produce different seeds");
        }
    }
}

#[test]
fn test_edge_cases() {
    let mut rng = BalatroRng::new(SeedType::Numeric(0));

    // Test with zero seed
    let val = rng.pseudorandom(SeedType::Numeric(0), Some(1), Some(10));
    assert!(val >= 1.0 && val <= 10.0);

    // Test with very large seed
    let val = rng.pseudorandom(SeedType::Numeric(u64::MAX), Some(1), Some(10));
    assert!(val >= 1.0 && val <= 10.0);

    // Test empty string seed
    let val = rng.pseudorandom(SeedType::String("".to_string()), Some(1), Some(10));
    assert!(val >= 1.0 && val <= 10.0);

    // Test single element collection
    let collection = vec!["only"];
    let element = rng.pseudorandom_element(&collection, 123);
    assert_eq!(element, Some(&"only"));

    // Test empty collection
    let empty_collection: Vec<&str> = vec![];
    let element = rng.pseudorandom_element(&empty_collection, 123);
    assert_eq!(element, None);
}

#[test]
fn test_lua_compatibility_patterns() {
    // Test patterns that should match Lua's behavior
    let mut rng = BalatroRng::new(SeedType::Numeric(42));

    // Test that single max parameter works like Lua (1 to max)
    let val = rng.pseudorandom(SeedType::Numeric(999), Some(10), None);
    assert!(val >= 1.0 && val <= 10.0, "Single max should work like Lua math.random(n)");

    // Test that no parameters work like Lua (0 to 1)
    let val = rng.pseudorandom(SeedType::Numeric(999), None, None);
    assert!(val >= 0.0 && val < 1.0, "No parameters should work like Lua math.random()");

    // Test that min/max parameters work like Lua (min to max)
    let val = rng.pseudorandom(SeedType::Numeric(999), Some(5), Some(15));
    assert!(val >= 5.0 && val <= 15.0, "Min/max should work like Lua math.random(min, max)");
}