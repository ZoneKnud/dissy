import pygame
import math
from typing import Optional
from game import PongGame

class GameGUI:
    def __init__(self, game: PongGame):
        self.game = game
        self.screen = pygame.display.set_mode((game.width, game.height))
        pygame.display.set_caption("Multiplayer Pong")
        
        # Colors
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.RED = (255, 0, 0)
        self.BLUE = (0, 0, 255)
        self.GREEN = (0, 255, 0)
        self.YELLOW = (255, 255, 0)
        self.CYAN = (0, 255, 255)
        self.MAGENTA = (255, 0, 255)
        
        self.player_colors = [self.RED, self.BLUE, self.GREEN, self.YELLOW, self.CYAN, self.MAGENTA]
        
        # Input state
        self.keys_pressed = set()
        self.mouse_y = 0
        
        # Font for UI
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
    def handle_event(self, event):
        """Handle pygame events."""
        if event.type == pygame.KEYDOWN:
            self.keys_pressed.add(event.key)
        elif event.type == pygame.KEYUP:
            self.keys_pressed.discard(event.key)
        elif event.type == pygame.MOUSEMOTION:
            self.mouse_y = event.pos[1]
    
    def get_paddle_input(self) -> float:
        """Get paddle input from user (0.0 to 1.0)."""
        # Use mouse Y position or arrow keys
        paddle_pos = self.mouse_y / self.game.height
        
        if pygame.K_UP in self.keys_pressed:
            paddle_pos = max(0.0, paddle_pos - 0.01)
        elif pygame.K_DOWN in self.keys_pressed:
            paddle_pos = min(1.0, paddle_pos + 0.01)
        
        return max(0.0, min(1.0, paddle_pos))
    
    def update(self, game_state: Optional[dict]):
        """Update GUI with latest game state."""
        if game_state:
            self.game.set_state(game_state)
    
    def render(self):
        """Render the game."""
        self.screen.fill(self.BLACK)
        
        # Draw game area based on number of players
        self._draw_game_area()
        
        # Draw ball
        pygame.draw.circle(self.screen, self.WHITE, 
                         (int(self.game.ball_pos[0]), int(self.game.ball_pos[1])), 
                         self.game.ball_radius)
        
        # Draw paddles
        self._draw_paddles()
        
        # Draw scores
        self._draw_scores()
        
        # Draw connection info
        self._draw_connection_info()
        
        pygame.display.flip()
    
    def _draw_game_area(self):
        """Draw the game area based on number of players."""
        num_players = len(self.game.players)
        
        if num_players < 3:
            # Not enough players - draw waiting message
            text = self.font.render("Waiting for players...", True, self.WHITE)
            text_rect = text.get_rect(center=(self.game.width // 2, self.game.height // 2))
            self.screen.blit(text, text_rect)
            return
        
        center_x = self.game.width // 2
        center_y = self.game.height // 2
        
        if num_players == 3:  # Triangle
            radius = min(self.game.width, self.game.height) // 3
            self._draw_polygon(center_x, center_y, radius, 3)
        elif num_players == 4:  # Square
            radius = min(self.game.width, self.game.height) // 3
            self._draw_polygon(center_x, center_y, radius, 4)
        else:  # Pentagon, hexagon, etc.
            radius = min(self.game.width, self.game.height) // 3
            self._draw_polygon(center_x, center_y, radius, num_players)
    
    def _draw_polygon(self, center_x: int, center_y: int, radius: int, sides: int):
        """Draw a polygon with given number of sides."""
        points = []
        for i in range(sides):
            angle = (2 * math.pi * i) / sides
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            points.append((x, y))
        
        if len(points) > 2:
            pygame.draw.polygon(self.screen, self.WHITE, points, 2)
    
    def _draw_paddles(self):
        """Draw all player paddles."""
        paddle_positions = self.game.get_paddle_positions()
        
        for i, (x, y, angle) in enumerate(paddle_positions):
            color = self.player_colors[i % len(self.player_colors)]
            
            # Calculate paddle corners
            paddle_half_length = self.game.paddle_height // 2
            paddle_half_width = self.game.paddle_width // 2
            
            # Paddle direction (perpendicular to normal)
            paddle_dir_x = math.cos(angle + math.pi/2)
            paddle_dir_y = math.sin(angle + math.pi/2)
            
            # Paddle normal direction
            normal_x = math.cos(angle)
            normal_y = math.sin(angle)
            
            # Calculate paddle corners
            corners = [
                (x - paddle_half_length * paddle_dir_x - paddle_half_width * normal_x,
                 y - paddle_half_length * paddle_dir_y - paddle_half_width * normal_y),
                (x + paddle_half_length * paddle_dir_x - paddle_half_width * normal_x,
                 y + paddle_half_length * paddle_dir_y - paddle_half_width * normal_y),
                (x + paddle_half_length * paddle_dir_x + paddle_half_width * normal_x,
                 y + paddle_half_length * paddle_dir_y + paddle_half_width * normal_y),
                (x - paddle_half_length * paddle_dir_x + paddle_half_width * normal_x,
                 y - paddle_half_length * paddle_dir_y + paddle_half_width * normal_y)
            ]
            
            pygame.draw.polygon(self.screen, color, corners)
    
    def _draw_scores(self):
        """Draw player scores."""
        y_offset = 20
        for i, (player_id, score) in enumerate(self.game.scores.items()):
            color = self.player_colors[i % len(self.player_colors)]
            text = self.small_font.render(f"Player {i+1}: {score}", True, color)
            self.screen.blit(text, (10, y_offset + i * 25))
    
    def _draw_connection_info(self):
        """Draw connection information."""
        num_players = len(self.game.players)
        text = self.small_font.render(f"Players: {num_players}", True, self.WHITE)
        self.screen.blit(text, (self.game.width - 120, 10))
        
        if num_players < 3:
            text = self.small_font.render("Need 3+ players to start", True, self.RED)
            self.screen.blit(text, (self.game.width - 200, 35))