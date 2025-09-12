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
        # Add ourselves as the first player
        game.add_player(network_manager.player_id)
    else:
        print("Discovering games...")
        if not network_manager.discover_and_join():
            print("No games found. Starting as host...")
            network_manager.start_as_host()
            # Add ourselves as the first player
            game.add_player(network_manager.player_id)
        else:
            # Add ourselves to the game when joining
            game.add_player(network_manager.player_id)
    
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
        
        # Sync players between network and game (only for clients using game state)
        if not network_manager.is_leader:
            latest_state = network_manager.get_latest_game_state()
            if latest_state and "players" in latest_state:
                # For clients, sync from the authoritative game state
                state_players = set(latest_state["players"].keys())
                current_players = set(game.players.keys())
                
                # Add new players
                for player_id in state_players - current_players:
                    game.add_player(player_id)
                
                # Remove disconnected players
                for player_id in current_players - state_players:
                    game.remove_player(player_id)
        else:
            # For leader, sync from network manager
            network_players = set(network_manager.get_players())
            current_players = set(game.players.keys())
            
            # Add new players
            for player_id in network_players - current_players:
                game.add_player(player_id)
            
            # Remove disconnected players  
            for player_id in current_players - network_players:
                game.remove_player(player_id)
        
        # Update game state (only if we're the leader)
        if network_manager.is_leader:
            # Get paddle input for this player if we're also playing
            if network_manager.player_id in game.players:
                paddle_input = gui.get_paddle_input()
                network_manager.player_inputs[network_manager.player_id] = paddle_input
            
            game.update(dt, network_manager.get_player_inputs())
            # Always broadcast game state for synchronization
            current_state = game.get_state()
            network_manager.broadcast_game_state(current_state)
        else:
            # Send our paddle input to leader
            paddle_input = gui.get_paddle_input()
            network_manager.send_paddle_input(paddle_input)
        
        # Update GUI with latest game state
        if network_manager.is_leader:
            # Leader uses their own authoritative game state
            gui.update(None)  # Don't override with network state
        else:
            # Clients use the game state from leader
            gui.update(network_manager.get_latest_game_state())
        gui.render()
    
    # Cleanup
    network_manager.shutdown()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()