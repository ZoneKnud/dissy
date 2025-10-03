import pygame
import math
import random
import zmq
import json
import threading
import time
import uuid
import argparse
import socket
import struct

pygame.init()

# Font that is used to render the text
font20 = pygame.font.Font('freesansbold.ttf', 20)
font16 = pygame.font.Font('freesansbold.ttf', 16)

# RGB values of standard colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
PURPLE = (255, 0, 255)
GRAY = (128, 128, 128)
ORANGE = (255, 165, 0)
CYAN = (0, 255, 255)

# Get screen info and calculate maximum square size
screen_info = pygame.display.Info()
max_size = min(screen_info.current_w, screen_info.current_h) - 200
WIDTH, HEIGHT = max_size, max_size

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Multi-Player Pong")

clock = pygame.time.Clock()

class NetworkDiscovery:
    def __init__(self, leader_port=5555, discovery_port=5556):
        self.leader_port = leader_port
        self.discovery_port = discovery_port
        self.running = True
        self.discovered_leaders = {}
        
    def start_leader_broadcast(self):
        """Start broadcasting leader presence"""
        def broadcast_loop():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Get local IP address
            try:
                # Connect to a remote address to determine local IP
                temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                temp_sock.connect(("8.8.8.8", 80))
                local_ip = temp_sock.getsockname()[0]
                temp_sock.close()
            except:
                local_ip = "127.0.0.1"
            
            message = {
                "type": "leader_broadcast",
                "ip": local_ip,
                "port": self.leader_port,
                "game": "MultiPlayerPong",
                "timestamp": time.time()
            }
            
            message_bytes = json.dumps(message).encode()
            
            print(f"Broadcasting leader presence on {local_ip}:{self.leader_port}")
            
            while self.running:
                try:
                    # Broadcast to subnet
                    sock.sendto(message_bytes, ('255.255.255.255', self.discovery_port))
                    # Also send to localhost for testing
                    sock.sendto(message_bytes, ('127.0.0.1', self.discovery_port))
                except Exception as e:
                    print(f"Broadcast error: {e}")
                
                time.sleep(2)  # Broadcast every 2 seconds
            
            sock.close()
        
        self.broadcast_thread = threading.Thread(target=broadcast_loop)
        self.broadcast_thread.daemon = True
        self.broadcast_thread.start()
    
    def start_discovery_listener(self, timeout=10):
        """Listen for leader broadcasts and return the first found leader"""
        def listen_loop():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(1.0)  # 1 second timeout for non-blocking
            
            try:
                sock.bind(('', self.discovery_port))
                print(f"Listening for leader broadcasts on port {self.discovery_port}...")
            except Exception as e:
                print(f"Could not bind to discovery port {self.discovery_port}: {e}")
                return
            
            start_time = time.time()
            
            while self.running and (time.time() - start_time) < timeout:
                try:
                    data, addr = sock.recvfrom(1024)
                    message = json.loads(data.decode())
                    
                    if (message.get("type") == "leader_broadcast" and 
                        message.get("game") == "MultiPlayerPong"):
                        
                        leader_id = f"{message['ip']}:{message['port']}"
                        
                        if leader_id not in self.discovered_leaders:
                            self.discovered_leaders[leader_id] = {
                                "ip": message["ip"],
                                "port": message["port"],
                                "timestamp": message["timestamp"],
                                "discovered_at": time.time()
                            }
                            print(f"Discovered leader at {message['ip']}:{message['port']}")
                
                except socket.timeout:
                    continue  # Check if we should keep running
                except Exception as e:
                    if self.running:  # Only print error if we're still supposed to be running
                        print(f"Discovery listen error: {e}")
            
            sock.close()
        
        self.listen_thread = threading.Thread(target=listen_loop)
        self.listen_thread.daemon = True
        self.listen_thread.start()
        
        # Wait for discovery to complete
        self.listen_thread.join(timeout + 1)
        
        return list(self.discovered_leaders.values())
    
    def get_best_leader(self):
        """Get the best leader from discovered leaders (most recent)"""
        if not self.discovered_leaders:
            return None
        
        # Remove old entries (older than 10 seconds)
        current_time = time.time()
        expired_leaders = []
        for leader_id, leader_info in self.discovered_leaders.items():
            if current_time - leader_info["discovered_at"] > 10:
                expired_leaders.append(leader_id)
        
        for leader_id in expired_leaders:
            del self.discovered_leaders[leader_id]
        
        if not self.discovered_leaders:
            return None
        
        # Return the most recently discovered leader
        best_leader = max(self.discovered_leaders.values(), 
                         key=lambda x: x["discovered_at"])
        return best_leader
    
    def stop(self):
        """Stop discovery services"""
        self.running = False
        if hasattr(self, 'broadcast_thread'):
            self.broadcast_thread.join(timeout=1.0)
        if hasattr(self, 'listen_thread'):
            self.listen_thread.join(timeout=1.0)

