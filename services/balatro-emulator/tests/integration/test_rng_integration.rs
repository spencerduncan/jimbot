//! Integration tests for the Balatro RNG system
//!
//! These tests verify end-to-end RNG behavior in realistic game scenarios.

use balatro_emulator::utils::{BalatroRng, SeedType};
use std::collections::HashMap;

#[test]
fn test_full_game_sequence_deterministic() {
    // Simulate a full game sequence with deterministic RNG
    let seed = SeedType::String("INTEGRATION_TEST".to_string());
    let mut rng1 = BalatroRng::new(seed.clone());
    let mut rng2 = BalatroRng::new(seed);

    // Simulate deck shuffling for multiple antes
    for ante in 1..=8 {
        let shuffle_seed = rng1.get_card_rng("shuffle", ante, Some("deck"));
        let mut deck1: Vec<u32> = (1..=52).collect();
        rng1.pseudoshuffle(&mut deck1, shuffle_seed);

        let shuffle_seed2 = rng2.get_card_rng("shuffle", ante, Some("deck"));
        let mut deck2: Vec<u32> = (1..=52).collect();
        rng2.pseudoshuffle(&mut deck2, shuffle_seed2);

        assert_eq!(deck1, deck2, "Deck shuffles should be identical for ante {}", ante);
    }
}

#[test]
fn test_shop_generation_sequence() {
    // Test shop generation across multiple rerolls and antes
    let mut rng = BalatroRng::new(SeedType::String("SHOP_TEST".to_string()));
    
    let shop_items = vec!["joker_1", "joker_2", "joker_3", "booster_1", "booster_2"];
    let mut shop_history = HashMap::new();

    for ante in 1..=8 {
        for reroll in 0..5 {
            let shop_seed = rng.get_shop_rng(ante, reroll);
            let selected_item = rng.pseudorandom_element(&shop_items, shop_seed);
            
            let key = format!("ante_{}_reroll_{}", ante, reroll);
            shop_history.insert(key, selected_item.unwrap().to_string());
        }
    }

    // Verify that we have the expected number of shop states
    assert_eq!(shop_history.len(), 8 * 5, "Should have 40 shop states (8 antes × 5 rerolls)");

    // Verify deterministic behavior by recreating the same sequence
    let mut rng2 = BalatroRng::new(SeedType::String("SHOP_TEST".to_string()));
    let mut shop_history2 = HashMap::new();

    for ante in 1..=8 {
        for reroll in 0..5 {
            let shop_seed = rng2.get_shop_rng(ante, reroll);
            let selected_item = rng2.pseudorandom_element(&shop_items, shop_seed);
            
            let key = format!("ante_{}_reroll_{}", ante, reroll);
            shop_history2.insert(key, selected_item.unwrap().to_string());
        }
    }

    assert_eq!(shop_history, shop_history2, "Shop generation should be deterministic");
}

#[test]
fn test_joker_trigger_sequence() {
    // Test joker effects triggering over multiple rounds
    let mut rng = BalatroRng::new(SeedType::String("JOKER_TEST".to_string()));
    
    let jokers = vec!["joker_mime", "joker_juggler", "joker_drunkard", "joker_stone"];
    let mut trigger_results = Vec::new();

    for round in 1..=20 {
        for joker in &jokers {
            let trigger_seed = rng.get_joker_rng(joker, round);
            
            // Simulate different joker effects
            let effect_chance = rng.probability_check(0.25, trigger_seed);
            let effect_value = rng.pseudorandom(SeedType::Numeric(trigger_seed), Some(1), Some(10));
            
            trigger_results.push((joker.to_string(), round, effect_chance, effect_value));
        }
    }

    // Verify deterministic behavior
    let mut rng2 = BalatroRng::new(SeedType::String("JOKER_TEST".to_string()));
    let mut trigger_results2 = Vec::new();

    for round in 1..=20 {
        for joker in &jokers {
            let trigger_seed = rng2.get_joker_rng(joker, round);
            
            let effect_chance = rng2.probability_check(0.25, trigger_seed);
            let effect_value = rng2.pseudorandom(SeedType::Numeric(trigger_seed), Some(1), Some(10));
            
            trigger_results2.push((joker.to_string(), round, effect_chance, effect_value));
        }
    }

    assert_eq!(trigger_results, trigger_results2, "Joker triggers should be deterministic");
}

