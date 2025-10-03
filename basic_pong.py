import pygame
import math
import random

pygame.init()

# Font that is used to render the text
font20 = pygame.font.Font('freesansbold.ttf', 20)

# RGB values of standard colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
PURPLE = (255, 0, 255)
GRAY = (128, 128, 128)

# Get screen info and calculate maximum square size
screen_info = pygame.display.Info()
max_size = min(screen_info.current_w, screen_info.current_h) - 200
WIDTH, HEIGHT = max_size, max_size

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Multi-Player Pong")

clock = pygame.time.Clock()

class GameField:
    def __init__(self, num_players):
        self.num_players = num_players
        self.center_x = WIDTH // 2
        self.center_y = HEIGHT // 2
        self.radius = min(WIDTH, HEIGHT) // 2 -0  # Increased from 80 to 20
        self.walls = []
        self.player_positions = []
        self.setup_field()
    
    def setup_field(self):
        if self.num_players == 2:
            # Extend walls to window edges
            self.walls = [
                ((0, 0), (WIDTH, 0)),  # Top wall - at very top
                ((0, HEIGHT-1), (WIDTH, HEIGHT-1))  # Bottom wall - at very bottom
            ]
            # For 2-player mode, use simple positions without rotation
            self.player_positions = [
                (20, self.center_y, 0, 0),  # Left player - no rotation
                (WIDTH-30, self.center_y, 0, 0)  # Right player - no rotation
            ]
        elif self.num_players == 4:
            # Use window edges as walls for 4-player mode
            self.walls = [
                ((0, 0), (WIDTH, 0)),          # Top wall
                ((WIDTH, 0), (WIDTH, HEIGHT)), # Right wall
                ((WIDTH, HEIGHT), (0, HEIGHT)), # Bottom wall
                ((0, HEIGHT), (0, 0))          # Left wall
            ]
            # Position players at each edge
            self.player_positions = [
                (self.center_x, 20, math.pi/2, 0),        # Top player
                (WIDTH-30, self.center_y, 0, -math.pi/2), # Right player
                (self.center_x, HEIGHT-30, -math.pi/2, math.pi), # Bottom player
                (20, self.center_y, math.pi, math.pi/2)   # Left player
            ]
        else:
            # Larger polygon field for 3 and 5+ players
            angle_step = 2 * math.pi / self.num_players
            self.walls = []
            self.player_positions = []
            
            # Create polygon vertices with larger radius
            vertices = []
            for i in range(self.num_players):
                angle = i * angle_step - math.pi/2  # Start from top
                x = self.center_x + self.radius * math.cos(angle)
                y = self.center_y + self.radius * math.sin(angle)
                vertices.append((x, y))
            
            # Create walls and player positions
            for i in range(self.num_players):
                next_i = (i + 1) % self.num_players
                
                # Wall from vertex i to vertex i+1
                wall_start = vertices[i]
                wall_end = vertices[next_i]
                self.walls.append((wall_start, wall_end))
                
                # Player position at middle of wall
                mid_x = (wall_start[0] + wall_end[0]) / 2
                mid_y = (wall_start[1] + wall_end[1]) / 2
                
                # Calculate wall angle and normal
                wall_angle = math.atan2(wall_end[1] - wall_start[1], wall_end[0] - wall_start[0])
                normal_angle = wall_angle + math.pi/2
                
                # Move player slightly inward from wall
                offset = 15  # Reduced from 20 to 15
                player_x = mid_x - offset * math.cos(normal_angle)
                player_y = mid_y - offset * math.sin(normal_angle)
                
                self.player_positions.append((player_x, player_y, wall_angle, normal_angle))
    
    def draw_walls(self):
        for wall in self.walls:
            pygame.draw.line(screen, GRAY, wall[0], wall[1], 3)

