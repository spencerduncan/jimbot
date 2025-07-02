#!/usr/bin/env python3
"""
Test script for BalatroMCP integration with the test event receiver.
This simulates events that would come from the BalatroMCP mod.
"""

import json
import time
import requests
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8080"

def send_event(event_type, game_state, metadata=None):
    """Send a single event to the test receiver"""
    event = {
        "event_type": event_type,
        "timestamp": time.time(),
        "game_state": game_state,
        "metadata": metadata or {}
    }
    
    response = requests.post(f"{BASE_URL}/events", json=event)
    print(f"Sent {event_type}: {response.status_code}")
    return response.json()

def send_batch(events):
    """Send a batch of events"""
    batch = {
        "events": events,
        "batch_id": f"test_batch_{int(time.time())}",
        "source": "test_script"
    }
    
    response = requests.post(f"{BASE_URL}/events/batch", json=batch)
    print(f"Sent batch: {response.status_code}")
    return response.json()

def simulate_game_session():
    """Simulate a typical Balatro game session"""
    print("Starting game session simulation...")
    
    # Game start
    send_event("game_started", {
        "seed": "TEST123",
        "difficulty": 0,
        "deck": "Red Deck",
        "stakes": 1
    })
    
    time.sleep(0.5)
    
    # Round start
    send_event("round_started", {
        "round": 1,
        "ante": 1,
        "blind_type": "Small Blind",
        "target_chips": 300,
        "current_chips": 0,
        "hands_remaining": 4,
        "discards_remaining": 3
    })
    
    # Hand played
    batch_events = []
    for i in range(3):
        batch_events.append({
            "event_type": "hand_played",
            "timestamp": time.time() + i * 0.1,
            "game_state": {
                "round": 1,
                "hand_type": "Pair",
                "base_chips": 30,
                "base_mult": 2,
                "final_chips": 60,
                "hands_remaining": 3 - i
            },
            "metadata": {
                "cards_played": ["AS", "AH"],
                "jokers_triggered": ["Joker 1"]
            }
        })
    
    send_batch(batch_events)
    
    time.sleep(0.5)
    
    # Round completed
    send_event("round_completed", {
        "round": 1,
        "ante": 1,
        "success": True,
        "final_chips": 350,
        "target_chips": 300,
        "money_earned": 3
    })
    
    # Shop phase
    send_event("shop_entered", {
        "money": 7,
        "shop_items": [
            {"type": "joker", "name": "Joker", "cost": 3},
            {"type": "planet", "name": "Jupiter", "cost": 3},
            {"type": "tarot", "name": "The Fool", "cost": 3}
        ]
    })
    
    time.sleep(0.5)
    
    # Purchase
    send_event("item_purchased", {
        "item_type": "joker",
        "item_name": "Joker",
        "cost": 3,
        "money_remaining": 4
    })
    
    # Game over
    send_event("game_ended", {
        "final_round": 3,
        "final_ante": 2,
        "final_score": 1250,
        "victory": False,
        "defeat_reason": "Failed Boss Blind"
    })
    
    print("Game session simulation complete!")

def check_stats():
    """Check current statistics"""
    response = requests.get(f"{BASE_URL}/stats")
    stats = response.json()
    print("\nCurrent Statistics:")
    print(f"Total Events: {stats['total_events']}")
    print(f"Events by Type: {json.dumps(stats['events_by_type'], indent=2)}")
    print(f"Uptime: {stats['uptime']:.1f} seconds")

def view_recent_events(limit=5):
    """View recent events"""
    response = requests.get(f"{BASE_URL}/events/recent", params={"limit": limit})
    data = response.json()
    print(f"\nRecent Events ({data['count']} total):")
    for event in data['events'][:limit]:
        event_data = event['data']
        print(f"  - {event_data['event_type']} at {datetime.fromtimestamp(event_data['timestamp'])}")

def main():
    """Run integration test"""
    print("BalatroMCP Integration Test")
    print("===========================")
    
    # Check health
    try:
        response = requests.get(f"{BASE_URL}/health")
        health = response.json()
        print(f"Server Status: {health['status']}")
        print(f"Redis: {health['redis']}")
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to test event receiver!")
        print("Make sure docker-compose is running:")
        print("  docker-compose -f docker-compose.minimal.yml up -d")
        return
    
    # Run simulation
    simulate_game_session()
    
    # Check results
    check_stats()
    view_recent_events()
    
    print("\nIntegration test complete!")

if __name__ == "__main__":
    main()