#[test]
fn test_card_enhancement_generation() {
    // Test card enhancement assignment across a full game
    let mut rng = BalatroRng::new(SeedType::String("ENHANCEMENT_TEST".to_string()));
    
    let enhancements = vec!["None", "Bonus", "Mult", "Wild", "Glass", "Steel", "Stone", "Gold", "Lucky"];
    let mut enhancement_distribution = HashMap::new();

    // Simulate card enhancement assignment for multiple antes
    for ante in 1..=8 {
        for card_index in 0..52 {
            let enhancement_seed = rng.get_card_rng("enhancement", ante, Some(&format!("card_{}", card_index)));
            let enhancement = rng.pseudorandom_element(&enhancements, enhancement_seed);
            
            let key = format!("ante_{}_card_{}", ante, card_index);
            enhancement_distribution.insert(key, enhancement.unwrap().to_string());
        }
    }

    // Verify that all enhancements are assigned
    assert_eq!(enhancement_distribution.len(), 8 * 52, "Should have 416 card enhancements");

    // Test deterministic behavior
    let mut rng2 = BalatroRng::new(SeedType::String("ENHANCEMENT_TEST".to_string()));
    let mut enhancement_distribution2 = HashMap::new();

    for ante in 1..=8 {
        for card_index in 0..52 {
            let enhancement_seed = rng2.get_card_rng("enhancement", ante, Some(&format!("card_{}", card_index)));
            let enhancement = rng2.pseudorandom_element(&enhancements, enhancement_seed);
            
            let key = format!("ante_{}_card_{}", ante, card_index);
            enhancement_distribution2.insert(key, enhancement.unwrap().to_string());
        }
    }

    assert_eq!(enhancement_distribution, enhancement_distribution2, "Enhancement assignment should be deterministic");
}

#[test]
fn test_cross_system_independence() {
    // Test that different game systems don't interfere with each other
    let mut rng = BalatroRng::new(SeedType::String("INDEPENDENCE_TEST".to_string()));
    
    // Generate seeds for different systems
    let shop_seed = rng.get_shop_rng(1, 0);
    let joker_seed = rng.get_joker_rng("test_joker", 1);
    let card_seed = rng.get_card_rng("rarity", 1, Some("joker"));
    
    // Generate values from these systems
    let shop_value = rng.pseudorandom(SeedType::Numeric(shop_seed), Some(1), Some(100));
    let joker_check = rng.probability_check(0.5, joker_seed);
    let card_options = vec!["common", "uncommon", "rare"];
    let card_choice = rng.pseudorandom_element(&card_options, card_seed);
    
    // Now test that generating the same seeds in different order produces the same results
    let mut rng2 = BalatroRng::new(SeedType::String("INDEPENDENCE_TEST".to_string()));
    
    // Generate in different order
    let joker_seed2 = rng2.get_joker_rng("test_joker", 1);
    let card_seed2 = rng2.get_card_rng("rarity", 1, Some("joker"));
    let shop_seed2 = rng2.get_shop_rng(1, 0);
    
    // Values should be the same regardless of order
    assert_eq!(shop_seed, shop_seed2, "Shop seeds should be independent of generation order");
    assert_eq!(joker_seed, joker_seed2, "Joker seeds should be independent of generation order");
    assert_eq!(card_seed, card_seed2, "Card seeds should be independent of generation order");
    
    let shop_value2 = rng2.pseudorandom(SeedType::Numeric(shop_seed2), Some(1), Some(100));
    let joker_check2 = rng2.probability_check(0.5, joker_seed2);
    let card_options2 = vec!["common", "uncommon", "rare"];
    let card_choice2 = rng2.pseudorandom_element(&card_options2, card_seed2);
    
    assert_eq!(shop_value, shop_value2, "Shop values should be independent");
    assert_eq!(joker_check, joker_check2, "Joker checks should be independent");
    assert_eq!(card_choice, card_choice2, "Card choices should be independent");
}