class Striker:
    def __init__(self, field_pos, width, height, speed, color, player_id):
        self.field_pos = field_pos  # Position along the wall (0-1)
        self.width = width
        self.height = height
        self.speed = speed
        self.color = color
        self.player_id = player_id
        self.wall_start = None
        self.wall_end = None
        self.wall_angle = 0
        self.normal_angle = 0
        self.rect = None
        self.center_y = HEIGHT // 2
        
    def set_wall_info(self, wall_start, wall_end, wall_angle, normal_angle):
        self.wall_start = wall_start
        self.wall_end = wall_end
        self.wall_angle = wall_angle
        self.normal_angle = normal_angle
        self.update_position()
    
    def update_position(self):
        if self.wall_start is None:  # 2-player mode - simple vertical paddles
            self.x = 20 if self.player_id == 0 else WIDTH - 30
            # Allow full range of movement
            self.y = (self.field_pos * (HEIGHT - self.height))
            
            # Keep paddle bounds within screen
            self.y = max(0, min(HEIGHT - self.height, self.y))
            
            # Simple rectangular paddle for 2-player mode
            self.corners = [
                (self.x, self.y),
                (self.x + self.width, self.y),
                (self.x + self.width, self.y + self.height),
                (self.x, self.y + self.height)
            ]
            
            self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        else:
            # Calculate position along wall (for polygon modes and 4-player mode)
            wall_x = self.wall_start[0] + (self.wall_end[0] - self.wall_start[0]) * self.field_pos
            wall_y = self.wall_start[1] + (self.wall_end[1] - self.wall_start[1]) * self.field_pos
            
            # Move inward from wall (toward center) so paddle is in front of wall
            offset = 15  # Move paddle inward so it can intercept the ball
            self.x = wall_x + offset * math.cos(self.normal_angle)
            self.y = wall_y + offset * math.sin(self.normal_angle)
            
            # Create rectangle parallel to the wall (not perpendicular)
            # Use wall_angle directly for paddle orientation
            cos_a = math.cos(self.wall_angle)
            sin_a = math.sin(self.wall_angle)
            
            # Rectangle corners relative to center - paddle runs along the wall
            hw, hh = self.height/2, self.width/2  # Swap width/height for wall-parallel orientation
            corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
            
            # Rotate and translate corners
            self.corners = []
            for cx, cy in corners:
                rx = cx * cos_a - cy * sin_a + self.x
                ry = cx * sin_a + cy * cos_a + self.y
                self.corners.append((rx, ry))
            
            # Create rect for collision (approximation)
            self.rect = pygame.Rect(self.x - hw, self.y - hh, self.height, self.width)
    
    def update(self, movement, dt):
        if movement != 0:
            if self.wall_start is None:  # 2-player mode
                # Move along full height of screen
                self.field_pos += movement * self.speed * dt / HEIGHT
                self.field_pos = max(0.0, min(1.0, self.field_pos))
            else:
                # Polygon mode
                wall_length = math.sqrt((self.wall_end[0] - self.wall_start[0])**2 + 
                                      (self.wall_end[1] - self.wall_start[1])**2)
                movement_per_second = self.speed / wall_length
                self.field_pos += movement * movement_per_second * dt
                self.field_pos = max(0.1, min(0.9, self.field_pos))
            self.update_position()
    
    def display(self):
        if len(self.corners) >= 4:
            pygame.draw.polygon(screen, self.color, self.corners)
    
    def get_rect(self):
        return self.rect
    
    def check_ball_collision(self, ball):
        """Check collision between ball (circle) and paddle (polygon)"""
        if self.wall_start is None:  # 2-player mode - use simple rect collision
            return pygame.Rect.colliderect(ball.get_rect(), self.get_rect())
        else:  # Polygon mode - use polygon-circle collision
            return self.point_in_polygon_collision(ball.posx, ball.posy, ball.radius)
    
    def point_in_polygon_collision(self, cx, cy, radius):
        """Check if circle collides with polygon paddle"""
        # Check if circle center is close enough to any edge of the paddle
        for i in range(len(self.corners)):
            x1, y1 = self.corners[i]
            x2, y2 = self.corners[(i + 1) % len(self.corners)]
            
            # Distance from circle center to line segment
            dist = self.point_to_line_distance(cx, cy, x1, y1, x2, y2)
            if dist <= radius:
                return True
        
        return False
    
    def point_to_line_distance(self, px, py, x1, y1, x2, y2):
        """Calculate distance from point to line segment"""
        # Vector from line start to point
        dx = px - x1
        dy = py - y1
        
        # Line vector
        lx = x2 - x1
        ly = y2 - y1
        
        # Line length squared
        line_len_sq = lx*lx + ly*ly
        if line_len_sq == 0:
            return math.sqrt(dx*dx + dy*dy)
        
        # Project point onto line
        t = max(0, min(1, (dx*lx + dy*ly) / line_len_sq))
        
        # Closest point on line
        closest_x = x1 + t * lx
        closest_y = y1 + t * ly
        
        # Distance to closest point
        dist_x = px - closest_x
        dist_y = py - closest_y
        return math.sqrt(dist_x*dist_x + dist_y*dist_y)

