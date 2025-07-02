// JimBot Memgraph Initial Schema
// This script creates the core schema for the Balatro knowledge graph
// Execute with: mgconsole < init_schema.cypher

// Clear existing data (WARNING: Only use in development)
// MATCH (n) DETACH DELETE n;

// ==========================================
// Node Constraints and Indexes
// ==========================================

// Joker constraints and indexes
CREATE CONSTRAINT ON (j:Joker) ASSERT j.name IS UNIQUE;
CREATE INDEX ON :Joker(rarity);
CREATE INDEX ON :Joker(cost);
CREATE INDEX ON :Joker(scaling_type);

// Playing card constraints and indexes  
CREATE CONSTRAINT ON (c:PlayingCard) ASSERT (c.suit, c.rank) IS UNIQUE;
CREATE INDEX ON :PlayingCard(enhancement);
CREATE INDEX ON :PlayingCard(seal);

// Hand type constraints and indexes
CREATE CONSTRAINT ON (h:HandType) ASSERT h.name IS UNIQUE;
CREATE INDEX ON :HandType(level);
CREATE INDEX ON :HandType(plays);

// Strategy constraints and indexes
CREATE CONSTRAINT ON (s:Strategy) ASSERT s.name IS UNIQUE;
CREATE INDEX ON :Strategy(win_rate);
CREATE INDEX ON :Strategy(games_played);
CREATE INDEX ON :Strategy(ante_reached);

// Deck archetype indexes
CREATE INDEX ON :DeckArchetype(name);
CREATE INDEX ON :DeckArchetype(viability_score);

// Game state tracking
CREATE CONSTRAINT ON (g:GameSession) ASSERT g.session_id IS UNIQUE;
CREATE INDEX ON :GameSession(timestamp);
CREATE INDEX ON :GameSession(final_ante);
CREATE INDEX ON :GameSession(final_score);

// ==========================================
// Relationship Indexes
// ==========================================

// Synergy relationship indexes
CREATE INDEX ON :SYNERGIZES_WITH(strength);
CREATE INDEX ON :SYNERGIZES_WITH(win_rate);
CREATE INDEX ON :SYNERGIZES_WITH(synergy_type);

// Strategy relationships
CREATE INDEX ON :ENABLES_STRATEGY(importance);
CREATE INDEX ON :LEADS_TO(transition_rate);
CREATE INDEX ON :COUNTERS(severity);

// ==========================================
// Core Node Creation
// ==========================================

