# Multiplayer Pong Game

A distributed multiplayer Pong game that supports 3-6 players on a local network. The game field shape adapts to the number of players (triangle for 3 players, square for 4, pentagon for 5, etc.).

## Features

- **Dynamic Game Field**: Game field shape changes based on number of players
- **Distributed Architecture**: Uses UDP for real-time communication and TCP for reliable connections
- **Leader Election**: Implements Bully algorithm for fault tolerance
- **Auto-discovery**: Players can automatically find and join games on the local network
- **Real-time Gameplay**: 60 FPS game loop with network synchronization

## Requirements

- Python 3.7+
- pygame 2.0+

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Start as Host
```bash
python main.py --host
```

### Join Existing Game
```bash
python main.py --discover
```

If no game is found, the client will automatically become a host.

### Controls

- **Mouse**: Move paddle position
- **Arrow Keys**: Fine adjustment of paddle position

## Network Architecture

- **Port**: 15243 (UDP and TCP)
- **Discovery**: UDP broadcast for game discovery
- **Game State**: UDP multicast for real-time game state
- **Player Join**: TCP for reliable player connection
- **Leader Election**: Bully algorithm for fault tolerance

## Game Rules

- Minimum 3 players required to start
- Maximum 6 players supported
- Ball bounces off paddles and game field edges
- Each player controls one paddle positioned around the game field perimeter
- Score increases when ball hits opponent's side

## File Structure

- `main.py`: Entry point and main game loop
- `network.py`: Network communication (UDP/TCP, discovery, leader election)
- `game.py`: Game logic and state management  
- `gui.py`: Graphics and user interface using pygame
- `requirements.txt`: Python dependencies

## Protocol

The game uses JSON messages over UDP/TCP with the following message types:

- `DISCOVERY_REQUEST`: Find existing games
- `DISCOVERY_RESPONSE`: Response with game info
- `PLAYER_JOIN`: Join game notification
- `PADDLE_INPUT`: Real-time paddle position
- `GAME_STATE`: Complete game state broadcast
- `ELECTION`: Leader election message
- `ELECTION_OKAY`: Election response
- `NEW_LEADER`: New leader announcement