//! Victory path analysis for optimal joker progression

use std::collections::{HashMap, VecDeque};

/// Represents a joker in the progression path
#[derive(Debug, Clone)]
pub struct PathJoker {
    pub name: String,
    pub cost: i32,
    pub rarity: String,
    pub ante_requirement: i32,
}

/// Represents a progression path from one joker to another
#[derive(Debug, Clone)]
pub struct ProgressionPath {
    pub jokers: Vec<PathJoker>,
    pub total_cost: i32,
    pub success_rate: f64,
    pub expected_ante: i32,
}

/// Configuration for path finding
pub struct PathConfig {
    pub starting_money: i32,
    pub target_ante: i32,
    pub max_depth: usize,
    pub min_success_rate: f64,
}

/// Find optimal progression paths within constraints
pub fn find_optimal_paths(
    jokers: &[PathJoker],
    transitions: &HashMap<String, Vec<(String, f64)>>, // joker -> [(target, win_rate)]
    config: PathConfig,
) -> Vec<ProgressionPath> {
    let mut paths = Vec::new();
    
    // Find all common jokers as starting points
    let starting_jokers: Vec<_> = jokers
        .iter()
        .filter(|j| j.rarity == "common" && j.cost <= config.starting_money)
        .collect();

    for start in starting_jokers {
        let mut queue = VecDeque::new();
        queue.push_back(vec![start.clone()]);

        while let Some(current_path) = queue.pop_front() {
            if current_path.len() >= config.max_depth {
                continue;
            }

            let last_joker = current_path.last().unwrap();
            let current_cost: i32 = current_path.iter().map(|j| j.cost).sum();

            // Check transitions from current joker
            if let Some(next_jokers) = transitions.get(&last_joker.name) {
                for (next_name, win_rate) in next_jokers {
                    if let Some(next_joker) = jokers.iter().find(|j| &j.name == next_name) {
                        let new_cost = current_cost + next_joker.cost;
                        
                        // Check budget constraint
                        if new_cost > config.starting_money {
                            continue;
                        }

                        // Check if we already have this joker in path (no cycles)
                        if current_path.iter().any(|j| j.name == next_joker.name) {
                            continue;
                        }

                        let mut new_path = current_path.clone();
                        new_path.push(next_joker.clone());

                        // Calculate path success rate
                        let path_success = calculate_path_success(&new_path, transitions);
                        
                        if path_success >= config.min_success_rate {
                            let expected_ante = calculate_expected_ante(&new_path);
                            
                            if expected_ante >= config.target_ante {
                                paths.push(ProgressionPath {
                                    jokers: new_path.clone(),
                                    total_cost: new_cost,
                                    success_rate: path_success,
                                    expected_ante,
                                });
                            }
                        }

                        queue.push_back(new_path);
                    }
                }
            }
        }
    }

    // Sort by success rate descending
    paths.sort_by(|a, b| b.success_rate.partial_cmp(&a.success_rate).unwrap());
    
    // Return top 10 paths
    paths.into_iter().take(10).collect()
}

fn calculate_path_success(
    path: &[PathJoker],
    transitions: &HashMap<String, Vec<(String, f64)>>,
) -> f64 {
    let mut success_rate = 1.0;

    for i in 0..path.len() - 1 {
        let from = &path[i].name;
        let to = &path[i + 1].name;

        if let Some(next_jokers) = transitions.get(from) {
            if let Some((_, win_rate)) = next_jokers.iter().find(|(name, _)| name == to) {
                success_rate *= win_rate;
            } else {
                success_rate *= 0.5; // Default transition probability
            }
        } else {
            success_rate *= 0.5;
        }
    }

    success_rate
}

fn calculate_expected_ante(path: &[PathJoker]) -> i32 {
    // Simple heuristic: later jokers help reach higher antes
    let base_ante = 4;
    let joker_contribution = path.len() as i32;
    let rarity_bonus: i32 = path
        .iter()
        .map(|j| match j.rarity.as_str() {
            "legendary" => 3,
            "rare" => 2,
            "uncommon" => 1,
            _ => 0,
        })
        .sum();

    base_ante + joker_contribution + rarity_bonus
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_path_finding() {
        let jokers = vec![
            PathJoker {
                name: "Joker".to_string(),
                cost: 2,
                rarity: "common".to_string(),
                ante_requirement: 0,
            },
            PathJoker {
                name: "Greedy Joker".to_string(),
                cost: 5,
                rarity: "common".to_string(),
                ante_requirement: 0,
            },
            PathJoker {
                name: "Lusty Joker".to_string(),
                cost: 7,
                rarity: "uncommon".to_string(),
                ante_requirement: 2,
            },
        ];

        let mut transitions = HashMap::new();
        transitions.insert(
            "Joker".to_string(),
            vec![("Greedy Joker".to_string(), 0.7)],
        );
        transitions.insert(
            "Greedy Joker".to_string(),
            vec![("Lusty Joker".to_string(), 0.8)],
        );

        let config = PathConfig {
            starting_money: 15,
            target_ante: 5,
            max_depth: 3,
            min_success_rate: 0.5,
        };

        let paths = find_optimal_paths(&jokers, &transitions, config);
        assert!(!paths.is_empty());
    }
}