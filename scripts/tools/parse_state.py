#!/usr/bin/env python3
import requests
import json
from bs4 import BeautifulSoup

# Get the HTML page
response = requests.get("http://localhost:8080")
soup = BeautifulSoup(response.text, "html.parser")

# Find the pre tag with JSON data
pre_tag = soup.find("pre")
if pre_tag:
    events_data = json.loads(pre_tag.text)

    # Find the latest GAME_STATE event
    game_state = None
    for batch in reversed(events_data):
        if "event" in batch and "events" in batch["event"]:
            # Each batch contains multiple events
            for event in reversed(batch["event"]["events"]):
                if event.get("type") == "GAME_STATE":
                    game_state = event.get("payload", {})
                    break
            if game_state:
                break

    if game_state:
        print("Current Game State:")
        print(f"Phase: {game_state.get('game_state', 'Unknown')}")
        print(f"Ante: {game_state.get('ante', 0)}")
        print(f"Money: ${game_state.get('money', 0)}")
        print(f"Hands remaining: {game_state.get('hands_remaining', 0)}")
        print(f"Discards remaining: {game_state.get('discards_remaining', 0)}")

        if "blind" in game_state and game_state["blind"]:
            print(f"\nBlind: {game_state['blind'].get('name', 'Unknown')}")
            print(f"Chips needed: {game_state['blind'].get('chips', 0)}")

        print("\nHand:")
        for i, card in enumerate(game_state.get("hand", [])):
            print(f"  {i}: {card['rank']} of {card['suit']}")

        print("\nJokers:")
        for joker in game_state.get("jokers", []):
            print(f"  - {joker['name']}")

        print("\nShop:")
        shop = game_state.get("shop_items", {})
        for key, item in shop.items():
            print(f"  {key}: {item.get('name', 'Unknown')} - ${item.get('cost', 0)}")
    else:
        print("No game state found")
