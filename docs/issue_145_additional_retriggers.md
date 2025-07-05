# Additional Retrigger Optimization Analysis

## Extended Scenarios Beyond Mime/Steel

### Hack Joker Optimization
Hack retriggers cards with ranks 2, 3, 4, and 5. Common performance issues:
- Multiple Hack jokers (or copied via Blueprint/Brainstorm)
- Red seal on low-rank cards
- Combination with scoring enhancements (mult/bonus/lucky cards)

```rust
pub struct HackOptimization {
    hack_count: u32,
    target_cards: Vec<CardId>, // Cards with rank 2-5
    red_seal_targets: Vec<CardId>,
}

impl HackOptimization {
    pub fn calculate_retriggers(&self) -> HashMap<CardId, u32> {
        let mut retriggers = HashMap::new();
        
        for card in &self.target_cards {
            let base_triggers = self.hack_count;
            let multiplier = if self.red_seal_targets.contains(card) { 2 } else { 1 };
            retriggers.insert(*card, base_triggers * multiplier);
        }
        
        retriggers
    }
    
    pub fn apply_optimized(&self, cards: &[Card]) -> HandResult {
        let retriggers = self.calculate_retriggers();
        let mut total_mult = 1.0;
        let mut total_chips = 0;
        
        // Group cards by enhancement type for batch processing
        let mut mult_cards = vec![];
        let mut lucky_cards = vec![];
        let mut bonus_cards = vec![];
        
        for card in cards {
            if let Some(&count) = retriggers.get(&card.id) {
                match card.enhancement {
                    Enhancement::Mult => mult_cards.push((card, count)),
                    Enhancement::Lucky => lucky_cards.push((card, count)),
                    Enhancement::Bonus => bonus_cards.push((card, count)),
                    _ => {}
                }
            }
        }
        
        // Batch process mult cards
        if !mult_cards.is_empty() {
            let mult_per_card = 4.0;
            for (_, count) in mult_cards {
                // Use safe exponentiation for multiple triggers
                if count <= SAFE_EXPONENT_LIMIT as u32 {
                    total_mult *= (1.0 + mult_per_card).powi(count as i32);
                } else {
                    // Fall back to iterative
                    for _ in 0..count {
                        total_mult += mult_per_card;
                    }
                }
            }
        }
        
        // Batch process bonus cards (additive, safe to multiply)
        for (_, count) in bonus_cards {
            total_chips += 30 * count as i32;
        }
        
        HandResult { mult: total_mult, chips: total_chips }
    }
}
```

### Sock and Buskin Optimization
Sock and Buskin retriggers all played face cards. Performance issues arise with:
- Multiple face cards played (J, Q, K)
- Red seal face cards
- Combination with scoring jokers (e.g., Shoot the Moon for Queens)

```rust
pub struct SockBuskinOptimization {
    sock_buskin_count: u32,
    face_cards: Vec<CardId>,
    red_seal_faces: Vec<CardId>,
    queen_bonus_active: bool, // Shoot the Moon
}

impl SockBuskinOptimization {
    pub fn calculate_face_retriggers(&self) -> FaceCardRetriggers {
        let mut retriggers = FaceCardRetriggers::default();
        
        for card_id in &self.face_cards {
            let base = self.sock_buskin_count;
            let red_seal_mult = if self.red_seal_faces.contains(card_id) { 2 } else { 1 };
            let total = base * red_seal_mult;
            
            retriggers.add_retrigger(*card_id, total);
        }
        
        retriggers
    }
    
    pub fn apply_optimized(&self, played_cards: &[Card]) -> HandResult {
        let retriggers = self.calculate_face_retriggers();
        let mut total_mult = 1.0;
        
        // Special optimization for Shoot the Moon + Sock and Buskin
        if self.queen_bonus_active {
            let queen_count = played_cards.iter()
                .filter(|c| c.rank == Rank::Queen)
                .count();
            
            if queen_count > 0 {
                let queen_mult = 13.0;
                let total_queen_triggers = retriggers.get_queen_triggers();
                
                // Safe multiplication for reasonable trigger counts
                if total_queen_triggers <= SAFE_EXPONENT_LIMIT as u32 {
                    total_mult *= queen_mult.powi(total_queen_triggers as i32);
                } else {
                    // Chunked multiplication for large counts
                    total_mult *= apply_chunked_mult(queen_mult, total_queen_triggers);
                }
            }
        }
        
        HandResult { mult: total_mult, chips: 0 }
    }
}
```

### General Retrigger Optimization Framework