// Create standard playing cards
UNWIND [
    {suit: 'Hearts', ranks: ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']},
    {suit: 'Diamonds', ranks: ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']},
    {suit: 'Clubs', ranks: ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']},
    {suit: 'Spades', ranks: ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']}
] AS card_data
UNWIND card_data.ranks AS rank
CREATE (c:PlayingCard {
    suit: card_data.suit,
    rank: rank,
    enhancement: 'none',
    seal: 'none',
    base_chips: CASE 
        WHEN rank = 'A' THEN 11
        WHEN rank IN ['J', 'Q', 'K'] THEN 10
        ELSE toInteger(rank)
    END
});

// Create hand types
UNWIND [
    {name: 'High Card', base_chips: 5, base_mult: 1},
    {name: 'Pair', base_chips: 10, base_mult: 2},
    {name: 'Two Pair', base_chips: 20, base_mult: 2},
    {name: 'Three of a Kind', base_chips: 30, base_mult: 3},
    {name: 'Straight', base_chips: 30, base_mult: 4},
    {name: 'Flush', base_chips: 35, base_mult: 4},
    {name: 'Full House', base_chips: 40, base_mult: 4},
    {name: 'Four of a Kind', base_chips: 60, base_mult: 7},
    {name: 'Straight Flush', base_chips: 100, base_mult: 8},
    {name: 'Royal Flush', base_chips: 100, base_mult: 8},
    {name: 'Five of a Kind', base_chips: 120, base_mult: 12},
    {name: 'Flush House', base_chips: 140, base_mult: 14},
    {name: 'Flush Five', base_chips: 160, base_mult: 16}
] AS hand_data
CREATE (h:HandType {
    name: hand_data.name,
    base_chips: hand_data.base_chips,
    base_mult: hand_data.base_mult,
    level: 1,
    plays: 0
});

// Create deck archetypes
UNWIND [
    {name: 'Flush Build', description: 'Focus on single suit for flush hands'},
    {name: 'High Card', description: 'Maximize face card and ace values'},
    {name: 'Pair Paradise', description: 'Duplicate cards for pairs and sets'},
    {name: 'Straight Shooter', description: 'Sequential cards for straights'},
    {name: 'Balanced', description: 'Even distribution across suits and ranks'}
] AS archetype
CREATE (d:DeckArchetype {
    name: archetype.name,
    description: archetype.description,
    viability_score: 0.5
});

// ==========================================
// Sample Jokers (Common Tier)
// ==========================================

UNWIND [
    {
        name: 'Joker',
        rarity: 'common',
        cost: 2,
        base_mult: 4,
        base_chips: 0,
        description: '+4 Mult',
        scaling_type: 'none'
    },
    {
        name: 'Greedy Joker',
        rarity: 'common',
        cost: 5,
        base_mult: 4,
        base_chips: 0,
        description: 'Played cards with Diamond suit give +3 Mult when scored',
        scaling_type: 'conditional'
    },
    {
        name: 'Lusty Joker',
        rarity: 'common',
        cost: 5,
        base_mult: 4,
        base_chips: 0,
        description: 'Played cards with Heart suit give +3 Mult when scored',
        scaling_type: 'conditional'
    },
    {
        name: 'Wrathful Joker',
        rarity: 'common',
        cost: 5,
        base_mult: 4,
        base_chips: 0,
        description: 'Played cards with Spade suit give +3 Mult when scored',
        scaling_type: 'conditional'
    },
    {
        name: 'Gluttonous Joker',
        rarity: 'common',
        cost: 5,
        base_mult: 4,
        base_chips: 0,
        description: 'Played cards with Club suit give +3 Mult when scored',
        scaling_type: 'conditional'
    }
] AS joker_data
CREATE (j:Joker {
    name: joker_data.name,
    rarity: joker_data.rarity,
    cost: joker_data.cost,
    base_mult: joker_data.base_mult,
    base_chips: joker_data.base_chips,
    description: joker_data.description,
    scaling_type: joker_data.scaling_type,
    times_purchased: 0,
    total_score_contribution: 0
});

// ==========================================
// Sample Jokers (Uncommon Tier)
// ==========================================

UNWIND [
    {
        name: 'Fibonacci',
        rarity: 'uncommon',
        cost: 7,
        base_mult: 0,
        base_chips: 8,
        description: 'Each played Ace, 2, 3, 5, or 8 gives +8 Chips when scored',
        scaling_type: 'conditional'
    },
    {
        name: 'Even Steven',
        rarity: 'uncommon',
        cost: 8,
        base_mult: 4,
        base_chips: 0,
        description: 'Played cards with even rank give +4 Mult when scored',
        scaling_type: 'conditional'
    },
    {
        name: 'Odd Todd',
        rarity: 'uncommon',
        cost: 8,
        base_mult: 0,
        base_chips: 31,
        description: 'Played cards with odd rank give +31 Chips when scored',
        scaling_type: 'conditional'
    },
    {
        name: 'Scholar',
        rarity: 'uncommon',
        cost: 6,
        base_mult: 0,
        base_chips: 20,
        description: 'Played Aces give +20 Chips and +4 Mult when scored',
        scaling_type: 'conditional'
    }
] AS joker_data
CREATE (j:Joker {
    name: joker_data.name,
    rarity: joker_data.rarity,
    cost: joker_data.cost,
    base_mult: joker_data.base_mult,
    base_chips: joker_data.base_chips,
    description: joker_data.description,
    scaling_type: joker_data.scaling_type,
    times_purchased: 0,
    total_score_contribution: 0
});

// ==========================================
// Initial Synergy Relationships
// ==========================================

// Suit-based joker synergies
MATCH (j1:Joker), (j2:Joker)
WHERE j1.name IN ['Greedy Joker', 'Lusty Joker', 'Wrathful Joker', 'Gluttonous Joker']
AND j2.name IN ['Greedy Joker', 'Lusty Joker', 'Wrathful Joker', 'Gluttonous Joker']
AND j1.name <> j2.name
CREATE (j1)-[:SYNERGIZES_WITH {
    strength: 0.3,
    synergy_type: 'complementary',
    win_rate: 0.45,
    confidence: 0.0,
    games_tested: 0
}]->(j2);

// Fibonacci synergizes with Odd Todd
MATCH (j1:Joker {name: 'Fibonacci'}), (j2:Joker {name: 'Odd Todd'})
CREATE (j1)-[:SYNERGIZES_WITH {
    strength: 0.8,
    synergy_type: 'multiplicative',
    win_rate: 0.0,
    confidence: 0.0,
    games_tested: 0
}]->(j2);

// Scholar synergizes with high-value strategies
MATCH (j1:Joker {name: 'Scholar'}), (j2:Joker)
WHERE j2.name IN ['Fibonacci', 'Even Steven']
CREATE (j1)-[:SYNERGIZES_WITH {
    strength: 0.6,
    synergy_type: 'additive',
    win_rate: 0.0,
    confidence: 0.0,
    games_tested: 0
}]->(j2);

// ==========================================
// Card Requirements
// ==========================================

// Suit-based jokers require their respective suits
MATCH (j:Joker), (c:PlayingCard)
WHERE (j.name = 'Greedy Joker' AND c.suit = 'Diamonds')
   OR (j.name = 'Lusty Joker' AND c.suit = 'Hearts')
   OR (j.name = 'Wrathful Joker' AND c.suit = 'Spades')
   OR (j.name = 'Gluttonous Joker' AND c.suit = 'Clubs')
CREATE (j)-[:REQUIRES_CARD {
    condition: 'scored',
    quantity: 1,
    optimal_quantity: 5
}]->(c);

// Fibonacci requires specific ranks
MATCH (j:Joker {name: 'Fibonacci'}), (c:PlayingCard)
WHERE c.rank IN ['A', '2', '3', '5', '8']
CREATE (j)-[:REQUIRES_CARD {
    condition: 'scored',
    quantity: 1,
    optimal_quantity: 3
}]->(c);

// Even Steven requires even ranks
MATCH (j:Joker {name: 'Even Steven'}), (c:PlayingCard)
WHERE c.rank IN ['2', '4', '6', '8', '10']
CREATE (j)-[:REQUIRES_CARD {
    condition: 'scored',
    quantity: 1,
    optimal_quantity: 3
}]->(c);

// Odd Todd requires odd ranks
MATCH (j:Joker {name: 'Odd Todd'}), (c:PlayingCard)
WHERE c.rank IN ['A', '3', '5', '7', '9', 'J', 'K']
CREATE (j)-[:REQUIRES_CARD {
    condition: 'scored',
    quantity: 1,
    optimal_quantity: 3
}]->(c);

// Scholar requires Aces
MATCH (j:Joker {name: 'Scholar'}), (c:PlayingCard {rank: 'A'})
CREATE (j)-[:REQUIRES_CARD {
    condition: 'scored',
    quantity: 1,
    optimal_quantity: 4
}]->(c);

// ==========================================
// Initial Strategies
// ==========================================

UNWIND [
    {
        name: 'Flush Focus',
        description: 'Build towards flush-based hands',
        win_rate: 0.0,
        avg_score: 0,
        games_played: 0,
        ante_reached: 0.0
    },
    {
        name: 'High Value',
        description: 'Focus on face cards and multipliers',
        win_rate: 0.0,
        avg_score: 0,
        games_played: 0,
        ante_reached: 0.0
    },
    {
        name: 'Pair Builder',
        description: 'Maximize pairs and sets',
        win_rate: 0.0,
        avg_score: 0,
        games_played: 0,
        ante_reached: 0.0
    }
] AS strategy_data
CREATE (s:Strategy {
    name: strategy_data.name,
    description: strategy_data.description,
    win_rate: strategy_data.win_rate,
    avg_score: strategy_data.avg_score,
    games_played: strategy_data.games_played,
    ante_reached: strategy_data.ante_reached
});

// Link jokers to strategies
MATCH (j:Joker), (s:Strategy)
WHERE (j.name IN ['Greedy Joker', 'Lusty Joker', 'Wrathful Joker', 'Gluttonous Joker'] AND s.name = 'Flush Focus')
   OR (j.name IN ['Scholar', 'Even Steven'] AND s.name = 'High Value')
   OR (j.name IN ['Odd Todd', 'Fibonacci'] AND s.name = 'Pair Builder')
CREATE (j)-[:ENABLES_STRATEGY {
    importance: 0.7
}]->(s);

// ==========================================
// Schema Metadata
// ==========================================

// Track schema version
CREATE (m:SchemaMetadata {
    version: 1,
    created_at: datetime(),
    description: 'Initial JimBot Memgraph schema'
});

// Create schema documentation node
CREATE (d:SchemaDoc {
    node_types: ['Joker', 'PlayingCard', 'HandType', 'Strategy', 'DeckArchetype', 'GameSession'],
    relationship_types: ['SYNERGIZES_WITH', 'REQUIRES_CARD', 'COUNTERS', 'ENABLES_STRATEGY', 'LEADS_TO'],
    total_nodes: 0,
    total_relationships: 0
});

// Update counts
MATCH (n)
WITH count(n) as node_count
MATCH ()-[r]->()
WITH node_count, count(r) as rel_count
MATCH (d:SchemaDoc)
SET d.total_nodes = node_count,
    d.total_relationships = rel_count;

// Verify schema creation
MATCH (m:SchemaMetadata)
RETURN 'Schema version ' + toString(m.version) + ' created successfully at ' + toString(m.created_at) as result;