class Ball:
    def __init__(self, posx, posy, radius, speed, color):
        self.posx = posx
        self.posy = posy
        self.radius = radius
        self.speed = speed
        self.color = color
        # Use completely random angle for initial direction
        angle = random.random() * 2 * math.pi
        self.xFac = math.cos(angle)
        self.yFac = math.sin(angle)
        self.firstTime = 1
        self.last_player_touched = None  # Track which player last touched the ball
        self.has_been_touched = False    # Track if any player has touched the ball
    
    def display(self):
        pygame.draw.circle(screen, self.color, (int(self.posx), int(self.posy)), self.radius)
    
    def update(self, dt, field):
        self.posx += self.speed * self.xFac * dt
        self.posy += self.speed * self.yFac * dt
        
        if field.num_players == 2:
            # 2-player mode: check boundaries for scoring
            if self.posx - self.radius <= 0 and self.firstTime:
                self.firstTime = 0
                return 1  # Player 2 scores
            elif self.posx + self.radius >= WIDTH and self.firstTime:
                self.firstTime = 0
                return -1  # Player 1 scores
            
            # Bounce off top and bottom walls (now at window edges)
            if self.posy - self.radius <= 0:
                self.posy = self.radius
                self.yFac *= -1
            elif self.posy + self.radius >= HEIGHT:
                self.posy = HEIGHT - self.radius
                self.yFac *= -1
        else:
            # Check wall collisions for polygon modes
            for i, wall in enumerate(field.walls):
                if self.check_wall_collision(wall):
                    # First reflect the ball off the wall
                    self.reflect_off_wall(wall)
                    
                    # Move ball away from wall to prevent sticking
                    x1, y1 = wall[0]
                    x2, y2 = wall[1]
                    
                    # Calculate wall normal
                    wx = x2 - x1
                    wy = y2 - y1
                    wall_length = math.sqrt(wx*wx + wy*wy)
                    
                    if wall_length > 0:
                        # Normalized wall vector
                        wx /= wall_length
                        wy /= wall_length
                        
                        # Normal vector (perpendicular to wall, pointing inward)
                        nx = -wy
                        ny = wx
                        
                        # Ensure normal points toward center of field
                        center_dx = field.center_x - self.posx
                        center_dy = field.center_y - self.posy
                        if (nx * center_dx + ny * center_dy) < 0:
                            nx = -nx
                            ny = -ny
                        
                        # Move ball away from wall
                        self.posx += nx * (self.radius + 2)
                        self.posy += ny * (self.radius + 2)
                    
                    # Only count as scoring if a player has touched the ball
                    if self.has_been_touched and self.last_player_touched is not None:
                        self.firstTime = 0
                        return self.last_player_touched + 1  # Return which player should score
                    else:
                        # Just bounced off wall without scoring
                        break
        
        return 0
    
    def check_wall_collision(self, wall):
        # Simple line-circle collision detection
        x1, y1 = wall[0]
        x2, y2 = wall[1]
        
        # Vector from wall start to ball center
        dx = self.posx - x1
        dy = self.posy - y1
        
        # Wall vector
        wx = x2 - x1
        wy = y2 - y1
        
        # Project ball onto wall
        wall_length_sq = wx*wx + wy*wy
        if wall_length_sq == 0:
            return False
            
        t = max(0, min(1, (dx*wx + dy*wy) / wall_length_sq))
        
        # Closest point on wall
        closest_x = x1 + t * wx
        closest_y = y1 + t * wy
        
        # Distance to closest point
        dist_sq = (self.posx - closest_x)**2 + (self.posy - closest_y)**2
        
        return dist_sq <= self.radius**2
    
    def reflect_off_wall(self, wall):
        x1, y1 = wall[0]
        x2, y2 = wall[1]
        
        # Wall normal (perpendicular)
        wx = x2 - x1
        wy = y2 - y1
        wall_length = math.sqrt(wx*wx + wy*wy)
        
        if wall_length == 0:
            return
            
        # Normalized wall vector
        wx /= wall_length
        wy /= wall_length
        
        # Normal vector (rotate wall vector 90 degrees)
        nx = -wy
        ny = wx
        
        # Reflect velocity off normal
        dot = self.xFac * nx + self.yFac * ny
        self.xFac = self.xFac - 2 * dot * nx
        self.yFac = self.yFac - 2 * dot * ny
    
    def reset(self, field):
        self.posx = field.center_x
        self.posy = field.center_y
        # More controlled initial direction for better gameplay
        if field.num_players == 2:
            # Start with horizontal movement and slight vertical component
            angle = random.choice([-0.5, 0.5, math.pi - 0.5, math.pi + 0.5])
            self.xFac = math.cos(angle)
            self.yFac = math.sin(angle)
        else:
            # Random direction for polygon modes
            angle = random.random() * 2 * math.pi
            self.xFac = math.cos(angle)
            self.yFac = math.sin(angle)
        self.firstTime = 1
        self.last_player_touched = None  # Reset tracking
        self.has_been_touched = False
    
    def hit(self):
        self.xFac *= -1
    
    def player_hit(self, player_id):
        """Called when a player hits the ball"""
        self.last_player_touched = player_id
        self.has_been_touched = True
    
    def get_rect(self):
        return pygame.Rect(self.posx - self.radius, self.posy - self.radius, 
                          self.radius * 2, self.radius * 2)

