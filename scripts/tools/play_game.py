#!/usr/bin/env python3
"""
Automated game playing script for BalatroMCP
Sends multiple commands in batch for faster execution
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8080/api/v1/commands"


def send_command(command_type, payload=None):
    """Send a single command to the game"""
    data = {"type": command_type, "payload": payload or {}}
    try:
        response = requests.post(BASE_URL, json=data, timeout=1)
        return response.status_code == 200
    except:
        return False


def select_cards(positions):
    """Select multiple cards at once"""
    for pos in positions:
        send_command("select_card", {"position": pos})
        time.sleep(0.1)  # Small delay between selections


def play_flush_strategy():
    """Try to play flushes when possible"""
    # First, deselect all cards
    send_command("clear_selection")

    # Select hearts for flush attempt
    select_cards([1, 2, 4, 6, 0])  # Jack, 9, 5, 3 of Hearts + Queen

    # Play the hand
    send_command("play_hand")


def play_pair_strategy():
    """Look for and play pairs"""
    # This would need to analyze the hand first
    pass


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "flush":
            play_flush_strategy()
        elif sys.argv[1] == "select":
            # Allow selecting specific cards: python play_game.py select 0,1,2,3,4
            positions = [int(x) for x in sys.argv[2].split(",")]
            select_cards(positions)
        elif sys.argv[1] == "play":
            send_command("play_hand")
        elif sys.argv[1] == "discard":
            send_command("discard")
        elif sys.argv[1] == "clear":
            send_command("clear_selection")
    else:
        print("Usage: python play_game.py [flush|select positions|play|discard|clear]")
