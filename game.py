import math
import time
from typing import Dict, List, Tuple

class PongGame:
    def __init__(self):
        self.width = 800
        self.height = 600
        self.ball_pos = [self.width // 2, self.height // 2]
        self.ball_velocity = [200, 150]  # pixels per second
        self.ball_radius = 10
        
        self.paddle_width = 15
        self.paddle_height = 80
        self.paddle_speed = 300  # pixels per second
        
        self.players = {}  # {player_id: {"paddle_pos": float, "score": int, "angle": float}}
        self.scores = {}
        
        self.last_update = time.time()
        
    def add_player(self, player_id: str):
        """Add a new player to the game."""
        num_players = len(self.players)
        angle = (2 * math.pi * num_players) / max(3, len(self.players) + 1)
        
        self.players[player_id] = {
            "paddle_pos": 0.5,  # Relative position (0-1) along the edge
            "score": 0,
            "angle": angle
        }
        self.scores[player_id] = 0
        
        # Recalculate angles for all players
        self._recalculate_player_positions()
    
    def remove_player(self, player_id: str):
        """Remove a player from the game."""
        if player_id in self.players:
            del self.players[player_id]
            del self.scores[player_id]
            self._recalculate_player_positions()
    
    def _recalculate_player_positions(self):
        """Recalculate paddle positions based on number of players."""
        num_players = len(self.players)
        if num_players < 3:
            return
        
        player_ids = list(self.players.keys())
        for i, player_id in enumerate(player_ids):
            angle = (2 * math.pi * i) / num_players
            self.players[player_id]["angle"] = angle
    
    def update_paddle_position(self, player_id: str, position: float):
        """Update a player's paddle position."""
        if player_id in self.players:
            self.players[player_id]["paddle_pos"] = max(0.0, min(1.0, position))
    
    def update(self, dt: float, player_inputs: Dict[str, float]):
        """Update game state."""
        current_time = time.time()
        dt = current_time - self.last_update
        self.last_update = current_time
        
        # Update paddle positions from inputs
        for player_id, paddle_pos in player_inputs.items():
            self.update_paddle_position(player_id, paddle_pos)
        
        # Update ball position
        self.ball_pos[0] += self.ball_velocity[0] * dt
        self.ball_pos[1] += self.ball_velocity[1] * dt
        
        # Check collisions
        self._check_collisions()
        
        # Keep ball in bounds (basic collision with screen edges)
        if self.ball_pos[0] <= self.ball_radius or self.ball_pos[0] >= self.width - self.ball_radius:
            self.ball_velocity[0] = -self.ball_velocity[0]
        if self.ball_pos[1] <= self.ball_radius or self.ball_pos[1] >= self.height - self.ball_radius:
            self.ball_velocity[1] = -self.ball_velocity[1]
    
    def _check_collisions(self):
        """Check for ball-paddle collisions."""
        num_players = len(self.players)
        if num_players < 3:
            return
        
        center_x = self.width // 2
        center_y = self.height // 2
        
        for player_id, player_data in self.players.items():
            angle = player_data["angle"]
            paddle_pos = player_data["paddle_pos"]
            
            # Calculate paddle position based on game geometry
            if num_players == 3:  # Triangle
                radius = min(self.width, self.height) // 3
            elif num_players == 4:  # Square
                radius = min(self.width, self.height) // 3
            else:  # Pentagon, hexagon, etc.
                radius = min(self.width, self.height) // 3
            
            # Paddle center position
            paddle_center_x = center_x + radius * math.cos(angle)
            paddle_center_y = center_y + radius * math.sin(angle)
            
            # Calculate paddle actual position along the edge
            paddle_normal_x = math.cos(angle + math.pi/2)
            paddle_normal_y = math.sin(angle + math.pi/2)
            
            paddle_offset = (paddle_pos - 0.5) * self.paddle_height
            paddle_x = paddle_center_x + paddle_offset * paddle_normal_x
            paddle_y = paddle_center_y + paddle_offset * paddle_normal_y
            
            # Simple collision detection
            dist_to_paddle = math.sqrt((self.ball_pos[0] - paddle_x)**2 + 
                                     (self.ball_pos[1] - paddle_y)**2)
            
            if dist_to_paddle < self.ball_radius + self.paddle_width // 2:
                # Collision detected - reflect ball
                # Simple reflection - reverse velocity towards center
                self.ball_velocity[0] = -self.ball_velocity[0]
                self.ball_velocity[1] = -self.ball_velocity[1]
                break
    
    def get_state(self) -> dict:
        """Get current game state for network transmission."""
        return {
            "ballPosition": {"x": self.ball_pos[0], "y": self.ball_pos[1]},
            "paddlePositions": {pid: data["paddle_pos"] for pid, data in self.players.items()},
            "scores": self.scores.copy(),
            "players": self.players.copy(),
            "gameArea": {"width": self.width, "height": self.height}
        }
    
    def set_state(self, state: dict):
        """Set game state from network data."""
        if "ballPosition" in state:
            self.ball_pos = [state["ballPosition"]["x"], state["ballPosition"]["y"]]
        
        if "paddlePositions" in state:
            for player_id, pos in state["paddlePositions"].items():
                if player_id in self.players:
                    self.players[player_id]["paddle_pos"] = pos
        
        if "scores" in state:
            self.scores.update(state["scores"])
        
        if "players" in state:
            # Update player data while preserving local player info
            for player_id, data in state["players"].items():
                if player_id not in self.players:
                    self.players[player_id] = data
                else:
                    self.players[player_id].update(data)
    
    def get_paddle_positions(self) -> List[Tuple[float, float, float]]:
        """Get paddle positions for rendering. Returns list of (x, y, angle) tuples."""
        positions = []
        num_players = len(self.players)
        
        if num_players < 3:
            return positions
        
        center_x = self.width // 2
        center_y = self.height // 2
        
        if num_players == 3:  # Triangle
            radius = min(self.width, self.height) // 3
        elif num_players == 4:  # Square  
            radius = min(self.width, self.height) // 3
        else:  # Pentagon, hexagon, etc.
            radius = min(self.width, self.height) // 3
        
        for player_data in self.players.values():
            angle = player_data["angle"]
            paddle_pos = player_data["paddle_pos"]
            
            # Paddle center position
            paddle_center_x = center_x + radius * math.cos(angle)
            paddle_center_y = center_y + radius * math.sin(angle)
            
            # Calculate paddle actual position along the edge
            paddle_normal_x = math.cos(angle + math.pi/2)
            paddle_normal_y = math.sin(angle + math.pi/2)
            
            paddle_offset = (paddle_pos - 0.5) * self.paddle_height
            paddle_x = paddle_center_x + paddle_offset * paddle_normal_x
            paddle_y = paddle_center_y + paddle_offset * paddle_normal_y
            
            positions.append((paddle_x, paddle_y, angle))
        
        return positions