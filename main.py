#!/usr/bin/env python3
"""
Networked Pong Game - Main Entry Point (ZeroMQ Version)

This is a distributed Pong game using ZeroMQ for reliable messaging.
It automatically discovers other players on the local network and 
elects a leader using the Bully algorithm.

Usage:
    python main.py

Requirements:
    pip install pygame pyzmq

Features:
    - ZeroMQ PUB-SUB pattern for game state broadcasting
    - ZeroMQ REQ-REP pattern for discovery and elections  
    - ZeroMQ PUSH-PULL pattern for player inputs
    - Automatic leader election using Bully algorithm
    - Real-time game synchronization

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
    parser = argparse.ArgumentParser(description='Networked Pong Game (ZeroMQ)')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug output')
    parser.add_argument('--port', type=int, default=15240,
                       help='Base network port to use (default: 15240)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  NETWORKED PONG GAME - ZeroMQ VERSION")
    print("=" * 60)
    print("This game uses ZeroMQ for reliable distributed messaging.")
    print("It automatically discovers other players on your local network.")
    print("The first player becomes the leader, others join automatically.")
    print("If the leader disconnects, a new leader is elected.")
    print()
    print("ZeroMQ Communication Patterns:")
    print("  PUB-SUB: Game state broadcasting")
    print("  REQ-REP: Discovery and elections")
    print("  PUSH-PULL: Player input messages")
    print()
    print("Controls:")
    print("  Arrow keys or W/S: Move paddle")
    print("  ESC: Quit game")
    print()
    print("Requirements:")
    print("  pip install pygame pyzmq")
    print()
    print("Starting ZeroMQ game...")
    print("=" * 60)
    
    # Create and start the game
    game = NetworkedStrikerGame()
    
    try:
        game.start()
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("Game interrupted by user. Shutting down ZeroMQ...")
        game.stop()
    except Exception as e:
        print(f"\nError occurred: {e}")
        game.stop()
        sys.exit(1)
    
    print("ZeroMQ game ended. Goodbye!")

if __name__ == "__main__":
    main()