class NetworkManager:
    def __init__(self, is_leader=True, leader_port=5555, leader_ip="127.0.0.1", discovery=None):
        self.context = zmq.Context()
        self.is_leader = is_leader
        self.leader_port = leader_port
        self.leader_ip = leader_ip
        self.player_id = str(uuid.uuid4())
        self.connected_players = {}
        self.game_state = None
        self.running = True
        self.discovery = discovery
        
        if is_leader:
            self.setup_leader()
        else:
            self.setup_follower()
    
    def setup_leader(self):
        self.socket = self.context.socket(zmq.ROUTER)
        self.socket.bind(f"tcp://*:{self.leader_port}")
        self.socket.setsockopt(zmq.RCVTIMEO, 100)  # 100ms timeout
        print(f"Leader started on port {self.leader_port}")
        
        # Start network discovery broadcasting
        if self.discovery:
            self.discovery.start_leader_broadcast()
        
        # Start network thread
        self.network_thread = threading.Thread(target=self.leader_network_loop)
        self.network_thread.daemon = True
        self.network_thread.start()
    
    def setup_follower(self):
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.IDENTITY, self.player_id.encode())
        self.socket.connect(f"tcp://{self.leader_ip}:{self.leader_port}")
        self.socket.setsockopt(zmq.RCVTIMEO, 100)  # 100ms timeout
        
        # Send join request
        self.send_message({"type": "join", "player_id": self.player_id})
        print(f"Connecting to leader at {self.leader_ip}:{self.leader_port}")
        
        # Start network thread
        self.network_thread = threading.Thread(target=self.follower_network_loop)
        self.network_thread.daemon = True
        self.network_thread.start()
    
    def leader_network_loop(self):
        while self.running:
            try:
                # Receive messages from followers
                identity, message = self.socket.recv_multipart(zmq.NOBLOCK)
                data = json.loads(message.decode())
                
                if data["type"] == "join":
                    self.handle_player_join(identity.decode(), data)
                elif data["type"] == "input":
                    self.handle_player_input(identity.decode(), data)
                elif data["type"] == "disconnect":
                    self.handle_player_disconnect(identity.decode())
                    
            except zmq.Again:
                pass  # No message received
            except Exception as e:
                print(f"Leader network error: {e}")
            
            time.sleep(0.001)  # Small delay to prevent busy waiting
    
    def follower_network_loop(self):
        while self.running:
            try:
                message = self.socket.recv(zmq.NOBLOCK)
                data = json.loads(message.decode())
                
                if data["type"] == "game_state":
                    self.game_state = data["state"]
                elif data["type"] == "player_assigned":
                    self.my_player_index = data["player_index"]
                    print(f"Assigned as player {self.my_player_index + 1}")
                    
            except zmq.Again:
                pass  # No message received
            except Exception as e:
                print(f"Follower network error: {e}")
            
            time.sleep(0.001)
    
    def handle_player_join(self, player_id, data):
        if player_id not in self.connected_players:
            player_index = len(self.connected_players)
            self.connected_players[player_id] = {
                "index": player_index,
                "movement": 0
            }
            print(f"Player {player_id} joined as player {player_index + 1}")
            
            # Send player assignment
            response = {
                "type": "player_assigned",
                "player_index": player_index
            }
            self.socket.send_multipart([player_id.encode(), json.dumps(response).encode()])
    
    def handle_player_input(self, player_id, data):
        if player_id in self.connected_players:
            self.connected_players[player_id]["movement"] = data["movement"]
    
    def handle_player_disconnect(self, player_id):
        if player_id in self.connected_players:
            del self.connected_players[player_id]
            print(f"Player {player_id} disconnected")
    
    def send_message(self, data):
        if self.is_leader:
            # Broadcast to all followers
            for player_id in self.connected_players:
                try:
                    self.socket.send_multipart([player_id.encode(), json.dumps(data).encode()], zmq.NOBLOCK)
                except zmq.Again:
                    pass
        else:
            # Send to leader
            try:
                self.socket.send(json.dumps(data).encode(), zmq.NOBLOCK)
            except zmq.Again:
                pass
    
    def send_input(self, movement):
        if not self.is_leader:
            self.send_message({
                "type": "input",
                "movement": movement,
                "player_id": self.player_id
            })
    
    def broadcast_game_state(self, game_state):
        if self.is_leader:
            self.send_message({
                "type": "game_state",
                "state": game_state
            })
    
    def get_player_count(self):
        if self.is_leader:
            return len(self.connected_players) + 1  # +1 for leader
        else:
            return 0  # Followers don't know total count
    
    def get_player_movements(self):
        if self.is_leader:
            movements = [0] * (len(self.connected_players) + 1)
            for player_id, player_data in self.connected_players.items():
                index = player_data["index"] + 1  # +1 because leader is index 0
                if index < len(movements):
                    movements[index] = player_data["movement"]
            return movements
        return []
    
    def cleanup(self):
        self.running = False
        if hasattr(self, 'network_thread'):
            self.network_thread.join(timeout=1.0)
        if self.discovery:
            self.discovery.stop()
        self.socket.close()
        self.context.term()

