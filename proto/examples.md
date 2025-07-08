# Protocol Buffer Examples for Balatro Events

This document provides example messages for testing and understanding the Balatro event schemas.

## Game State Event Example

```json
{
  "base": {
    "phase": "PLAY_HAND",
    "score": 2500,
    "money": 35,
    "handsRemaining": 3,
    "discardsRemaining": 2,
    "blind": {
      "name": "The Hook",
      "requiredScore": 5000,
      "blindType": "boss",
      "modifiers": {
        "effect": "Discards 2 random cards per hand played"
      }
    },
    "sessionId": "game_123456"
  },
  "jokers": [
    {
      "id": "j_001",
      "name": "Joker",
      "position": 0,
      "params": {
        "mult": 4.0
      },
      "isDebuffed": false,
      "edition": "foil"
    },
    {
      "id": "j_002", 
      "name": "Mime",
      "position": 1,
      "params": {
        "retrigger": 1.0
      },
      "isDebuffed": false
    }
  ],
  "hand": [
    {
      "id": "c_h_a",
      "suit": "Hearts",
      "rank": "A",
      "enhancement": "gold",
      "seal": "red",
      "edition": "polychrome",
      "isDebuffed": false,
      "position": 0
    },
    {
      "id": "c_h_k",
      "suit": "Hearts", 
      "rank": "K",
      "position": 1
    }
  ],
  "score": {
    "chips": 35,
    "mult": 4.0,
    "total": 140,
    "handType": "pair",
    "handLevel": 2,
    "scoringCards": ["c_h_a", "c_d_a"]
  },
  "round": 3,
  "ante": 2,
  "phase": "PLAY_HAND",
  "consumables": [
    {
      "id": "tarot_001",
      "type": "tarot",
      "name": "The Fool",
      "properties": {
        "effect": "Creates a copy of the last played hand"
      }
    }
  ],
  "vouchers": ["Overstock", "Clearance Sale"],
  "stake": "red",
  "deckType": "red_deck"
}
```

## Trigger Event Example

```json
{
  "triggerId": "trig_001",
  "sourceId": "j_001",
  "sourceType": "joker",
  "triggerType": "played",
  "effects": [
    {
      "effectType": "add_mult",
      "value": 4.0,
      "target": "hand"
    }
  ],
  "timestamp": "2024-01-15T10:30:45.123Z",
  "context": {
    "phase": "scoring",
    "playedCards": ["c_h_a", "c_h_k", "c_h_q", "c_h_j", "c_h_10"],
    "scoredCards": ["c_h_a", "c_h_k", "c_h_q", "c_h_j", "c_h_10"],
    "handType": "flush",
    "repetition": 0,
    "isBossBlind": true
  },
  "causedTriggers": ["trig_002", "trig_003"]
}
```

## Play Hand Action Example

```json
{
  "actionId": "act_001",
  "actionType": "play_hand",
  "timestamp": "2024-01-15T10:30:44.000Z",
  "correlationId": "session_123456",
  "playHand": {
    "cardIds": ["c_h_a", "c_h_k", "c_h_q", "c_h_j", "c_h_10"],
    "expectedHandType": "flush"
  }
}
```

## Shop Action Example

```json
{
  "actionId": "act_002",
  "actionType": "shop",
  "timestamp": "2024-01-15T10:32:00.000Z",
  "correlationId": "session_123456",
  "shop": {
    "type": "BUY",
    "itemId": "shop_joker_001",
    "expectedCost": 6
  }
}
```

## Cascade Event Example

```json
{
  "initialTrigger": "trig_001",
  "triggerChain": ["trig_001", "trig_002", "trig_003", "trig_004"],
  "totalChipsAdded": 150,
  "totalMultFactor": 2.5,
  "cascadeDepth": 4,
  "startTime": "2024-01-15T10:30:45.123Z",
  "endTime": "2024-01-15T10:30:45.234Z"
}
```

## Round Summary Example

```json
{
  "round": 5,
  "ante": 2,
  "won": true,
  "finalScore": 8500,
  "requiredScore": 5000,
  "handsPlayed": 3,
  "cardsDiscarded": 8,
  "jokersTriggered": ["j_001", "j_002", "j_001", "j_003"],
  "moneyEarned": 15,
  "startTime": "2024-01-15T10:28:00.000Z",
  "endTime": "2024-01-15T10:32:30.000Z"
}
```

## Complex Trigger Chain Example

This shows how multiple jokers interact:

```json
{
  "triggers": [
    {
      "triggerId": "trig_001",
      "sourceId": "j_hack",
      "sourceType": "joker",
      "triggerType": "retrigger",
      "effects": [
        {
          "effectType": "retrigger_card",
          "value": 1.0,
          "target": "c_d_2"
        }
      ]
    },
    {
      "triggerId": "trig_002",
      "sourceId": "c_d_2",
      "sourceType": "card",
      "triggerType": "scored",
      "effects": [
        {
          "effectType": "add_chips",
          "value": 2.0
        }
      ],
      "context": {
        "repetition": 1
      }
    },
    {
      "triggerId": "trig_003",
      "sourceId": "j_blueprint",
      "sourceType": "joker",
      "triggerType": "copy",
      "effects": [
        {
          "effectType": "copy_joker",
          "target": "j_mult",
          "additionalParams": {
            "copiedMult": 4.0
          }
        }
      ]
    }
  ]
}
```

## Validation Examples

### Valid Play Hand Action
- Card IDs exist in current hand
- Number of cards is valid (1-5)
- Game phase is PLAY_HAND

### Invalid Shop Action
```json
{
  "error": "Insufficient funds",
  "action": {
    "shop": {
      "type": "BUY",
      "itemId": "expensive_joker",
      "expectedCost": 20
    }
  },
  "currentMoney": 5
}
```

### Action Validation Rules
```json
{
  "maxPlayCards": 5,
  "maxDiscardCards": 5,
  "canUseConsumables": true,
  "availableMoney": 35,
  "allowedActions": ["play_hand", "discard", "use_consumable"]
}
```