import pygame
import threading
import time
from typing import Dict, List
from network import NetworkManager, MessageType, Player

# Font that is used to render the text
pygame.font.init()
font20 = pygame.font.Font(None, 20)

# RGB values of standard colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)

# Basic parameters of the screen
WIDTH, HEIGHT = 900, 600
FPS = 60

# Game colors for different players
PLAYER_COLORS = [GREEN, RED, BLUE, YELLOW, (255, 0, 255), (0, 255, 255)]

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
        self.game_started = False
        self.players: Dict[str, Dict] = {}
        self.ball_pos = [WIDTH // 2, HEIGHT // 2]
        self.ball_vel = [5, 5]
        self.ball_radius = 7
        
        # Local player input
        self.local_paddle_pos = HEIGHT // 2
        self.paddle_speed = 7
        
        # Game update rate
        self.last_game_update = time.time()
        self.game_update_interval = 1.0 / 60.0  # 60 FPS
        
    def start(self):
        """Start the game and network"""
        print("Starting networked Pong game...")
        self.running = True
        
        # Start network
        self.network.start()
        
        # Wait a bit for network discovery
        time.sleep(3)
        
        print(f"Network status:")
        print(f"  Player ID: {self.network.player_id}")
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
        
        # Calculate paddle positions based on number of players
        num_players = len(players)
        if num_players == 0:
            return
        
        # For simplicity, arrange players around the screen
        for i, player in enumerate(players):
            color_index = i % len(PLAYER_COLORS)
            
            if num_players == 2:
                # Traditional pong setup
                x = 20 if i == 0 else WIDTH - 30
                y = HEIGHT // 2 - 50
            elif num_players <= 4:
                # Four sides setup
                if i == 0:  # Left
                    x, y = 20, HEIGHT // 2 - 50
                elif i == 1:  # Right  
                    x, y = WIDTH - 30, HEIGHT // 2 - 50
                elif i == 2:  # Top
                    x, y = WIDTH // 2 - 50, 20
                else:  # Bottom
                    x, y = WIDTH // 2 - 50, HEIGHT - 30
            else:
                # Circular arrangement for more players
                import math
                angle = (2 * math.pi * i) / num_players
                radius = min(WIDTH, HEIGHT) // 3
                x = WIDTH // 2 + int(radius * math.cos(angle)) - 50
                y = HEIGHT // 2 + int(radius * math.sin(angle)) - 50
            
            self.players[player.id] = {
                'ip': player.ip,
                'x': x,
                'y': y,
                'color': PLAYER_COLORS[color_index],
                'score': 0,
                'paddle_pos': y
            }
        
        print(f"Initialized game with {len(self.players)} players")
    
    def _handle_network_message(self, message: dict, sender_ip: str):
        """Handle network messages"""
        msg_type = message.get("type")
        data = message.get("data", {})
        
        if msg_type == MessageType.PADDLE_INPUT.value:
            self._handle_paddle_input(data)
        elif msg_type == MessageType.GAME_STATE.value:
            self._handle_game_state(data)
        elif msg_type == MessageType.PLAYER_JOIN.value:
            print(f"Player joined: {data.get('playerId')}")
            self._initialize_game()  # Re-initialize with new player
        elif msg_type == MessageType.PLAYER_LEAVE.value:
            print(f"Player left: {data.get('playerId')}")
            self._initialize_game()  # Re-initialize without player
    
    def _handle_paddle_input(self, data: dict):
        """Handle paddle input from network player"""
        player_id = data.get("playerId")
        paddle_pos = data.get("paddlePosition")
        
        if player_id in self.players:
            self.players[player_id]['paddle_pos'] = paddle_pos
    
    def _handle_game_state(self, data: dict):
        """Handle game state update from leader"""
        if self.network.is_network_leader():
            return  # Leaders don't process their own game state
            
        # Update ball position
        ball_pos = data.get("ballPosition", {})
        self.ball_pos = [ball_pos.get("x", self.ball_pos[0]), ball_pos.get("y", self.ball_pos[1])]
        
        # Update paddle positions
        paddle_positions = data.get("paddlePositions", {})
        for player_id, pos in paddle_positions.items():
            if player_id in self.players:
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
            
        message = {
            "type": MessageType.PADDLE_INPUT.value,
            "data": {
                "playerId": self.network.player_id,
                "paddlePosition": self.local_paddle_pos
            }
        }
        
        try:
            import socket
            import json
            paddle_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            paddle_socket.sendto(json.dumps(message).encode(), (leader_ip, NetworkManager.GAME_PORT))
            paddle_socket.close()
        except Exception as e:
            print(f"Failed to send paddle input: {e}")
    
    def _broadcast_game_state(self):
        """Broadcast game state to all players (leader only)"""
        if not self.network.is_network_leader():
            return
            
        message = {
            "type": MessageType.GAME_STATE.value,
            "data": {
                "ballPosition": {"x": self.ball_pos[0], "y": self.ball_pos[1]},
                "paddlePositions": {pid: p['paddle_pos'] for pid, p in self.players.items()},
                "scores": {pid: p['score'] for pid, p in self.players.items()}
            }
        }
        
        try:
            import socket
            import json
            for player in self.network.get_players():
                if player.id != self.network.player_id:
                    try:
                        state_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        state_socket.sendto(json.dumps(message).encode(), (player.ip, NetworkManager.GAME_PORT))
                        state_socket.close()
                    except Exception as e:
                        print(f"Failed to send game state to {player.ip}: {e}")
        except Exception as e:
            print(f"Failed to broadcast game state: {e}")
    
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
        
        # Ball collision with left/right walls (simple scoring)
        if self.ball_pos[0] <= self.ball_radius:
            self.ball_vel[0] = -self.ball_vel[0]
            # Could add scoring logic here
        elif self.ball_pos[0] >= WIDTH - self.ball_radius:
            self.ball_vel[0] = -self.ball_vel[0]
            # Could add scoring logic here
        
        # Simple paddle collision (basic implementation)
        for player_id, player in self.players.items():
            paddle_rect = pygame.Rect(player['x'], player['paddle_pos'], 10, 100)
            ball_rect = pygame.Rect(self.ball_pos[0] - self.ball_radius, 
                                  self.ball_pos[1] - self.ball_radius,
                                  self.ball_radius * 2, self.ball_radius * 2)
            
            if paddle_rect.colliderect(ball_rect):
                self.ball_vel[0] = -self.ball_vel[0]
                break
    
    def _handle_input(self):
        """Handle local player input"""
        keys = pygame.key.get_pressed()
        
        # Update local paddle position
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.local_paddle_pos = max(0, self.local_paddle_pos - self.paddle_speed)
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.local_paddle_pos = min(HEIGHT - 100, self.local_paddle_pos + self.paddle_speed)
    
    def _render(self):
        """Render the game"""
        self.screen.fill(BLACK)
        
        # Draw players/paddles
        for player_id, player in self.players.items():
            # Highlight local player
            color = WHITE if player_id == self.network.player_id else player['color']
            paddle_rect = pygame.Rect(player['x'], player['paddle_pos'], 10, 100)
            pygame.draw.rect(self.screen, color, paddle_rect)
            
            # Draw player ID (first 8 chars)
            text = font20.render(player_id[:8], True, color)
            self.screen.blit(text, (player['x'], player['paddle_pos'] - 25))
        
        # Draw ball
        pygame.draw.circle(self.screen, WHITE, 
                         (int(self.ball_pos[0]), int(self.ball_pos[1])), 
                         self.ball_radius)
        
        # Draw network info
        info_lines = [
            f"Players: {len(self.players)}",
            f"Leader: {'Yes' if self.network.is_network_leader() else 'No'}",
            f"Player ID: {self.network.player_id[:8]}",
            f"Local IP: {self.network.local_ip}"
        ]
        
        for i, line in enumerate(info_lines):
            text = font20.render(line, True, WHITE)
            self.screen.blit(text, (10, 10 + i * 25))
        
        pygame.display.flip()
    
    def _game_loop(self):
        """Main game loop"""
        while self.running:
            # Handle pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
            
            # Handle input
            self._handle_input()
            
            # Send paddle input to leader
            self._send_paddle_input()
            
            # Update game logic (leader only)
            current_time = time.time()
            if current_time - self.last_game_update >= self.game_update_interval:
                self._update_game_logic()
                self._broadcast_game_state()
                self.last_game_update = current_time
            
            # Render
            self._render()
            
            # Control frame rate
            self.clock.tick(FPS)
        
        self.stop()

if __name__ == "__main__":
    game = NetworkedStrikerGame()
    try:
        game.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        game.stop()