#[test]
fn test_state_save_load_mid_game() {
    // Test saving and loading state in the middle of a game
    let mut rng = BalatroRng::new(SeedType::String("SAVE_LOAD_TEST".to_string()));
    
    // Simulate part of a game
    let mut game_events = Vec::new();
    
    // Generate some initial events
    for i in 0..10 {
        let seed = rng.pseudoseed(&format!("event_{}", i));
        let value = rng.pseudorandom(SeedType::Numeric(seed), Some(1), Some(100));
        game_events.push((i, value));
    }
    
    // Save state
    let saved_state = rng.state().clone();
    
    // Continue the game
    for i in 10..20 {
        let seed = rng.pseudoseed(&format!("event_{}", i));
        let value = rng.pseudorandom(SeedType::Numeric(seed), Some(1), Some(100));
        game_events.push((i, value));
    }
    
    // Load the saved state and continue from there
    let mut loaded_rng = BalatroRng::from_state(saved_state);
    let mut loaded_events = Vec::new();
    
    // Continue from where we saved
    for i in 10..20 {
        let seed = loaded_rng.pseudoseed(&format!("event_{}", i));
        let value = loaded_rng.pseudorandom(SeedType::Numeric(seed), Some(1), Some(100));
        loaded_events.push((i, value));
    }
    
    // The continued events should match
    for i in 0..10 {
        assert_eq!(game_events[i + 10], loaded_events[i], "Loaded game should continue identically");
    }
}

#[test]
fn test_large_scale_performance() {
    // Test performance with large numbers of operations
    let mut rng = BalatroRng::new(SeedType::String("PERFORMANCE_TEST".to_string()));
    
    let start_time = std::time::Instant::now();
    
    // Simulate 10,000 operations
    for i in 0..10000 {
        let seed = rng.pseudoseed(&format!("perf_{}", i));
        let _value = rng.pseudorandom(SeedType::Numeric(seed), Some(1), Some(1000));
    }
    
    let elapsed = start_time.elapsed();
    
    // Should complete in a reasonable time (less than 1 second)
    assert!(elapsed.as_secs() < 1, "10,000 operations should complete in less than 1 second");
}

#[test]
fn test_seed_collision_resistance() {
    // Test that different keys produce different seeds
    let mut rng = BalatroRng::new(SeedType::String("COLLISION_TEST".to_string()));
    
    let mut seed_set = std::collections::HashSet::new();
    let mut collisions = 0;
    
    // Generate seeds for various patterns
    for ante in 1..=8 {
        for reroll in 0..10 {
            let seed = rng.get_shop_rng(ante, reroll);
            if !seed_set.insert(seed) {
                collisions += 1;
            }
        }
    }
    
    for joker_id in 0..100 {
        for trigger in 0..10 {
            let seed = rng.get_joker_rng(&format!("joker_{}", joker_id), trigger);
            if !seed_set.insert(seed) {
                collisions += 1;
            }
        }
    }
    
    for ante in 1..=8 {
        for pattern in &["rarity", "soul_", "front", "erratic"] {
            let seed = rng.get_card_rng(pattern, ante, Some("test"));
            if !seed_set.insert(seed) {
                collisions += 1;
            }
        }
    }
    
    // Should have very few collisions (less than 1% of total)
    let total_seeds = seed_set.len() + collisions;
    let collision_rate = collisions as f64 / total_seeds as f64;
    
    assert!(collision_rate < 0.01, "Collision rate should be less than 1%, got {:.2}%", collision_rate * 100.0);
}