class GameField:
    def __init__(self, num_players):
        self.num_players = max(1, num_players)  # Allow single player for leader waiting
        self.center_x = WIDTH // 2
        self.center_y = HEIGHT // 2
        self.radius = min(WIDTH, HEIGHT) // 2 - 20
        self.walls = []
        self.player_positions = []
        self.setup_field()
    
    def setup_field(self):
        if self.num_players == 1:
            # Single player mode (leader waiting) - use 2-player setup but only show one paddle
            self.walls = [
                ((0, 0), (WIDTH, 0)),
                ((0, HEIGHT-1), (WIDTH, HEIGHT-1))
            ]
            self.player_positions = [
                (20, self.center_y, 0, 0)
            ]
        elif self.num_players == 2:
            self.walls = [
                ((0, 0), (WIDTH, 0)),
                ((0, HEIGHT-1), (WIDTH, HEIGHT-1))
            ]
            self.player_positions = [
                (20, self.center_y, 0, 0),
                (WIDTH-30, self.center_y, 0, 0)
            ]
        elif self.num_players == 4:
            self.walls = [
                ((0, 0), (WIDTH, 0)),
                ((WIDTH, 0), (WIDTH, HEIGHT)),
                ((WIDTH, HEIGHT), (0, HEIGHT)),
                ((0, HEIGHT), (0, 0))
            ]
            self.player_positions = [
                (self.center_x, 20, math.pi/2, 0),
                (WIDTH-30, self.center_y, 0, -math.pi/2),
                (self.center_x, HEIGHT-30, -math.pi/2, math.pi),
                (20, self.center_y, math.pi, math.pi/2)
            ]
        else:
            angle_step = 2 * math.pi / self.num_players
            self.walls = []
            self.player_positions = []
            
            vertices = []
            for i in range(self.num_players):
                angle = i * angle_step - math.pi/2
                x = self.center_x + self.radius * math.cos(angle)
                y = self.center_y + self.radius * math.sin(angle)
                vertices.append((x, y))
            
            for i in range(self.num_players):
                next_i = (i + 1) % self.num_players
                
                wall_start = vertices[i]
                wall_end = vertices[next_i]
                self.walls.append((wall_start, wall_end))
                
                mid_x = (wall_start[0] + wall_end[0]) / 2
                mid_y = (wall_start[1] + wall_end[1]) / 2
                
                wall_angle = math.atan2(wall_end[1] - wall_start[1], wall_end[0] - wall_start[0])
                normal_angle = wall_angle + math.pi/2
                
                offset = 15
                player_x = mid_x - offset * math.cos(normal_angle)
                player_y = mid_y - offset * math.sin(normal_angle)
                
                self.player_positions.append((player_x, player_y, wall_angle, normal_angle))
    
    def draw_walls(self):
        for wall in self.walls:
            pygame.draw.line(screen, GRAY, wall[0], wall[1], 3)

