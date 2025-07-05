#!/usr/bin/env python3
"""
Send commands to BalatroMCP via the event bus
"""

import json
import sys

import requests


def send_command(action, params=None):
    """Send a command to the BalatroMCP mod"""
    command = {
        "type": "COMMAND",
        "source": "AI_Agent",
        "action": action,
        "params": params or {},
    }

    try:
        response = requests.post(
            "http://localhost:8080/api/v1/commands",
            json=command,
            headers={"Content-Type": "application/json"},
        )
        print(f"Sent command: {action}")
        print(f"Response: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending command: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python send_command.py <action> [params_json]")
        print("\nAvailable actions:")
        print('  navigate_menu - params: {"action": "play"}')
        print("  start_new_run")
        print('  select_deck - params: {"deck": "Red Deck"}')
        print('  select_stake - params: {"stake": 1}')
        print("  play_hand")
        print("  discard")
        print("  skip_shop")
        print("  select_small_blind")
        return

    action = sys.argv[1]
    params = None

    if len(sys.argv) > 2:
        try:
            params = json.loads(sys.argv[2])
        except:
            print("Invalid JSON for params")
            return

    send_command(action, params)


if __name__ == "__main__":
    main()
