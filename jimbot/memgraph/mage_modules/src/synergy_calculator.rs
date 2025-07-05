//! High-performance synergy calculation algorithms

use std::collections::HashMap;

/// Card representation for fast operations
#[derive(Debug, Clone)]
pub struct Card {
    pub suit: String,
    pub rank: String,
    pub enhancement: Option<String>,
    pub base_chips: i32,
}

impl Card {
    pub fn rank_value(&self) -> i32 {
        match self.rank.as_str() {
            "A" => 14,
            "K" => 13,
            "Q" => 12,
            "J" => 11,
            _ => self.rank.parse().unwrap_or(0),
        }
    }
}

/// Joker attributes for synergy calculation
#[derive(Debug, Clone)]
pub struct JokerAttributes {
    pub name: String,
    pub rarity: String,
    pub cost: i32,
    pub base_chips: i32,
    pub base_mult: i32,
    pub scaling_type: String,
}

/// Synergy result between two jokers
#[derive(Debug)]
pub struct SynergyResult {
    pub joker1: String,
    pub joker2: String,
    pub strength: f64,
    pub synergy_type: String,
}

/// Calculate synergy score between two jokers
pub fn calculate_synergy(joker1: &JokerAttributes, joker2: &JokerAttributes) -> f64 {
    let mut score = 0.0;

    // Same scaling type creates strong synergy
    if joker1.scaling_type == joker2.scaling_type {
        score += 0.3;
    }

    // Complementary effects
    match (&joker1.scaling_type.as_str(), &joker2.scaling_type.as_str()) {
        ("multiplicative", "additive") | ("additive", "multiplicative") => score += 0.25,
        ("conditional", _) | (_, "conditional") => score += 0.15,
        _ => {}
    }

    // Rarity compatibility
    if joker1.rarity == joker2.rarity {
        score += 0.2;
    }

    // Cost efficiency
    let total_cost = joker1.cost + joker2.cost;
    if total_cost <= 15 {
        score += 0.15;
    } else if total_cost <= 25 {
        score += 0.1;
    }

    // Effect stacking
    if joker1.base_mult > 0 && joker2.base_mult > 0 {
        score += 0.2;
    }

    score.min(1.0) // Cap at 1.0
}

/// Calculate all pairwise synergies for a set of jokers
pub fn calculate_all_synergies(
    jokers: &[JokerAttributes],
    min_strength: f64,
) -> Vec<SynergyResult> {
    let mut results = Vec::new();

    for i in 0..jokers.len() {
        for j in (i + 1)..jokers.len() {
            let synergy = calculate_synergy(&jokers[i], &jokers[j]);
            
            if synergy >= min_strength {
                results.push(SynergyResult {
                    joker1: jokers[i].name.clone(),
                    joker2: jokers[j].name.clone(),
                    strength: synergy,
                    synergy_type: determine_synergy_type(&jokers[i], &jokers[j]),
                });
            }
        }
    }

    // Sort by strength descending
    results.sort_by(|a, b| b.strength.partial_cmp(&a.strength).unwrap());
    results
}

fn determine_synergy_type(joker1: &JokerAttributes, joker2: &JokerAttributes) -> String {
    if joker1.scaling_type == joker2.scaling_type {
        "amplifying".to_string()
    } else if joker1.base_mult > 0 && joker2.base_mult > 0 {
        "multiplicative".to_string()
    } else {
        "complementary".to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_synergy_calculation() {
        let joker1 = JokerAttributes {
            name: "Blueprint".to_string(),
            rarity: "rare".to_string(),
            cost: 10,
            base_chips: 0,
            base_mult: 0,
            scaling_type: "copy".to_string(),
        };

        let joker2 = JokerAttributes {
            name: "Brainstorm".to_string(),
            rarity: "rare".to_string(),
            cost: 10,
            base_chips: 0,
            base_mult: 0,
            scaling_type: "copy".to_string(),
        };

        let synergy = calculate_synergy(&joker1, &joker2);
        assert!(synergy > 0.5); // Same type and rarity should have good synergy
    }
}