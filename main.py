#!/usr/bin/env python3
"""
Networked Pong Game - Main Entry Point

This is a distributed Pong game that automatically discovers other players
on the local network and elects a leader using the Bully algorithm.

Usage:
    python main.py

Controls:
    - Arrow keys or W/S: Move paddle up/down
    - ESC: Quit game

The first player to start becomes the leader. Additional players will
automatically discover and join the game. If the leader disconnects,
a new leader is elected automatically.
"""

import sys
import argparse
from game import NetworkedStrikerGame

def main():
    parser = argparse.ArgumentParser(description='Networked Pong Game')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug output')
    parser.add_argument('--port', type=int, default=15243,
                       help='Network port to use (default: 15243)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  NETWORKED PONG GAME")
    print("=" * 60)
    print("This game automatically discovers other players on your local network.")
    print("The first player becomes the leader, others join automatically.")
    print("If the leader disconnects, a new leader is elected.")
    print()
    print("Controls:")
    print("  Arrow keys or W/S: Move paddle")
    print("  ESC: Quit game")
    print()
    print("Starting game...")
    print("=" * 60)
    
    # Create and start the game
    game = NetworkedStrikerGame()
    
    try:
        game.start()
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("Game interrupted by user. Shutting down...")
        game.stop()
    except Exception as e:
        print(f"\nError occurred: {e}")
        game.stop()
        sys.exit(1)
    
    print("Game ended. Goodbye!")

if __name__ == "__main__":
    main()