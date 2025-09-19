import pygame
import threading
import time
import json
from typing import Dict, List
from network import NetworkManager, MessageType, Player

# Font that is used to render the text
pygame.font.init()
font20 = pygame.font.Font(None, 20)
font30 = pygame.font.Font(None, 30)

# RGB values of standard colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)

# Basic parameters of the screen
WIDTH, HEIGHT = 900, 600
FPS = 60

# Game colors for different players
PLAYER_COLORS = [GREEN, RED, BLUE, YELLOW, CYAN, MAGENTA]

class NetworkedStrikerGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Networked Pong")
        self.clock = pygame.time.Clock()
        
        # Network setup
        self.network = NetworkManager(on_message_callback=self._handle_network_message)
        
        # Game state
        self.running = False
        self.players: Dict[str, Dict] = {}
        self.ball_pos = [WIDTH // 2, HEIGHT // 2]
        self.ball_vel = [5, 5]
        self.ball_radius = 7
        
        # Local player input
        self.local_paddle_pos = HEIGHT // 2 - 50
        self.paddle_speed = 7
        
        # Game update rate
        self.last_game_update = time.time()
        self.last_input_send = time.time()
        self.game_update_interval = 1.0 / 60.0  # 60 FPS
        self.input_send_interval = 1.0 / 30.0   # 30 FPS for input
        
        # Paddle dimensions
        self.paddle_width = 10
        self.paddle_height = 100
        
    def start(self):
        """Start the game and network"""
        print("Starting networked Pong game...")
        self.running = True
        
        # Start network
        self.network.start()
        
        # Wait a bit for network discovery
        time.sleep(3)
        
        print(f"Network status:")
        print(f"  Player ID: {self.network.player_id[:8]}")
        print(f"  Local IP: {self.network.local_ip}")
        print(f"  Is Leader: {self.network.is_network_leader()}")
        print(f"  Players in network: {self.network.get_player_count()}")
        
        # Initialize game state
        self._initialize_game()
        
        # Start game loop
        self._game_loop()
    
    def stop(self):
        """Stop the game and network"""
        self.running = False
        self.network.stop()
        pygame.quit()
    
    def _initialize_game(self):
        """Initialize game state based on network players"""
        players = self.network.get_players()
        self.players = {}
        
        print(f"Initializing game with {len(players)} players")
        
        # Calculate paddle positions based on number of players
        num_players = len(players)
        if num_players == 0:
            return
        
        # Sort players by ID for consistent positioning
        sorted_players = sorted(players, key=lambda p: p.id)
        
        # Assign positions to players
        for i, player in enumerate(sorted_players):
            color_index = i % len(PLAYER_COLORS)
            
            if num_players <= 2:
                # Traditional pong setup - left and right
                if i == 0:
                    x = 20  # Left side
                else:
                    x = WIDTH - 30  # Right side
                y = HEIGHT // 2 - self.paddle_height // 2
            else:
                # Multiple players - distribute around edges
                if i == 0:  # Left
                    x, y = 20, HEIGHT // 2 - self.paddle_height // 2
                elif i == 1:  # Right  
                    x, y = WIDTH - 30, HEIGHT // 2 - self.paddle_height // 2
                elif i == 2:  # Top
                    x, y = WIDTH // 2 - self.paddle_width // 2, 20
                elif i == 3:  # Bottom
                    x, y = WIDTH // 2 - self.paddle_width // 2, HEIGHT - 30
                else:
                    # Additional players in corners or middle positions
                    x, y = 50 + (i-4) * 100, HEIGHT // 2 - self.paddle_height // 2
            
            self.players[player.id] = {
                'ip': player.ip,
                'x': x,
                'y': y,
                'color': PLAYER_COLORS[color_index],
                'score': 0,
                'paddle_pos': y,
                'is_local': player.id == self.network.player_id
            }
            
            # Set local paddle position if this is the local player
            if player.id == self.network.player_id:
                self.local_paddle_pos = y
        
        print(f"Initialized game:")
        for pid, player in self.players.items():
            print(f"  Player {pid[:8]}: pos=({player['x']}, {player['y']}) local={player['is_local']}")
    
    def _handle_network_message(self, message: dict, sender_ip: str):
        """Handle network messages"""
        msg_type = message.get("type")
        data = message.get("data", {})
        
        if msg_type == MessageType.PADDLE_INPUT.value:
            self._handle_paddle_input(data)
        elif msg_type == MessageType.GAME_STATE.value:
            self._handle_game_state(data)
        elif msg_type == MessageType.DISCOVERY_RESPONSE.value:
            print("New player joined network")
            # Re-initialize when players change
            time.sleep(0.1)  # Small delay to ensure network state is updated
            self._initialize_game()
        elif msg_type == MessageType.PLAYER_JOIN.value:
            print(f"Player joined: {data.get('playerId', 'unknown')[:8]}")
            # Re-initialize when players change
            time.sleep(0.1)  # Small delay to ensure network state is updated
            self._initialize_game()
        elif msg_type == MessageType.PLAYER_LEAVE.value:
            print(f"Player left: {data.get('playerId', 'unknown')[:8]}")
            # Re-initialize when players change
            time.sleep(0.1)  # Small delay to ensure network state is updated
            self._initialize_game()
    
    def _handle_paddle_input(self, data: dict):
        """Handle paddle input from network player"""
        player_id = data.get("playerId")
        paddle_pos = data.get("paddlePosition")
        
        if player_id in self.players:
            self.players[player_id]['paddle_pos'] = paddle_pos
            # Debug output for leader receiving paddle input
            if self.network.is_network_leader():
                print(f"Leader received paddle input from {player_id[:8]}: {paddle_pos}")
    
    def _handle_game_state(self, data: dict):
        """Handle game state update from leader"""
        if self.network.is_network_leader():
            return  # Leaders don't process their own game state
            
        # Update ball position
        ball_data = data.get("ball", {})
        if ball_data:
            self.ball_pos = [ball_data.get("x", self.ball_pos[0]), ball_data.get("y", self.ball_pos[1])]
        
        # Update paddle positions
        paddle_positions = data.get("paddles", {})
        for player_id, pos in paddle_positions.items():
            if player_id in self.players and not self.players[player_id]['is_local']:
                self.players[player_id]['paddle_pos'] = pos
        
        # Update scores
        scores = data.get("scores", {})
        for player_id, score in scores.items():
            if player_id in self.players:
                self.players[player_id]['score'] = score
    
    def _send_paddle_input(self):
        """Send local paddle input to leader"""
        if self.network.is_network_leader():
            return  # Leader handles input locally
            
        leader_id, leader_ip = self.network.get_leader_info()
        if not leader_ip:
            return
        
        # Send paddle position
        self.network.send_message(
            MessageType.PADDLE_INPUT,
            {
                "playerId": self.network.player_id,
                "paddlePosition": self.local_paddle_pos
            },
            leader_ip
        )
        # Debug output for sending paddle input
        # print(f"Sent paddle input to leader: {self.local_paddle_pos}")
    
    def _broadcast_game_state(self):
        """Broadcast game state to all players (leader only)"""
        if not self.network.is_network_leader():
            return
            
        # Prepare game state data
        game_state = {
            "ball": {
                "x": self.ball_pos[0],
                "y": self.ball_pos[1]
            },
            "paddles": {pid: p['paddle_pos'] for pid, p in self.players.items()},
            "scores": {pid: p['score'] for pid, p in self.players.items()}
        }
        
        # Send to all non-leader players
        self.network.send_message(MessageType.GAME_STATE, game_state)
        
        # Debug output occasionally 
        if hasattr(self, '_debug_counter'):
            self._debug_counter += 1
        else:
            self._debug_counter = 0
        
        if self._debug_counter % 180 == 0:  # Every 3 seconds at 60fps
            print(f"Broadcasting game state to {len(self.players)-1} players")
            for pid, paddle_pos in game_state["paddles"].items():
                print(f"  Player {pid[:8]}: paddle at {paddle_pos}")
    
    def _update_game_logic(self):
        """Update game logic (leader only)"""
        if not self.network.is_network_leader():
            return
            
        # Update local player paddle position
        if self.network.player_id in self.players:
            self.players[self.network.player_id]['paddle_pos'] = self.local_paddle_pos
        
        # Update ball position
        self.ball_pos[0] += self.ball_vel[0]
        self.ball_pos[1] += self.ball_vel[1]
        
        # Ball collision with top/bottom walls
        if self.ball_pos[1] <= self.ball_radius or self.ball_pos[1] >= HEIGHT - self.ball_radius:
            self.ball_vel[1] = -self.ball_vel[1]
        
        # Ball collision with left/right walls 
        if self.ball_pos[0] <= self.ball_radius or self.ball_pos[0] >= WIDTH - self.ball_radius:
            self.ball_vel[0] = -self.ball_vel[0]
        
        # Simple paddle collision detection
        ball_rect = pygame.Rect(
            self.ball_pos[0] - self.ball_radius, 
            self.ball_pos[1] - self.ball_radius,
            self.ball_radius * 2, 
            self.ball_radius * 2
        )
        
        for player_id, player in self.players.items():
            paddle_rect = pygame.Rect(
                player['x'], 
                player['paddle_pos'], 
                self.paddle_width, 
                self.paddle_height
            )
            
            if paddle_rect.colliderect(ball_rect):
                # Simple bounce - reverse x velocity
                self.ball_vel[0] = -self.ball_vel[0]
                # Add some variation based on where ball hits paddle
                hit_pos = (self.ball_pos[1] - player['paddle_pos']) / self.paddle_height
                self.ball_vel[1] += (hit_pos - 0.5) * 4  # Add some english
                break
    
    def _handle_input(self):
        """Handle local player input"""
        keys = pygame.key.get_pressed()
        
        # Update local paddle position
        old_pos = self.local_paddle_pos
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.local_paddle_pos = max(0, self.local_paddle_pos - self.paddle_speed)
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.local_paddle_pos = min(HEIGHT - self.paddle_height, self.local_paddle_pos + self.paddle_speed)
        
        # Update local player in players dict immediately
        if self.network.player_id in self.players:
            self.players[self.network.player_id]['paddle_pos'] = self.local_paddle_pos
    
    def _render(self):
        """Render the game"""
        self.screen.fill(BLACK)
        
        # Draw center line
        pygame.draw.line(self.screen, WHITE, (WIDTH//2, 0), (WIDTH//2, HEIGHT), 2)
        
        # Draw players/paddles
        for player_id, player in self.players.items():
            # Highlight local player with white border
            color = player['color']
            paddle_rect = pygame.Rect(player['x'], player['paddle_pos'], self.paddle_width, self.paddle_height)
            
            if player['is_local']:
                # Draw white border for local player
                border_rect = pygame.Rect(player['x']-2, player['paddle_pos']-2, self.paddle_width+4, self.paddle_height+4)
                pygame.draw.rect(self.screen, WHITE, border_rect)
            
            pygame.draw.rect(self.screen, color, paddle_rect)
            
            # Draw player ID (first 6 chars)
            text = font20.render(player_id[:6], True, color)
            self.screen.blit(text, (player['x'], player['paddle_pos'] - 25))
            
            # Draw score
            score_text = font20.render(str(player['score']), True, color)
            self.screen.blit(score_text, (player['x'], player['paddle_pos'] + self.paddle_height + 5))
        
        # Draw ball
        pygame.draw.circle(self.screen, WHITE, 
                         (int(self.ball_pos[0]), int(self.ball_pos[1])), 
                         self.ball_radius)
        
        # Draw network info
        info_lines = [
            f"Players: {len(self.players)}",
            f"Leader: {'Yes' if self.network.is_network_leader() else 'No'}",
            f"Player: {self.network.player_id[:8]}",
            f"IP: {self.network.local_ip}"
        ]
        
        for i, line in enumerate(info_lines):
            color = GREEN if i == 1 and self.network.is_network_leader() else WHITE
            text = font20.render(line, True, color)
            self.screen.blit(text, (10, 10 + i * 25))
        
        # Draw instructions
        if len(self.players) == 1:
            instruction_text = font30.render("Waiting for other players...", True, YELLOW)
            text_rect = instruction_text.get_rect(center=(WIDTH//2, HEIGHT//2 + 100))
            self.screen.blit(instruction_text, text_rect)
        
        pygame.display.flip()
    
    def _game_loop(self):
        """Main game loop"""
        print("Starting game loop...")
        while self.running:
            current_time = time.time()
            
            # Handle pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
            
            # Handle input
            self._handle_input()
            
            # Send paddle input periodically
            if current_time - self.last_input_send >= self.input_send_interval:
                self._send_paddle_input()
                self.last_input_send = current_time
            
            # Update game logic and broadcast state (leader only)
            if current_time - self.last_game_update >= self.game_update_interval:
                self._update_game_logic()
                self._broadcast_game_state()
                self.last_game_update = current_time
            
            # Render
            self._render()
            
            # Control frame rate
            self.clock.tick(FPS)
        
        print("Game loop ended")
        self.stop()

if __name__ == "__main__":
    game = NetworkedStrikerGame()
    try:
        game.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        game.stop()