```rust
pub trait RetriggerOptimizer {
    fn can_optimize(&self, trigger_count: u32) -> bool;
    fn apply_optimized(&self, cards: &[Card], trigger_count: u32) -> EffectResult;
    fn apply_iterative(&self, cards: &[Card], trigger_count: u32) -> EffectResult;
}

pub struct RetriggerEngine {
    optimizers: HashMap<JokerType, Box<dyn RetriggerOptimizer>>,
    safe_threshold: u32,
}

impl RetriggerEngine {
    pub fn new() -> Self {
        let mut optimizers = HashMap::new();
        
        // Register optimizers for each retrigger joker
        optimizers.insert(JokerType::Mime, Box::new(MimeOptimizer));
        optimizers.insert(JokerType::Hack, Box::new(HackOptimizer));
        optimizers.insert(JokerType::SockAndBuskin, Box::new(SockBuskinOptimizer));
        optimizers.insert(JokerType::Dusk, Box::new(DuskOptimizer));
        optimizers.insert(JokerType::Seltzer, Box::new(SeltzerOptimizer));
        
        Self {
            optimizers,
            safe_threshold: SAFE_EXPONENT_LIMIT as u32,
        }
    }
    
    pub fn process_retriggers(&self, 
        joker: &Joker, 
        cards: &[Card], 
        count: u32
    ) -> EffectResult {
        if let Some(optimizer) = self.optimizers.get(&joker.joker_type) {
            if optimizer.can_optimize(count) && count <= self.safe_threshold {
                optimizer.apply_optimized(cards, count)
            } else {
                optimizer.apply_iterative(cards, count)
            }
        } else {
            // Fallback for non-optimized jokers
            self.apply_standard_retrigger(joker, cards, count)
        }
    }
}
```

### Testing Additional Scenarios

```rust
#[cfg(test)]
mod extended_tests {
    use super::*;
    
    #[test]
    fn test_hack_optimization() {
        // Test with 5 cards (2,3,4,5,A), 3 Hack effects via copying
        let cards = vec![
            create_card(Rank::Two, Some(Enhancement::Mult), Some(Seal::Red)),
            create_card(Rank::Three, Some(Enhancement::Mult), None),
            create_card(Rank::Four, Some(Enhancement::Lucky), None),
            create_card(Rank::Five, Some(Enhancement::Bonus), None),
            create_card(Rank::Ace, None, None), // Not affected by Hack
        ];
        
        let optimizer = HackOptimization {
            hack_count: 3, // Original + 2 copies
            target_cards: cards[0..4].iter().map(|c| c.id).collect(),
            red_seal_targets: vec![cards[0].id],
        };
        
        let result = optimizer.apply_optimized(&cards);
        
        // Verify calculations
        // Card 0: 3 hack * 2 red seal = 6 triggers of +4 mult
        // Card 1: 3 hack triggers of +4 mult
        // Card 3: 3 hack triggers of +30 chips
        assert!(result.mult > 1.0);
        assert_eq!(result.chips, 90); // 30 * 3 from bonus card
    }
    
    #[test]
    fn test_sock_buskin_queens() {
        // Test Sock and Buskin with Shoot the Moon
        let cards = vec![
            create_card(Rank::Queen, None, Some(Seal::Red)),
            create_card(Rank::Queen, None, None),
            create_card(Rank::King, None, None),
        ];
        
        let optimizer = SockBuskinOptimization {
            sock_buskin_count: 2, // Original + 1 copy
            face_cards: cards.iter().map(|c| c.id).collect(),
            red_seal_faces: vec![cards[0].id],
            queen_bonus_active: true,
        };
        
        let result = optimizer.apply_optimized(&cards);
        
        // Queen 0: 2 sock * 2 red seal = 4 triggers of x13
        // Queen 1: 2 sock triggers of x13
        // Total: 13^6
        let expected = 13.0_f64.powi(6);
        assert!((result.mult - expected).abs() < 1e-10);
    }
    
    #[test]
    fn test_floating_point_stability() {
        // Test that optimizations maintain accuracy across different scenarios
        let scenarios = vec![
            ("Mime + Steel", 1.5, 20),
            ("Hack + Mult", 5.0, 15),
            ("Sock + Queens", 13.0, 10),
        ];
        
        for (name, mult, count) in scenarios {
            let iterative = (0..count).fold(1.0, |acc, _| acc * mult);
            let optimized = mult.powi(count);
            let relative_error = (iterative - optimized).abs() / iterative;
            
            assert!(relative_error < 1e-12, 
                "{} failed: error {}", name, relative_error);
        }
    }
}
```

## Performance Comparison

| Scenario | Unoptimized | Optimized | Speedup |
|----------|-------------|-----------|---------|
| 14 Red Seal Steel Kings + 3 Mime | ~840 operations | ~5 operations | 168x |
| 5 Hack targets (4 red seal) | ~40 operations | ~8 operations | 5x |
| 3 Face cards + Sock & Buskin (2x) | ~18 operations | ~4 operations | 4.5x |
| Complex mixed retriggers | O(n×m×k) | O(n+m+k) | ~10-50x |

## Key Insights

1. **Batch Processing**: Group cards by enhancement type to apply effects in bulk
2. **Pre-calculation**: Calculate retrigger counts once, then apply effects
3. **Special Case Handling**: Optimize known synergies (e.g., Shoot the Moon + Sock and Buskin)
4. **Floating Point Awareness**: Use SAFE_EXPONENT_LIMIT consistently across all optimizers

## Additional Retrigger Jokers to Consider

- **Dusk**: Retriggers all cards in hand when final hand is played
- **Seltzer**: Retriggers all cards if played hand contains a Straight
- **Hanging Chad**: Retriggers first played card 2 additional times
- **Retriggered cards from Seals**: Purple Seal (on discard), Gold Seal (when held)

Each of these can benefit from similar optimization strategies, particularly when combined with Blueprint/Brainstorm copying effects.