class Striker:
    def __init__(self, field_pos, width, height, speed, color, player_id):
        self.field_pos = field_pos
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
        
    def set_wall_info(self, wall_start, wall_end, wall_angle, normal_angle):
        self.wall_start = wall_start
        self.wall_end = wall_end
        self.wall_angle = wall_angle
        self.normal_angle = normal_angle
        self.update_position()
    
    def update_position(self):
        if self.wall_start is None:
            self.x = 20 if self.player_id == 0 else WIDTH - 30
            self.y = (self.field_pos * (HEIGHT - self.height))
            self.y = max(0, min(HEIGHT - self.height, self.y))
            
            self.corners = [
                (self.x, self.y),
                (self.x + self.width, self.y),
                (self.x + self.width, self.y + self.height),
                (self.x, self.y + self.height)
            ]
            
            self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        else:
            wall_x = self.wall_start[0] + (self.wall_end[0] - self.wall_start[0]) * self.field_pos
            wall_y = self.wall_start[1] + (self.wall_end[1] - self.wall_start[1]) * self.field_pos
            
            offset = 15
            self.x = wall_x + offset * math.cos(self.normal_angle)
            self.y = wall_y + offset * math.sin(self.normal_angle)
            
            cos_a = math.cos(self.wall_angle)
            sin_a = math.sin(self.wall_angle)
            
            hw, hh = self.height/2, self.width/2
            corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
            
            self.corners = []
            for cx, cy in corners:
                rx = cx * cos_a - cy * sin_a + self.x
                ry = cx * sin_a + cy * cos_a + self.y
                self.corners.append((rx, ry))
            
            self.rect = pygame.Rect(self.x - hw, self.y - hh, self.height, self.width)
    
    def update(self, movement, dt):
        if movement != 0:
            if self.wall_start is None:
                self.field_pos += movement * self.speed * dt / HEIGHT
                self.field_pos = max(0.0, min(1.0, self.field_pos))
            else:
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
        if self.wall_start is None:
            return pygame.Rect.colliderect(ball.get_rect(), self.get_rect())
        else:
            return self.point_in_polygon_collision(ball.posx, ball.posy, ball.radius)
    
    def point_in_polygon_collision(self, cx, cy, radius):
        for i in range(len(self.corners)):
            x1, y1 = self.corners[i]
            x2, y2 = self.corners[(i + 1) % len(self.corners)]
            
            dist = self.point_to_line_distance(cx, cy, x1, y1, x2, y2)
            if dist <= radius:
                return True
        
        return False
    
    def point_to_line_distance(self, px, py, x1, y1, x2, y2):
        dx = px - x1
        dy = py - y1
        
        lx = x2 - x1
        ly = y2 - y1
        
        line_len_sq = lx*lx + ly*ly
        if line_len_sq == 0:
            return math.sqrt(dx*dx + dy*dy)
        
        t = max(0, min(1, (dx*lx + dy*ly) / line_len_sq))
        
        closest_x = x1 + t * lx
        closest_y = y1 + t * ly
        
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
        angle = random.random() * 2 * math.pi
        self.xFac = math.cos(angle)
        self.yFac = math.sin(angle)
        self.firstTime = 1
        self.last_player_touched = None
        self.has_been_touched = False
    
    def display(self):
        pygame.draw.circle(screen, self.color, (int(self.posx), int(self.posy)), self.radius)
    
    def update(self, dt, field):
        self.posx += self.speed * self.xFac * dt
        self.posy += self.speed * self.yFac * dt
        
        if field.num_players == 2:
            if self.posx - self.radius <= 0 and self.firstTime:
                self.firstTime = 0
                return 1
            elif self.posx + self.radius >= WIDTH and self.firstTime:
                self.firstTime = 0
                return -1
            
            if self.posy - self.radius <= 0:
                self.posy = self.radius
                self.yFac *= -1
            elif self.posy + self.radius >= HEIGHT:
                self.posy = HEIGHT - self.radius
                self.yFac *= -1
        else:
            for i, wall in enumerate(field.walls):
                if self.check_wall_collision(wall):
                    self.reflect_off_wall(wall)
                    
                    x1, y1 = wall[0]
                    x2, y2 = wall[1]
                    
                    wx = x2 - x1
                    wy = y2 - y1
                    wall_length = math.sqrt(wx*wx + wy*wy)
                    
                    if wall_length > 0:
                        wx /= wall_length
                        wy /= wall_length
                        
                        nx = -wy
                        ny = wx
                        
                        center_dx = field.center_x - self.posx
                        center_dy = field.center_y - self.posy
                        if (nx * center_dx + ny * center_dy) < 0:
                            nx = -nx
                            ny = -ny
                        
                        self.posx += nx * (self.radius + 2)
                        self.posy += ny * (self.radius + 2)
                    
                    if self.has_been_touched and self.last_player_touched is not None:
                        self.firstTime = 0
                        return self.last_player_touched + 1
                    else:
                        break
        
        return 0
    
    def check_wall_collision(self, wall):
        x1, y1 = wall[0]
        x2, y2 = wall[1]
        
        dx = self.posx - x1
        dy = self.posy - y1
        
        wx = x2 - x1
        wy = y2 - y1
        
        wall_length_sq = wx*wx + wy*wy
        if wall_length_sq == 0:
            return False
            
        t = max(0, min(1, (dx*wx + dy*wy) / wall_length_sq))
        
        closest_x = x1 + t * wx
        closest_y = y1 + t * wy
        
        dist_sq = (self.posx - closest_x)**2 + (self.posy - closest_y)**2
        
        return dist_sq <= self.radius**2
    
    def reflect_off_wall(self, wall):
        x1, y1 = wall[0]
        x2, y2 = wall[1]
        
        wx = x2 - x1
        wy = y2 - y1
        wall_length = math.sqrt(wx*wx + wy*wy)
        
        if wall_length == 0:
            return
            
        wx /= wall_length
        wy /= wall_length
        
        nx = -wy
        ny = wx
        
        dot = self.xFac * nx + self.yFac * ny
        self.xFac = self.xFac - 2 * dot * nx
        self.yFac = self.yFac - 2 * dot * ny
    
    def reset(self, field):
        self.posx = field.center_x
        self.posy = field.center_y
        if field.num_players == 2:
            angle = random.choice([-0.5, 0.5, math.pi - 0.5, math.pi + 0.5])
            self.xFac = math.cos(angle)
            self.yFac = math.sin(angle)
        else:
            angle = random.random() * 2 * math.pi
            self.xFac = math.cos(angle)
            self.yFac = math.sin(angle)
        self.firstTime = 1
        self.last_player_touched = None
        self.has_been_touched = False
    
    def hit(self):
        self.xFac *= -1
    
    def player_hit(self, player_id):
        self.last_player_touched = player_id
        self.has_been_touched = True
    
    def get_rect(self):
        return pygame.Rect(self.posx - self.radius, self.posy - self.radius, 
                          self.radius * 2, self.radius * 2)

