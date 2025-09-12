import socket
import json
import threading
import time
import uuid
import struct
from typing import Dict, List, Optional, Tuple

class NetworkManager:
    GAME_PORT = 15243
    MULTICAST_GROUP = "224.1.1.1"
    HEARTBEAT_INTERVAL = 1.0
    HEARTBEAT_TIMEOUT = 3.0
    
    def __init__(self):
        self.player_id = str(uuid.uuid4())
        self.player_ip = self._get_local_ip()
        self.is_leader = False
        self.leader_id = None
        self.leader_ip = None
        self.players = {}  # {player_id: {"ip": str, "last_heartbeat": float}}
        self.player_inputs = {}  # {player_id: paddle_position}
        self.latest_game_state = None
        
        # Network sockets
        self.udp_socket = None
        self.tcp_socket = None
        self.tcp_connections = {}  # {player_id: socket}
        
        # Threading
        self.running = False
        self.threads = []
        
        # Election state
        self.election_in_progress = False
        self.election_responses = set()
        
    def _get_local_ip(self) -> str:
        """Get the local IP address."""
        try:
            # Connect to a remote server to determine local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except:
            return "127.0.0.1"
    
    def start_as_host(self):
        """Start this instance as the game host/leader."""
        self.is_leader = True
        self.leader_id = self.player_id
        self.leader_ip = self.player_ip
        self.players[self.player_id] = {
            "ip": self.player_ip,
            "last_heartbeat": time.time()
        }
        
        self._setup_sockets()
        self._start_threads()
        print(f"Started as host with ID: {self.player_id}")
    
    def discover_and_join(self) -> bool:
        """Discover and join an existing game. Returns True if successful."""
        self._setup_discovery_socket()
        
        # Send discovery request
        discovery_msg = {
            "type": "DISCOVERY_REQUEST",
            "data": {"playerId": self.player_id}
        }
        
        # Broadcast discovery request
        broadcast_addr = ('<broadcast>', self.GAME_PORT)
        self.udp_socket.sendto(json.dumps(discovery_msg).encode(), broadcast_addr)
        
        # Wait for response
        self.udp_socket.settimeout(3.0)
        try:
            data, addr = self.udp_socket.recvfrom(1024)
            response = json.loads(data.decode())
            
            if response["type"] == "DISCOVERY_RESPONSE":
                self.leader_id = response["data"]["leaderId"]
                self.leader_ip = response["data"]["leaderIp"]
                self.players = {p["id"]: {"ip": p["ip"], "last_heartbeat": time.time()} 
                              for p in response["data"]["players"]}
                
                # Add ourselves to the player list
                self.players[self.player_id] = {
                    "ip": self.player_ip,
                    "last_heartbeat": time.time()
                }
                
                print(f"Received player list: {[p[:8] for p in self.players.keys()]}")
                
                # Establish TCP connection to leader
                self._connect_to_leader()
                
                # Setup proper UDP socket for game communication
                self.udp_socket.close()
                self._setup_game_socket()
                
                self._start_threads()
                print(f"Joined game with leader: {self.leader_id}")
                return True
                
        except socket.timeout:
            pass
        except Exception as e:
            print(f"Error during discovery: {e}")
        
        return False
    
    def _setup_sockets(self):
        """Setup UDP and TCP sockets."""
        # UDP socket for game communication
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.bind(('', self.GAME_PORT))
        
        # Multicast setup
        mreq = struct.pack("4sl", socket.inet_aton(self.MULTICAST_GROUP), socket.INADDR_ANY)
        self.udp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        
        if self.is_leader:
            # TCP socket for reliable connections
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_socket.settimeout(1.0)  # Add timeout to prevent hanging
            self.tcp_socket.bind(('', self.GAME_PORT))
            self.tcp_socket.listen(5)
    
    def _setup_discovery_socket(self):
        """Setup UDP socket for discovery."""
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.bind(('', 0))  # Bind to any available port
    
    def _setup_game_socket(self):
        """Setup UDP socket for game communication after discovery."""
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.settimeout(None)  # Remove timeout for game socket
        self.udp_socket.bind(('', self.GAME_PORT))
        
        # Multicast setup
        mreq = struct.pack("4sl", socket.inet_aton(self.MULTICAST_GROUP), socket.INADDR_ANY)
        self.udp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    
    def _connect_to_leader(self):
        """Connect to the leader via TCP."""
        tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_client.connect((self.leader_ip, self.GAME_PORT))
        
        # Send join message
        join_msg = {
            "type": "PLAYER_JOIN",
            "data": {
                "playerId": self.player_id,
                "playerIp": self.player_ip
            }
        }
        tcp_client.send(json.dumps(join_msg).encode())
        tcp_client.close()
    
    def _start_threads(self):
        """Start network threads."""
        self.running = True
        
        # UDP listener thread
        udp_thread = threading.Thread(target=self._udp_listener, daemon=True)
        udp_thread.start()
        self.threads.append(udp_thread)
        
        if self.is_leader:
            # TCP listener thread for new connections
            tcp_thread = threading.Thread(target=self._tcp_listener, daemon=True)
            tcp_thread.start()
            self.threads.append(tcp_thread)
            
            # Heartbeat thread
            heartbeat_thread = threading.Thread(target=self._heartbeat_sender, daemon=True)
            heartbeat_thread.start()
            self.threads.append(heartbeat_thread)
        else:
            # Heartbeat monitor thread
            monitor_thread = threading.Thread(target=self._heartbeat_monitor, daemon=True)
            monitor_thread.start()
            self.threads.append(monitor_thread)
    
    def _udp_listener(self):
        """Listen for UDP messages."""
        while self.running:
            try:
                data, addr = self.udp_socket.recvfrom(1024)
                message = json.loads(data.decode())
                self._handle_udp_message(message, addr)
            except Exception as e:
                if self.running:
                    print(f"UDP listener error: {e}")
    
    def _tcp_listener(self):
        """Listen for TCP connections (leader only)."""
        while self.running:
            try:
                conn, addr = self.tcp_socket.accept()
                conn.settimeout(5.0)  # Set timeout for data read
                data = conn.recv(1024)
                if data:
                    message = json.loads(data.decode())
                    self._handle_tcp_message(message, addr, conn)
                conn.close()
            except socket.timeout:
                # Normal timeout, just continue
                continue
            except Exception as e:
                if self.running:
                    print(f"TCP listener error: {e}")
    
    def _handle_udp_message(self, message: dict, addr: tuple):
        """Handle incoming UDP messages."""
        msg_type = message["type"]
        
        # Ignore messages from ourselves
        if "data" in message and "playerId" in message["data"] and message["data"]["playerId"] == self.player_id:
            return
        if "data" in message and "senderId" in message["data"] and message["data"]["senderId"] == self.player_id:
            return
        if "data" in message and "newLeaderId" in message["data"] and message["data"]["newLeaderId"] == self.player_id:
            return
        
        if msg_type == "DISCOVERY_REQUEST" and self.is_leader:
            self._handle_discovery_request(message, addr)
        elif msg_type == "PADDLE_INPUT":
            self._handle_paddle_input(message)
        elif msg_type == "GAME_STATE":
            self._handle_game_state(message)
        elif msg_type == "PLAYER_JOIN" and not self.is_leader:
            # Only clients should handle PLAYER_JOIN UDP broadcasts
            self._handle_player_join_broadcast(message)
        elif msg_type == "ELECTION":
            self._handle_election_message(message, addr)
        elif msg_type == "ELECTION_OKAY":
            self._handle_election_okay(message)
        elif msg_type == "NEW_LEADER":
            self._handle_new_leader(message)
    
    def _handle_tcp_message(self, message: dict, addr: tuple, conn: socket.socket):
        """Handle incoming TCP messages."""
        if message["type"] == "PLAYER_JOIN":
            self._handle_player_join(message, addr)
        conn.close()
    
    def _handle_discovery_request(self, message: dict, addr: tuple):
        """Handle discovery request from new player."""
        player_id = message["data"]["playerId"]
        
        response = {
            "type": "DISCOVERY_RESPONSE",
            "data": {
                "leaderId": self.leader_id,
                "leaderIp": self.leader_ip,
                "players": [{"id": pid, "ip": pdata["ip"]} 
                           for pid, pdata in self.players.items()]
            }
        }
        
        self.udp_socket.sendto(json.dumps(response).encode(), addr)
    
    def _handle_player_join(self, message: dict, addr: tuple):
        """Handle player join request."""
        player_id = message["data"]["playerId"]
        player_ip = message["data"]["playerIp"]
        
        # Add player to our list
        self.players[player_id] = {
            "ip": player_ip,
            "last_heartbeat": time.time()
        }
        
        print(f"Player {player_id[:8]}... joined from {player_ip}")
        
        # Notify all other players (but not ourselves via UDP)
        join_notification = {
            "type": "PLAYER_JOIN",
            "data": {
                "playerId": player_id,
                "playerIp": player_ip
            }
        }
        self._broadcast_udp(join_notification)
    
    def _handle_player_join_broadcast(self, message: dict):
        """Handle player join broadcast from leader (clients only)."""
        player_id = message["data"]["playerId"]
        player_ip = message["data"]["playerIp"]
        
        # Add player to our local list
        self.players[player_id] = {
            "ip": player_ip,
            "last_heartbeat": time.time()
        }
        
        print(f"Player {player_id[:8]}... joined the game")
    
    def _handle_paddle_input(self, message: dict):
        """Handle paddle input from players."""
        player_id = message["data"]["playerId"]
        paddle_position = message["data"]["paddlePosition"]
        self.player_inputs[player_id] = paddle_position
    
    def _handle_game_state(self, message: dict):
        """Handle game state update from leader."""
        self.latest_game_state = message["data"]
        # Update heartbeat for leader
        if self.leader_id in self.players:
            self.players[self.leader_id]["last_heartbeat"] = time.time()
    
    def _heartbeat_sender(self):
        """Send heartbeat messages (leader only)."""
        while self.running and self.is_leader:
            # Heartbeat is sent as part of game state updates
            time.sleep(self.HEARTBEAT_INTERVAL)
    
    def _heartbeat_monitor(self):
        """Monitor leader heartbeat (clients only)."""
        while self.running and not self.is_leader:
            time.sleep(1.0)
            
            if self.leader_id in self.players:
                last_heartbeat = self.players[self.leader_id]["last_heartbeat"]
                if time.time() - last_heartbeat > self.HEARTBEAT_TIMEOUT:
                    print("Leader timeout detected, starting election...")
                    self._start_election()
                    break
    
    def _start_election(self):
        """Start leader election using Bully algorithm."""
        if self.election_in_progress:
            return
            
        self.election_in_progress = True
        self.election_responses.clear()
        
        # Send election messages to players with higher IDs
        election_msg = {
            "type": "ELECTION",
            "data": {"senderId": self.player_id}
        }
        
        higher_id_players = [pid for pid in self.players.keys() if pid > self.player_id]
        
        for player_id in higher_id_players:
            player_ip = self.players[player_id]["ip"]
            try:
                self.udp_socket.sendto(
                    json.dumps(election_msg).encode(),
                    (player_ip, self.GAME_PORT)
                )
            except Exception as e:
                print(f"Failed to send election message to {player_id}: {e}")
        
        # Wait for responses
        time.sleep(2.0)
        
        if not self.election_responses:
            # No responses, we are the new leader
            self._become_leader()
        
        self.election_in_progress = False
    
    def _handle_election_message(self, message: dict, addr: tuple):
        """Handle election message."""
        sender_id = message["data"]["senderId"]
        
        # Send okay response if we have higher ID
        if self.player_id > sender_id:
            okay_msg = {
                "type": "ELECTION_OKAY",
                "data": {"senderId": self.player_id}
            }
            self.udp_socket.sendto(json.dumps(okay_msg).encode(), addr)
            
            # Start our own election only if we're not already leader
            if not self.election_in_progress and not self.is_leader:
                self._start_election()
    
    def _handle_election_okay(self, message: dict):
        """Handle election okay response."""
        sender_id = message["data"]["senderId"]
        self.election_responses.add(sender_id)
    
    def _handle_new_leader(self, message: dict):
        """Handle new leader announcement."""
        self.leader_id = message["data"]["newLeaderId"]
        self.leader_ip = message["data"]["newLeaderIp"]
        self.is_leader = False
        print(f"New leader elected: {self.leader_id}")
    
    def _become_leader(self):
        """Become the new leader."""
        self.is_leader = True
        self.leader_id = self.player_id
        self.leader_ip = self.player_ip
        
        # Announce leadership
        leader_msg = {
            "type": "NEW_LEADER",
            "data": {
                "newLeaderId": self.player_id,
                "newLeaderIp": self.player_ip
            }
        }
        self._broadcast_udp(leader_msg)
        
        print(f"Became new leader: {self.player_id}")
    
    def _broadcast_udp(self, message: dict):
        """Broadcast UDP message to all players."""
        data = json.dumps(message).encode()
        self.udp_socket.sendto(data, (self.MULTICAST_GROUP, self.GAME_PORT))
    
    def send_paddle_input(self, paddle_position: float):
        """Send paddle input to leader."""
        if not self.is_leader and self.leader_ip:
            input_msg = {
                "type": "PADDLE_INPUT",
                "data": {
                    "playerId": self.player_id,
                    "paddlePosition": paddle_position
                }
            }
            try:
                self.udp_socket.sendto(
                    json.dumps(input_msg).encode(),
                    (self.leader_ip, self.GAME_PORT)
                )
            except Exception as e:
                print(f"Failed to send paddle input: {e}")
    
    def broadcast_game_state(self, game_state: dict):
        """Broadcast game state to all players (leader only)."""
        if self.is_leader:
            state_msg = {
                "type": "GAME_STATE",
                "data": game_state
            }
            self._broadcast_udp(state_msg)
    
    def get_player_inputs(self) -> Dict[str, float]:
        """Get latest player inputs."""
        return self.player_inputs.copy()
    
    def get_latest_game_state(self) -> Optional[dict]:
        """Get the latest game state."""
        return self.latest_game_state
    
    def get_players(self) -> List[str]:
        """Get list of connected player IDs."""
        return list(self.players.keys())
    
    def process_messages(self):
        """Process any pending network messages. Called from main loop."""
        # Network processing is handled by background threads
        pass
    
    def shutdown(self):
        """Shutdown network manager."""
        self.running = False
        
        if self.udp_socket:
            self.udp_socket.close()
        if self.tcp_socket:
            self.tcp_socket.close()
        
        for conn in self.tcp_connections.values():
            conn.close()
        
        # Wait for threads to finish
        for thread in self.threads:
            thread.join(timeout=1.0)