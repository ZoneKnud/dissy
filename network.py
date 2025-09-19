import socket
import threading
import json
import time
import uuid
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

class MessageType(Enum):
    DISCOVERY_REQUEST = "DISCOVERY_REQUEST"
    DISCOVERY_RESPONSE = "DISCOVERY_RESPONSE"
    PLAYER_JOIN = "PLAYER_JOIN"
    PLAYER_LEAVE = "PLAYER_LEAVE"
    PADDLE_INPUT = "PADDLE_INPUT"
    GAME_STATE = "GAME_STATE"
    HEARTBEAT = "HEARTBEAT"
    ELECTION = "ELECTION"
    ELECTION_OKAY = "ELECTION_OKAY"
    NEW_LEADER = "NEW_LEADER"

@dataclass
class Player:
    id: str
    ip: str
    last_heartbeat: float = 0.0

class NetworkManager:
    GAME_PORT = 15243
    HEARTBEAT_INTERVAL = 1.0  # seconds
    HEARTBEAT_TIMEOUT = 3.0   # seconds
    MULTICAST_GROUP = "224.1.1.1"
    
    def __init__(self, on_message_callback: Callable = None):
        self.player_id = str(uuid.uuid4())
        self.local_ip = self._get_local_ip()
        self.is_leader = False
        self.leader_id = None
        self.leader_ip = None
        self.players: Dict[str, Player] = {}
        self.running = False
        
        # Sockets
        self.udp_socket = None
        self.tcp_socket = None
        self.multicast_socket = None
        
        # Threads
        self.udp_listener_thread = None
        self.tcp_listener_thread = None
        self.heartbeat_thread = None
        self.election_thread = None
        
        # Callbacks
        self.on_message_callback = on_message_callback
        
        # Election state
        self.election_in_progress = False
        self.election_responses = set()
        
    def _get_local_ip(self) -> str:
        """Get the local IP address"""
        try:
            # Create a socket and connect to a remote server to get local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
    
    def start(self):
        """Start the network manager"""
        self.running = True
        self._setup_sockets()
        self._start_threads()
        
        # Start discovery process
        self._discover_leader()
    
    def stop(self):
        """Stop the network manager"""
        self.running = False
        
        # Send leave message if not leader
        if not self.is_leader and self.leader_ip:
            self._send_player_leave()
        
        # Close sockets
        if self.udp_socket:
            self.udp_socket.close()
        if self.tcp_socket:
            self.tcp_socket.close()
        if self.multicast_socket:
            self.multicast_socket.close()
    
    def _setup_sockets(self):
        """Setup UDP and TCP sockets"""
        # UDP socket for discovery and communication
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.bind(('', self.GAME_PORT))
        
        # Multicast socket for game state broadcasting
        self.multicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.multicast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # TCP socket for reliable communication
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
    def _start_threads(self):
        """Start listener threads"""
        self.udp_listener_thread = threading.Thread(target=self._udp_listener, daemon=True)
        self.udp_listener_thread.start()
        
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_monitor, daemon=True)
        self.heartbeat_thread.start()
    
    def _discover_leader(self):
        """Send discovery request to find existing leader"""
        message = {
            "type": MessageType.DISCOVERY_REQUEST.value,
            "data": {
                "playerId": self.player_id,
                "playerIp": self.local_ip
            }
        }
        
        # Send broadcast
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        broadcast_socket.sendto(json.dumps(message).encode(), ('<broadcast>', self.GAME_PORT))
        broadcast_socket.close()
        
        # Wait for response for 2 seconds
        time.sleep(2.0)
        
        # If no leader found, become leader
        if not self.leader_id:
            self._become_leader()
    
    def _become_leader(self):
        """Become the leader of the network"""
        print(f"Becoming leader with ID: {self.player_id}")
        self.is_leader = True
        self.leader_id = self.player_id
        self.leader_ip = self.local_ip
        
        # Add self to players list
        self.players[self.player_id] = Player(
            id=self.player_id,
            ip=self.local_ip,
            last_heartbeat=time.time()
        )
        
        # Start TCP server for incoming connections
        self._start_tcp_server()
    
    def _start_tcp_server(self):
        """Start TCP server for reliable connections"""
        if self.tcp_listener_thread and self.tcp_listener_thread.is_alive():
            return
            
        self.tcp_socket.bind((self.local_ip, self.GAME_PORT))
        self.tcp_socket.listen(5)
        
        self.tcp_listener_thread = threading.Thread(target=self._tcp_listener, daemon=True)
        self.tcp_listener_thread.start()
    
    def _tcp_listener(self):
        """Listen for incoming TCP connections"""
        while self.running:
            try:
                client_socket, address = self.tcp_socket.accept()
                threading.Thread(
                    target=self._handle_tcp_client,
                    args=(client_socket, address),
                    daemon=True
                ).start()
            except Exception as e:
                if self.running:
                    print(f"TCP listener error: {e}")
    
    def _handle_tcp_client(self, client_socket, address):
        """Handle TCP client connection"""
        try:
            while self.running:
                data = client_socket.recv(1024)
                if not data:
                    break
                
                message = json.loads(data.decode())
                self._handle_message(message, address[0])
        except Exception as e:
            print(f"TCP client handler error: {e}")
        finally:
            client_socket.close()
    
    def _udp_listener(self):
        """Listen for UDP messages"""
        while self.running:
            try:
                data, addr = self.udp_socket.recvfrom(1024)
                message = json.loads(data.decode())
                self._handle_message(message, addr[0])
            except Exception as e:
                if self.running:
                    print(f"UDP listener error: {e}")
    
    def _handle_message(self, message: dict, sender_ip: str):
        """Handle incoming message"""
        msg_type = message.get("type")
        data = message.get("data", {})
        
        if msg_type == MessageType.DISCOVERY_REQUEST.value:
            self._handle_discovery_request(data, sender_ip)
        elif msg_type == MessageType.DISCOVERY_RESPONSE.value:
            self._handle_discovery_response(data, sender_ip)
        elif msg_type == MessageType.PLAYER_JOIN.value:
            self._handle_player_join(data, sender_ip)
        elif msg_type == MessageType.HEARTBEAT.value:
            self._handle_heartbeat(data, sender_ip)
        elif msg_type == MessageType.ELECTION.value:
            self._handle_election(data, sender_ip)
        elif msg_type == MessageType.ELECTION_OKAY.value:
            self._handle_election_okay(data, sender_ip)
        elif msg_type == MessageType.NEW_LEADER.value:
            self._handle_new_leader(data, sender_ip)
        
        # Call user callback if provided
        if self.on_message_callback:
            self.on_message_callback(message, sender_ip)
    
    def _handle_discovery_request(self, data: dict, sender_ip: str):
        """Handle discovery request from new player"""
        if not self.is_leader:
            return
        
        player_id = data.get("playerId")
        
        # Send response with current players list
        response = {
            "type": MessageType.DISCOVERY_RESPONSE.value,
            "data": {
                "leaderId": self.leader_id,
                "leaderIp": self.leader_ip,
                "players": [{"id": p.id, "ip": p.ip} for p in self.players.values()]
            }
        }
        
        # Send unicast response
        response_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        response_socket.sendto(json.dumps(response).encode(), (sender_ip, self.GAME_PORT))
        response_socket.close()
        
        # Add new player to the list
        self.players[player_id] = Player(
            id=player_id,
            ip=sender_ip,
            last_heartbeat=time.time()
        )
        
        print(f"New player joined: {player_id} from {sender_ip}")
    
    def _handle_discovery_response(self, data: dict, sender_ip: str):
        """Handle discovery response from leader"""
        if self.is_leader:
            return
        
        self.leader_id = data.get("leaderId")
        self.leader_ip = data.get("leaderIp")
        
        # Update players list
        players_data = data.get("players", [])
        for player_data in players_data:
            self.players[player_data["id"]] = Player(
                id=player_data["id"],
                ip=player_data["ip"],
                last_heartbeat=time.time()
            )
        
        print(f"Found leader: {self.leader_id} at {self.leader_ip}")
        print(f"Players in network: {len(self.players)}")
    
    def _handle_player_join(self, data: dict, sender_ip: str):
        """Handle player join notification"""
        player_id = data.get("playerId")
        player_ip = data.get("playerIp")
        
        if player_id not in self.players:
            self.players[player_id] = Player(
                id=player_id,
                ip=player_ip,
                last_heartbeat=time.time()
            )
            print(f"Player joined: {player_id}")
    
    def _handle_heartbeat(self, data: dict, sender_ip: str):
        """Handle heartbeat from leader"""
        if sender_ip == self.leader_ip:
            # Update leader's last heartbeat time
            if self.leader_id in self.players:
                self.players[self.leader_id].last_heartbeat = time.time()
    
    def _handle_election(self, data: dict, sender_ip: str):
        """Handle election message"""
        sender_id = data.get("senderId")
        
        # If our ID is higher, send OKAY and start our own election
        if self.player_id > sender_id:
            self._send_election_okay(sender_ip)
            self._start_election()
    
    def _handle_election_okay(self, data: dict, sender_ip: str):
        """Handle election okay response"""
        if self.election_in_progress:
            self.election_responses.add(data.get("senderId"))
    
    def _handle_new_leader(self, data: dict, sender_ip: str):
        """Handle new leader announcement"""
        self.leader_id = data.get("newLeaderId")
        self.leader_ip = data.get("newLeaderIp")
        self.election_in_progress = False
        
        print(f"New leader elected: {self.leader_id}")
    
    def _heartbeat_monitor(self):
        """Monitor heartbeats and detect leader failure"""
        while self.running:
            time.sleep(1.0)
            
            if not self.is_leader and self.leader_id:
                # Check if leader is still alive
                leader = self.players.get(self.leader_id)
                if leader and time.time() - leader.last_heartbeat > self.HEARTBEAT_TIMEOUT:
                    print("Leader timeout detected, starting election")
                    self._start_election()
            elif self.is_leader:
                # Send heartbeat as leader
                self._send_heartbeat()
    
    def _start_election(self):
        """Start leader election using bully algorithm"""
        if self.election_in_progress:
            return
        
        self.election_in_progress = True
        self.election_responses.clear()
        
        # Send election message to all players with higher IDs
        higher_id_players = [p for p in self.players.values() if p.id > self.player_id]
        
        if not higher_id_players:
            # No higher ID players, become leader
            self._become_leader()
            self._announce_new_leader()
            return
        
        # Send election messages
        for player in higher_id_players:
            self._send_election(player.ip)
        
        # Wait for responses
        time.sleep(2.0)
        
        # If no responses, become leader
        if not self.election_responses:
            self._become_leader()
            self._announce_new_leader()
        
        self.election_in_progress = False
    
    def _send_election(self, target_ip: str):
        """Send election message"""
        message = {
            "type": MessageType.ELECTION.value,
            "data": {"senderId": self.player_id}
        }
        
        try:
            election_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            election_socket.sendto(json.dumps(message).encode(), (target_ip, self.GAME_PORT))
            election_socket.close()
        except Exception as e:
            print(f"Failed to send election message: {e}")
    
    def _send_election_okay(self, target_ip: str):
        """Send election okay response"""
        message = {
            "type": MessageType.ELECTION_OKAY.value,
            "data": {"senderId": self.player_id}
        }
        
        try:
            okay_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            okay_socket.sendto(json.dumps(message).encode(), (target_ip, self.GAME_PORT))
            okay_socket.close()
        except Exception as e:
            print(f"Failed to send election okay: {e}")
    
    def _announce_new_leader(self):
        """Announce that this node is the new leader"""
        message = {
            "type": MessageType.NEW_LEADER.value,
            "data": {
                "newLeaderId": self.player_id,
                "newLeaderIp": self.local_ip
            }
        }
        
        # Send to all known players
        for player in self.players.values():
            if player.id != self.player_id:
                try:
                    announce_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    announce_socket.sendto(json.dumps(message).encode(), (player.ip, self.GAME_PORT))
                    announce_socket.close()
                except Exception as e:
                    print(f"Failed to announce new leader to {player.ip}: {e}")
    
    def _send_heartbeat(self):
        """Send heartbeat as leader"""
        message = {
            "type": MessageType.HEARTBEAT.value,
            "data": {
                "leaderId": self.player_id,
                "timestamp": time.time()
            }
        }
        
        # Send to all players
        for player in self.players.values():
            if player.id != self.player_id:
                try:
                    heartbeat_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    heartbeat_socket.sendto(json.dumps(message).encode(), (player.ip, self.GAME_PORT))
                    heartbeat_socket.close()
                except Exception as e:
                    print(f"Failed to send heartbeat to {player.ip}: {e}")
    
    def _send_player_leave(self):
        """Send player leave message"""
        if not self.leader_ip:
            return
            
        message = {
            "type": MessageType.PLAYER_LEAVE.value,
            "data": {
                "playerId": self.player_id
            }
        }
        
        try:
            leave_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            leave_socket.sendto(json.dumps(message).encode(), (self.leader_ip, self.GAME_PORT))
            leave_socket.close()
        except Exception as e:
            print(f"Failed to send leave message: {e}")
    
    def get_players(self) -> List[Player]:
        """Get list of all players"""
        return list(self.players.values())
    
    def get_player_count(self) -> int:
        """Get number of players"""
        return len(self.players)
    
    def is_network_leader(self) -> bool:
        """Check if this node is the leader"""
        return self.is_leader
    
    def get_leader_info(self) -> tuple:
        """Get leader ID and IP"""
        return self.leader_id, self.leader_ip