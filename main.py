import pygame
import sys
import argparse
from network import NetworkManager
from game import PongGame
from gui import GameGUI

def main():
    """Main entry point for the multiplayer Pong game."""
    parser = argparse.ArgumentParser(description='Multiplayer Pong Game')
    parser.add_argument('--host', action='store_true', help='Start as host')
    parser.add_argument('--discover', action='store_true', help='Discover and join existing game')
    args = parser.parse_args()
    
    # Initialize pygame
    pygame.init()
    
    # Create network manager and game instances
    network_manager = NetworkManager()
    game = PongGame()
    gui = GameGUI(game)
    
    # Start network discovery or hosting
    if args.host:
        print("Starting as host...")
        network_manager.start_as_host()
    else:
        print("Discovering games...")
        if not network_manager.discover_and_join():
            print("No games found. Starting as host...")
            network_manager.start_as_host()
    
    # Main game loop
    clock = pygame.time.Clock()
    running = True
    
    while running:
        dt = clock.tick(60) / 1000.0  # 60 FPS
        
        # Handle pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            gui.handle_event(event)
        
        # Process network messages
        network_manager.process_messages()
        
        # Update game state (only if we're the leader)
        if network_manager.is_leader:
            game.update(dt, network_manager.get_player_inputs())
            network_manager.broadcast_game_state(game.get_state())
        
        # Update GUI with latest game state
        gui.update(network_manager.get_latest_game_state())
        gui.render()
    
    # Cleanup
    network_manager.shutdown()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()