def create_game_state(field, players, ball, scores):
    """Create serializable game state for network transmission"""
    player_states = []
    for player in players:
        player_states.append({
            "field_pos": player.field_pos,
            "x": player.x,
            "y": player.y,
            "corners": player.corners
        })
    
    return {
        "num_players": field.num_players,
        "ball": {
            "posx": ball.posx,
            "posy": ball.posy,
            "xFac": ball.xFac,
            "yFac": ball.yFac
        },
        "players": player_states,
        "scores": scores
    }

def apply_game_state(state, field, players, ball, scores):
    """Apply received game state to local game objects"""
    if state is None:
        return scores
    
    # Update ball
    ball.posx = state["ball"]["posx"]
    ball.posy = state["ball"]["posy"]
    ball.xFac = state["ball"]["xFac"]
    ball.yFac = state["ball"]["yFac"]
    
    # Update players
    for i, player_state in enumerate(state["players"]):
        if i < len(players):
            players[i].field_pos = player_state["field_pos"]
            players[i].x = player_state["x"]
            players[i].y = player_state["y"]
            players[i].corners = player_state["corners"]
    
    # Update scores
    return state["scores"]

def main():
    parser = argparse.ArgumentParser(description='Multi-Player Pong')
    parser.add_argument('--join', type=str, help='Join game at specific IP address (e.g., --join 192.168.1.100)')
    parser.add_argument('--port', type=int, default=5555, help='Game port number (default: 5555)')
    parser.add_argument('--discovery-port', type=int, default=5556, help='Discovery port number (default: 5556)')
    parser.add_argument('--no-discovery', action='store_true', help='Disable automatic network discovery')
    parser.add_argument('--discovery-timeout', type=int, default=10, help='Discovery timeout in seconds (default: 10)')
    args = parser.parse_args()
    
    # Initialize network discovery
    discovery = None if args.no_discovery else NetworkDiscovery(args.port, args.discovery_port)
    
    # Determine if this is leader or follower
    is_leader = args.join is None
    leader_ip = args.join if args.join else "127.0.0.1"
    
    if not is_leader and not args.join and discovery:
        # Auto-discover leader
        print("Searching for game leaders on the network...")
        discovered_leaders = discovery.start_discovery_listener(args.discovery_timeout)
        
        if discovered_leaders:
            best_leader = discovery.get_best_leader()
            if best_leader:
                leader_ip = best_leader["ip"]
                leader_port = best_leader["port"]
                print(f"Found leader at {leader_ip}:{leader_port}")
                
                # Update port if leader uses different port
                if leader_port != args.port:
                    args.port = leader_port
            else:
                print("No active leaders found. Starting as leader...")
                is_leader = True
        else:
            print("No leaders discovered. Starting as leader...")
            is_leader = True
    elif not is_leader and args.join:
        print(f"Connecting to specified leader at {args.join}:{args.port}")
    
    # Initialize network
    network = NetworkManager(is_leader=is_leader, leader_port=args.port, leader_ip=leader_ip, discovery=discovery)
    
    running = True
    colors = [GREEN, RED, BLUE, YELLOW, PURPLE, ORANGE, CYAN, WHITE]
    
    # Control keys for each player
    player_keys = [
        (pygame.K_w, pygame.K_s),      # Player 1: W/S
        (pygame.K_UP, pygame.K_DOWN),  # Player 2: UP/DOWN
        (pygame.K_t, pygame.K_g),      # Player 3: T/G
        (pygame.K_i, pygame.K_k),      # Player 4: I/K
        (pygame.K_r, pygame.K_f),      # Player 5: R/F
        (pygame.K_u, pygame.K_j),      # Player 6: U/J
        (pygame.K_o, pygame.K_l),      # Player 7: O/L
        (pygame.K_p, pygame.K_SEMICOLON) # Player 8: P/;
    ]
    
    def setup_game(num_players, existing_scores=None):
        field = GameField(num_players)
        
        players = []
        for i in range(num_players):
            paddle_speed = 600
            ball_speed = 400
            
            color = colors[i % len(colors)]
            player = Striker(0.5, 10, 100, paddle_speed, color, i)
            
            if field.num_players <= 2:
                player.update_position()
            else:
                if i < len(field.walls):
                    wall_start, wall_end = field.walls[i]
                    wall_angle = math.atan2(wall_end[1] - wall_start[1], wall_end[0] - wall_start[0])  # Fixed typo: wallEnd -> wall_end
                    normal_angle = wall_angle + math.pi/2
                    player.set_wall_info(wall_start, wall_end, wall_angle, normal_angle)
            players.append(player)
        
        ball = Ball(field.center_x, field.center_y, 8, ball_speed, WHITE)
        
        if field.num_players <= 2:
            angle = random.choice([-0.5, 0.5, math.pi - 0.5, math.pi + 0.5])
            ball.xFac = math.cos(angle)
            ball.yFac = math.sin(angle)
        else:
            angle = random.random() * 2 * math.pi
            ball.xFac = math.cos(angle)
            ball.yFac = math.sin(angle)
        
        # Preserve existing scores or create new ones
        if existing_scores and len(existing_scores) >= num_players:
            scores = existing_scores[:num_players]
        else:
            scores = [0] * num_players
            if existing_scores:
                for i in range(min(len(existing_scores), num_players)):
                    scores[i] = existing_scores[i]
        
        return field, players, ball, scores
    
    # Initial setup
    current_num_players = 1 if is_leader else 2  # Leader starts with 1 player
    field, players, ball, scores = setup_game(current_num_players)
    movements = [0] * 8  # Support up to 8 players
    my_player_index = 0 if is_leader else getattr(network, 'my_player_index', 1)
    last_num_players = current_num_players
    
    print(f"Started as {'leader' if is_leader else 'follower'}")
    if is_leader:
        print("Waiting for other players to join...")
        if not args.no_discovery:
            print("Broadcasting presence for automatic discovery...")
        print(f"Manual connection: python basic_pong.py --join {leader_ip} --port {args.port}")
    
    while running:
        dt = clock.tick(60) / 1000.0
        dt = min(dt, 1/30.0)
        
        screen.fill(BLACK)
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.KEYDOWN:
                # Reset button (only for leader)
                if event.key == pygame.K_SPACE and is_leader:
                    scores = [0] * len(scores)
                    ball.reset(field)
                
                # Player movement
                if is_leader:
                    player_index = 0  # Leader is always player 0
                else:
                    player_index = getattr(network, 'my_player_index', -1)
                
                if 0 <= player_index < len(player_keys):
                    if event.key == player_keys[player_index][0]:  # Up/Left key
                        movements[player_index] = -1
                        if not is_leader:
                            network.send_input(-1)
                    elif event.key == player_keys[player_index][1]:  # Down/Right key
                        movements[player_index] = 1
                        if not is_leader:
                            network.send_input(1)
            
            if event.type == pygame.KEYUP:
                if is_leader:
                    player_index = 0
                else:
                    player_index = getattr(network, 'my_player_index', -1)
                
                if 0 <= player_index < len(player_keys):
                    if event.key in player_keys[player_index]:
                        movements[player_index] = 0
                        if not is_leader:
                            network.send_input(0)
        
        # Leader game logic
        if is_leader:
            # Check for new players and adjust game
            total_players = network.get_player_count()
            # Only force minimum 2 players if there are actually followers connected
            current_num_players = max(1, total_players) if total_players == 1 else max(2, total_players)
            
            if current_num_players != last_num_players:
                print(f"Player count changed: {last_num_players} -> {current_num_players}")
                field, players, ball, scores = setup_game(current_num_players, scores)
                last_num_players = current_num_players
            
            # Get movements from network
            network_movements = network.get_player_movements()
            for i, movement in enumerate(network_movements):
                if i < len(movements):
                    movements[i] = movement
            
            # Update game objects
            for i, player in enumerate(players):
                if i < len(movements):
                    player.update(movements[i], dt)
            
            # Only update ball and check collisions if we have at least 2 players
            if current_num_players >= 2:
                # Ball collision with paddles
                ball_hit_paddle = False
                for player in players:
                    if player.check_ball_collision(ball):
                        ball.player_hit(player.player_id)
                        
                        if field.num_players == 2:
                            if player.player_id == 0 and ball.posx < player.x + player.width:
                                ball.posx = player.x + player.width + ball.radius
                            elif player.player_id == 1 and ball.posx > player.x:
                                ball.posx = player.x - ball.radius
                        else:
                            nx = math.cos(player.normal_angle)
                            ny = math.sin(player.normal_angle)
                            
                            dot = ball.xFac * nx + ball.yFac * ny
                            ball.xFac = ball.xFac - 2 * dot * nx
                            ball.yFac = ball.yFac - 2 * dot * ny
                            
                            ball.posx += nx * (ball.radius + 5)
                            ball.posy += ny * (ball.radius + 5)
                        
                        if field.num_players == 2:
                            ball.hit()
                        
                        ball_hit_paddle = True
                        break
                
                # Update ball
                point = 0
                if not ball_hit_paddle:
                    point = ball.update(dt, field)
                else:
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
                        scoring_player = point - 1
                        if 0 <= scoring_player < len(scores):
                            scores[scoring_player] += 1
                    
                    ball.reset(field)
            
            # Broadcast game state to followers (even if only 1 player, for when 2nd joins)
            if network.get_player_count() > 1:
                game_state = create_game_state(field, players, ball, scores)
                network.broadcast_game_state(game_state)
        
        else:
            # Follower: apply received game state
            if hasattr(network, 'game_state') and network.game_state:
                scores = apply_game_state(network.game_state, field, players, ball, scores)
                
                # Check if we need to recreate game objects due to player count change
                new_num_players = network.game_state.get("num_players", 2)
                if new_num_players != current_num_players:
                    current_num_players = new_num_players
                    field, players, ball, scores = setup_game(current_num_players, scores)
        
        # Draw everything
        field.draw_walls()
        
        for i, player in enumerate(players):
            player.display()
            # Highlight current player
            if i == my_player_index:
                # Draw a small circle above the paddle to indicate it's controlled by this client
                if hasattr(player, 'x') and hasattr(player, 'y'):
                    pygame.draw.circle(screen, WHITE, (int(player.x), int(player.y - 20)), 5)
        
        # Only draw ball if we have at least 2 players
        if current_num_players >= 2 or not is_leader:
            ball.display()
        
        # Display scores and info
        y_offset = 20
        for i in range(len(scores)):
            color = colors[i % len(colors)]
            score_text = font20.render(f"Player {i+1}: {scores[i]}", True, color)
            screen.blit(score_text, (10, y_offset + i * 25))
        
        # Show waiting message when leader is alone
        if is_leader and current_num_players == 1:
            waiting_text = font20.render("Waiting for players to join...", True, YELLOW)
            text_rect = waiting_text.get_rect(center=(WIDTH//2, HEIGHT//2))
            screen.blit(waiting_text, text_rect)
        
        # Display role and player info
        role_text = font16.render(f"Role: {'Leader' if is_leader else 'Follower'}", True, WHITE)
        screen.blit(role_text, (10, HEIGHT - 80))
        
        if is_leader:
            player_count_text = font16.render(f"Players: {current_num_players}", True, WHITE)
            screen.blit(player_count_text, (10, HEIGHT - 60))
            reset_text = font16.render("Press SPACE to reset scores", True, WHITE)
            screen.blit(reset_text, (10, HEIGHT - 40))
        else:
            my_player_text = font16.render(f"You are Player {getattr(network, 'my_player_index', 0) + 1}", True, WHITE)
            screen.blit(my_player_text, (10, HEIGHT - 60))
        
        connection_text = font16.render(f"Network: {'Active' if (is_leader and network.get_player_count() > 1) or (not is_leader and hasattr(network, 'game_state')) else 'Waiting...'}", True, GREEN if (is_leader and network.get_player_count() > 1) or (not is_leader and hasattr(network, 'game_state')) else RED)
        screen.blit(connection_text, (10, HEIGHT - 20))
        
        pygame.display.update()
    
    # Cleanup
    network.cleanup()
    pygame.quit()

if __name__ == "__main__":
    main()