def main():
    running = True
    num_players = 2  # Start with 2 players
    
    # Player colors
    colors = [GREEN, RED, BLUE, YELLOW, PURPLE]
    
    # Control keys for each player
    player_keys = [
        (pygame.K_w, pygame.K_s),      # Player 1: W/S
        (pygame.K_UP, pygame.K_DOWN),  # Player 2: UP/DOWN
        (pygame.K_t, pygame.K_g),      # Player 3: T/G
        (pygame.K_i, pygame.K_k),      # Player 4: I/K
        (pygame.K_r, pygame.K_f)       # Player 5: R/F
    ]
    
    def setup_game(num_players):
        field = GameField(num_players)
        
        # Create players
        players = []
        for i in range(num_players):
            # Faster paddle speed for 2-player mode
            # paddle_speed = 600 if field.num_players == 2 else 300
            # ball_speed = 350 if field.num_players == 2 else 300

            paddle_speed = 600
            ball_speed = 400

            player = Striker(0.5, 10, 100, paddle_speed, colors[i], i)
            
            if field.num_players == 2:
                # For 2-player mode, don't set wall info (keeps paddles vertical)
                player.update_position()
            else:
                # For polygon modes and 4-player mode, set wall info
                wall_start, wall_end = field.walls[i]
                wall_angle = math.atan2(wall_end[1] - wall_start[1], wall_end[0] - wall_start[0])
                normal_angle = wall_angle + math.pi/2
                player.set_wall_info(wall_start, wall_end, wall_angle, normal_angle)
            players.append(player)
        
        # Create ball with appropriate speed and initial direction
        ball = Ball(field.center_x, field.center_y, 8, ball_speed, WHITE)
        
        # Set initial direction based on game mode
        if field.num_players == 2:
            # Controlled angles for 2-player mode
            angle = random.choice([-0.5, 0.5, math.pi - 0.5, math.pi + 0.5])
            ball.xFac = math.cos(angle)
            ball.yFac = math.sin(angle)
        else:
            # Random angle for polygon modes
            angle = random.random() * 2 * math.pi
            ball.xFac = math.cos(angle)
            ball.yFac = math.sin(angle)
        
        return field, players, ball, [0] * num_players, [0] * num_players
    
    field, players, ball, scores, movements = setup_game(num_players)
    
    while running:
        dt = clock.tick() / 1000.0
        # Cap delta time to prevent issues when window loses focus
        dt = min(dt, 1/30.0)  # Cap at 30 FPS equivalent (0.033 seconds)
        
        screen.fill(BLACK)
        
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.KEYDOWN:
                # Number keys to change player count
                if event.key == pygame.K_2:
                    num_players = 2
                    field, players, ball, scores, movements = setup_game(num_players)
                elif event.key == pygame.K_3:
                    num_players = 3
                    field, players, ball, scores, movements = setup_game(num_players)
                elif event.key == pygame.K_4:
                    num_players = 4
                    field, players, ball, scores, movements = setup_game(num_players)
                elif event.key == pygame.K_5:
                    num_players = 5
                    field, players, ball, scores, movements = setup_game(num_players)
                
                # Player movement
                for i in range(min(num_players, len(player_keys))):
                    if event.key == player_keys[i][0]:  # Up/Left key
                        movements[i] = -1
                    elif event.key == player_keys[i][1]:  # Down/Right key
                        movements[i] = 1
            
            if event.type == pygame.KEYUP:
                for i in range(min(num_players, len(player_keys))):
                    if event.key in player_keys[i]:
                        movements[i] = 0
        
        # Update game objects first
        for i, player in enumerate(players):
            player.update(movements[i], dt)
        
        # Check paddle collisions BEFORE updating ball position
        ball_hit_paddle = False
        for player in players:
            if player.check_ball_collision(ball):
                # Track which player hit the ball
                ball.player_hit(player.player_id)
                
                # Better collision handling for different modes
                if field.num_players == 2:
                    # Prevent ball from getting stuck inside paddle
                    if player.player_id == 0 and ball.posx < player.x + player.width:
                        ball.posx = player.x + player.width + ball.radius
                    elif player.player_id == 1 and ball.posx > player.x:
                        ball.posx = player.x - ball.radius
                else:
                    # For polygon mode, reflect ball based on paddle normal
                    # Use the wall normal to reflect the ball
                    nx = math.cos(player.normal_angle)
                    ny = math.sin(player.normal_angle)
                    
                    # Reflect velocity off paddle normal
                    dot = ball.xFac * nx + ball.yFac * ny
                    ball.xFac = ball.xFac - 2 * dot * nx
                    ball.yFac = ball.yFac - 2 * dot * ny
                    
                    # Move ball away from paddle to prevent sticking
                    ball.posx += nx * (ball.radius + 5)
                    ball.posy += ny * (ball.radius + 5)
                
                if field.num_players == 2:
                    ball.hit()  # Only use simple hit for 2-player mode
                
                ball_hit_paddle = True
                break  # Only hit one paddle per frame
        
        # Only check for scoring/wall collisions if ball didn't hit a paddle
        point = 0
        if not ball_hit_paddle:
            point = ball.update(dt, field)
        else:
            # Still update ball position even if it hit a paddle
            ball.posx += ball.speed * ball.xFac * dt
            ball.posy += ball.speed * ball.yFac * dt
        
        # Handle scoring
        if point != 0:
            if field.num_players == 2:
                if point == -1:
                    scores[0] += 1
                elif point == 1:
                    scores[1] += 1
            else:
                # In polygon mode, the last player who touched the ball scores
                scoring_player = point - 1  # Convert from 1-based to 0-based index
                if 0 <= scoring_player < num_players:
                    scores[scoring_player] += 1
            
            ball.reset(field)
        
        # Draw everything
        field.draw_walls()
        
        for player in players:
            player.display()
        
        ball.display()
        
        # Display scores and controls
        y_offset = 20
        for i in range(num_players):
            score_text = font20.render(f"Player {i+1}: {scores[i]}", True, colors[i])
            screen.blit(score_text, (10, y_offset + i * 25))
        
        # Display controls
        controls_text = font20.render("Press 2-5 to change player count", True, WHITE)
        screen.blit(controls_text, (10, HEIGHT - 40))
        
        pygame.display.update()

if __name__ == "__main__":
    main()
    pygame.quit()