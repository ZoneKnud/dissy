import zmq
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
    BASE_PORT = 15240
    PUB_PORT_OFFSET = 0    # 15240 - for broadcasting game state
    SUB_PORT_OFFSET = 0    # 15240 - for receiving game state
    REP_PORT_OFFSET = 1    # 15241 - for discovery/election responses
    REQ_PORT_OFFSET = 1    # 15241 - for discovery/election requests
    PUSH_PORT_OFFSET = 2   # 15242 - for sending inputs
    PULL_PORT_OFFSET = 2   # 15242 - for receiving inputs
    
    HEARTBEAT_INTERVAL = 1.0  # seconds
    HEARTBEAT_TIMEOUT = 3.0   # seconds
    
    def __init__(self, on_message_callback: Callable = None):
        self.player_id = str(uuid.uuid4())
        self.local_ip = self._get_local_ip()
        self.is_leader = False
        self.leader_id = None
        self.leader_ip = None
        self.players: Dict[str, Player] = {}
        self.running = False
        
        # ZeroMQ context and sockets
        self.context = zmq.Context()
        self.publisher = None      # PUB socket for broadcasting
        self.subscriber = None     # SUB socket for receiving broadcasts
        self.responder = None      # REP socket for responding to requests
        self.requester = None      # REQ socket for making requests
        self.pusher = None         # PUSH socket for sending inputs
        self.puller = None         # PULL socket for receiving inputs
        
        # Threads
        self.subscriber_thread = None
        self.responder_thread = None
        self.puller_thread = None
        self.heartbeat_thread = None
        
        # Callbacks
        self.on_message_callback = on_message_callback
        
        # Election state
        self.election_in_progress = False
        self.election_responses = set()
        
        # Connection tracking
        self.subscriber_connected = False
        self.pusher_connected = False
        
        print(f"NetworkManager initialized - ID: {self.player_id[:8]}, IP: {self.local_ip}")
        
    def _get_local_ip(self) -> str:
        """Get the local IP address"""
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
    
    def start(self):
        """Start the network manager"""
        print("Starting ZeroMQ network manager...")
        self.running = True
        self._setup_sockets()
        self._start_threads()
        
        # Start discovery process
        self._discover_leader()
    
    def stop(self):
        """Stop the network manager"""
        print("Stopping ZeroMQ network manager...")
        self.running = False
        
        # Send leave message
        if self.is_leader:
            self._send_leader_leaving()
        elif self.leader_ip:
            self._send_player_leave()
        
        # Close sockets
        self._cleanup_sockets()
        
        # Terminate context
        self.context.term()
    
    def _setup_sockets(self):
        """Setup ZeroMQ sockets"""
        # Publisher for broadcasting game state (leader only)
        self.publisher = self.context.socket(zmq.PUB)
        pub_address = f"tcp://*:{self.BASE_PORT + self.PUB_PORT_OFFSET}"
        self.publisher.bind(pub_address)
        print(f"Publisher socket bound to {pub_address}")
        
        # Subscriber for receiving broadcasts
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.setsockopt(zmq.SUBSCRIBE, b"")  # Subscribe to all messages
        
        # Responder for handling discovery/election requests
        self.responder = self.context.socket(zmq.REP)
        rep_address = f"tcp://*:{self.BASE_PORT + self.REP_PORT_OFFSET}"
        self.responder.bind(rep_address)
        print(f"Responder socket bound to {rep_address}")
        
        # Requester for making discovery/election requests
        self.requester = self.context.socket(zmq.REQ)
        
        # Puller for receiving inputs (leader only)
        self.puller = self.context.socket(zmq.PULL)
        pull_address = f"tcp://*:{self.BASE_PORT + self.PULL_PORT_OFFSET}"
        self.puller.bind(pull_address)
        print(f"Puller socket bound to {pull_address}")
        
        # Pusher for sending inputs
        self.pusher = self.context.socket(zmq.PUSH)
        
    def _cleanup_sockets(self):
        """Clean up ZeroMQ sockets"""
        sockets = [self.publisher, self.subscriber, self.responder, 
                  self.requester, self.pusher, self.puller]
        for socket in sockets:
            if socket:
                socket.close()
    
    def _start_threads(self):
        """Start listener threads"""
        self.subscriber_thread = threading.Thread(target=self._subscriber_listener, daemon=True)
        self.subscriber_thread.start()
        
        self.responder_thread = threading.Thread(target=self._responder_listener, daemon=True)
        self.responder_thread.start()
        
        self.puller_thread = threading.Thread(target=self._puller_listener, daemon=True)
        self.puller_thread.start()
        
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_monitor, daemon=True)
        self.heartbeat_thread.start()
    
    def _discover_leader(self):
        """Discover existing leader by trying to connect to known addresses"""
        print("Discovering existing leader...")
        
        # Try to find leader by scanning local network
        import socket
        local_network = ".".join(self.local_ip.split(".")[:-1])
        
        for i in range(1, 255):
            if not self.running:
                break
                
            target_ip = f"{local_network}.{i}"
            if target_ip == self.local_ip:
                continue
                
            try:
                # Try to connect to potential leader
                req_address = f"tcp://{target_ip}:{self.BASE_PORT + self.REQ_PORT_OFFSET}"
                test_socket = self.context.socket(zmq.REQ)
                test_socket.setsockopt(zmq.RCVTIMEO, 100)  # 100ms timeout
                test_socket.connect(req_address)
                
                # Send discovery request
                discovery_msg = {
                    "type": MessageType.DISCOVERY_REQUEST.value,
                    "data": {
                        "playerId": self.player_id,
                        "playerIp": self.local_ip
                    }
                }
                
                test_socket.send_string(json.dumps(discovery_msg))
                
                try:
                    response = test_socket.recv_string()
                    response_data = json.loads(response)
                    
                    if response_data.get("type") == MessageType.DISCOVERY_RESPONSE.value:
                        print(f"Found leader at {target_ip}")
                        self._handle_discovery_response(response_data["data"], target_ip)
                        test_socket.close()
                        return
                        
                except zmq.Again:
                    pass  # Timeout, try next IP
                    
                test_socket.close()
                
            except Exception:
                continue  # Connection failed, try next IP
        
        # No leader found, become leader
        if not self.leader_id:
            print("No leader found, becoming leader")
            self._become_leader()
    
    def _become_leader(self):
        """Become the leader of the network"""
        print(f"Becoming leader with ID: {self.player_id[:8]}")
        self.is_leader = True
        self.leader_id = self.player_id
        self.leader_ip = self.local_ip
        
        # Add self to players list
        self.players[self.player_id] = Player(
            id=self.player_id,
            ip=self.local_ip,
            last_heartbeat=time.time()
        )
        
        print(f"Leader established. Players: {len(self.players)}")
        
        # Notify game layer about leadership change
        if self.on_message_callback:
            leader_change_message = {
                "type": "LEADER_CHANGE",
                "data": {
                    "newLeaderId": self.player_id,
                    "playerCount": len(self.players)
                }
            }
            self.on_message_callback(leader_change_message, self.local_ip)
    
    def _subscriber_listener(self):
        """Listen for broadcasts from leader"""
        print("Subscriber listener started")
        while self.running:
            try:
                if self.leader_ip and not self.is_leader and not self.subscriber_connected:
                    # Connect to leader's publisher only once
                    sub_address = f"tcp://{self.leader_ip}:{self.BASE_PORT + self.SUB_PORT_OFFSET}"
                    self.subscriber.connect(sub_address)
                    self.subscriber_connected = True
                    print(f"Subscriber connected to {sub_address}")
                
                if self.subscriber_connected and not self.is_leader:
                    message_str = self.subscriber.recv_string(zmq.NOBLOCK)
                    message = json.loads(message_str)
                    self._handle_message(message, self.leader_ip)
                    
            except zmq.Again:
                time.sleep(0.01)  # No message available
            except Exception as e:
                if self.running:
                    print(f"Subscriber error: {e}")
                    time.sleep(0.1)
    
    def _responder_listener(self):
        """Listen for requests (discovery, election)"""
        print("Responder listener started")
        while self.running:
            try:
                request_str = self.responder.recv_string(zmq.NOBLOCK)
                request = json.loads(request_str)
                response = self._handle_request(request)
                self.responder.send_string(json.dumps(response))
                
            except zmq.Again:
                time.sleep(0.01)  # No request available
            except Exception as e:
                if self.running:
                    print(f"Responder error: {e}")
                    # Send error response
                    try:
                        error_response = {"type": "ERROR", "data": {"message": str(e)}}
                        self.responder.send_string(json.dumps(error_response))
                    except:
                        pass
    
    def _puller_listener(self):
        """Listen for input messages (leader only)"""
        print("Puller listener started")
        while self.running:
            try:
                if self.is_leader:
                    message_str = self.puller.recv_string(zmq.NOBLOCK)
                    message = json.loads(message_str)
                    self._handle_message(message, "input")
                    
            except zmq.Again:
                time.sleep(0.01)  # No message available
            except Exception as e:
                if self.running:
                    print(f"Puller error: {e}")
                    time.sleep(0.1)
    
    def _handle_request(self, request: dict) -> dict:
        """Handle incoming request and return response"""
        req_type = request.get("type")
        data = request.get("data", {})
        
        if req_type == MessageType.DISCOVERY_REQUEST.value:
            return self._handle_discovery_request(data)
        elif req_type == MessageType.ELECTION.value:
            return self._handle_election_request(data)
        else:
            return {"type": "ERROR", "data": {"message": "Unknown request type"}}
    
    def _handle_discovery_request(self, data: dict) -> dict:
        """Handle discovery request and return response"""
        if not self.is_leader:
            return {"type": "ERROR", "data": {"message": "Not a leader"}}
        
        player_id = data.get("playerId")
        player_ip = data.get("playerIp")
        
        print(f"Discovery request from {player_id[:8]} at {player_ip}")
        
        # Add new player
        self.players[player_id] = Player(
            id=player_id,
            ip=player_ip,
            last_heartbeat=time.time()
        )
        
        # Return response with player list
        response = {
            "type": MessageType.DISCOVERY_RESPONSE.value,
            "data": {
                "leaderId": self.leader_id,
                "leaderIp": self.leader_ip,
                "players": [{"id": p.id, "ip": p.ip} for p in self.players.values()]
            }
        }
        
        print(f"Discovery response sent. Total players: {len(self.players)}")
        
        # Broadcast player join to all players
        self._broadcast_player_join(player_id, player_ip)
        
        return response
    
    def _handle_discovery_response(self, data: dict, sender_ip: str):
        """Handle discovery response from leader"""
        self.leader_id = data.get("leaderId")
        self.leader_ip = data.get("leaderIp")
        
        # Update players list
        self.players.clear()
        players_data = data.get("players", [])
        for player_data in players_data:
            self.players[player_data["id"]] = Player(
                id=player_data["id"],
                ip=player_data["ip"],
                last_heartbeat=time.time()
            )
        
        print(f"Connected to leader: {self.leader_id[:8]} at {self.leader_ip}")
        print(f"Players in network: {len(self.players)}")
        
        # Connect pusher to leader's puller for input (but don't connect subscriber here)
        if self.leader_ip and not self.pusher_connected:
            push_address = f"tcp://{self.leader_ip}:{self.BASE_PORT + self.PUSH_PORT_OFFSET}"
            self.pusher.connect(push_address)
            self.pusher_connected = True
            print(f"Pusher connected to {push_address}")
    
    def _broadcast_player_join(self, player_id: str, player_ip: str):
        """Broadcast player join message"""
        message = {
            "type": MessageType.PLAYER_JOIN.value,
            "data": {
                "playerId": player_id,
                "playerIp": player_ip
            }
        }
        
        if self.is_leader:
            self.publisher.send_string(json.dumps(message))
    
    def _handle_message(self, message: dict, sender_ip: str):
        """Handle incoming message"""
        msg_type = message.get("type")
        data = message.get("data", {})
        
        # Debug output for non-frequent messages
        if msg_type not in [MessageType.HEARTBEAT.value, MessageType.GAME_STATE.value]:
            print(f"Received {msg_type}")
        
        if msg_type == MessageType.PLAYER_JOIN.value:
            self._handle_player_join(data, sender_ip)
        elif msg_type == MessageType.PLAYER_LEAVE.value:
            self._handle_player_leave(data, sender_ip)
        elif msg_type == MessageType.HEARTBEAT.value:
            self._handle_heartbeat(data, sender_ip)
        elif msg_type == MessageType.PADDLE_INPUT.value:
            self._handle_paddle_input(data, sender_ip)
        elif msg_type == MessageType.GAME_STATE.value:
            self._handle_game_state(data, sender_ip)
        elif msg_type == MessageType.NEW_LEADER.value:
            self._handle_new_leader(data, sender_ip)
        
        # Call user callback
        if self.on_message_callback:
            self.on_message_callback(message, sender_ip)
    
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
            print(f"Player joined: {player_id[:8]} from {player_ip}")
    
    def _handle_player_leave(self, data: dict, sender_ip: str):
        """Handle player leave notification"""
        player_id = data.get("playerId")
        if player_id in self.players:
            del self.players[player_id]
            print(f"Player left: {player_id[:8]}")
    
    def _handle_heartbeat(self, data: dict, sender_ip: str):
        """Handle heartbeat from leader"""
        if sender_ip == self.leader_ip:
            leader_id = data.get("leaderId")
            if leader_id in self.players:
                self.players[leader_id].last_heartbeat = time.time()
    
    def _handle_paddle_input(self, data: dict, sender_ip: str):
        """Handle paddle input"""
        pass  # Handled by game callback
    
    def _handle_game_state(self, data: dict, sender_ip: str):
        """Handle game state"""
        pass  # Handled by game callback
    
    def _handle_election_request(self, data: dict) -> dict:
        """Handle election request"""
        sender_id = data.get("senderId")
        
        if self.player_id > sender_id:
            # Start our own election
            threading.Thread(target=self._start_election, daemon=True).start()
            return {
                "type": MessageType.ELECTION_OKAY.value,
                "data": {"senderId": self.player_id}
            }
        else:
            return {"type": "ERROR", "data": {"message": "Lower ID"}}
    
    def _handle_new_leader(self, data: dict, sender_ip: str):
        """Handle new leader announcement"""
        old_leader_ip = self.leader_ip
        
        self.leader_id = data.get("newLeaderId")
        self.leader_ip = data.get("newLeaderIp")
        self.is_leader = False
        self.election_in_progress = False
        
        # Reconnect to new leader if it's different
        if old_leader_ip != self.leader_ip:
            # Disconnect from old leader
            if old_leader_ip and self.subscriber_connected:
                try:
                    self.subscriber.disconnect(f"tcp://{old_leader_ip}:{self.BASE_PORT + self.SUB_PORT_OFFSET}")
                    self.subscriber_connected = False
                except:
                    pass
            
            if old_leader_ip and self.pusher_connected:
                try:
                    self.pusher.disconnect(f"tcp://{old_leader_ip}:{self.BASE_PORT + self.PUSH_PORT_OFFSET}")
                    self.pusher_connected = False
                except:
                    pass
        
        print(f"New leader announced: {self.leader_id[:8]} at {self.leader_ip}")
    
    def _heartbeat_monitor(self):
        """Monitor heartbeats and send them if leader"""
        while self.running:
            time.sleep(self.HEARTBEAT_INTERVAL)
            
            if self.is_leader:
                self._send_heartbeat()
            elif self.leader_id:
                # Check if leader is alive
                leader = self.players.get(self.leader_id)
                if leader and time.time() - leader.last_heartbeat > self.HEARTBEAT_TIMEOUT:
                    print("Leader timeout detected, starting election")
                    if self.leader_id in self.players:
                        del self.players[self.leader_id]
                    self.leader_id = None
                    self.leader_ip = None
                    self._start_election()
    
    def _send_heartbeat(self):
        """Send heartbeat as leader"""
        message = {
            "type": MessageType.HEARTBEAT.value,
            "data": {
                "leaderId": self.player_id,
                "timestamp": time.time()
            }
        }
        
        if self.is_leader:
            self.publisher.send_string(json.dumps(message))
    
    def _start_election(self):
        """Start leader election"""
        if self.election_in_progress:
            return
        
        print("Starting leader election...")
        self.election_in_progress = True
        
        # Find players with higher IDs
        higher_id_players = [p for p in self.players.values() if p.id > self.player_id]
        
        if not higher_id_players:
            print("No higher ID players, becoming leader")
            self._become_leader()
            self._announce_new_leader()
            self.election_in_progress = False
            return
        
        # Send election messages to higher ID players
        responses = 0
        for player in higher_id_players:
            try:
                req_socket = self.context.socket(zmq.REQ)
                req_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
                req_address = f"tcp://{player.ip}:{self.BASE_PORT + self.REQ_PORT_OFFSET}"
                req_socket.connect(req_address)
                
                election_msg = {
                    "type": MessageType.ELECTION.value,
                    "data": {"senderId": self.player_id}
                }
                
                req_socket.send_string(json.dumps(election_msg))
                
                try:
                    response = req_socket.recv_string()
                    response_data = json.loads(response)
                    if response_data.get("type") == MessageType.ELECTION_OKAY.value:
                        responses += 1
                except zmq.Again:
                    pass  # Timeout
                
                req_socket.close()
                
            except Exception as e:
                print(f"Election request to {player.ip} failed: {e}")
        
        # If no responses, become leader
        if responses == 0:
            print("No election responses, becoming leader")
            self._become_leader()
            self._announce_new_leader()
        
        self.election_in_progress = False
    
    def _announce_new_leader(self):
        """Announce new leader"""
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
                    req_socket = self.context.socket(zmq.REQ)
                    req_socket.setsockopt(zmq.RCVTIMEO, 1000)
                    req_address = f"tcp://{player.ip}:{self.BASE_PORT + self.REQ_PORT_OFFSET}"
                    req_socket.connect(req_address)
                    req_socket.send_string(json.dumps(message))
                    req_socket.recv_string()  # Wait for acknowledgment
                    req_socket.close()
                except Exception as e:
                    print(f"Failed to announce leadership to {player.ip}: {e}")
    
    def _send_player_leave(self):
        """Send player leave message"""
        if not self.leader_ip:
            return
        
        message = {
            "type": MessageType.PLAYER_LEAVE.value,
            "data": {"playerId": self.player_id}
        }
        
        if self.is_leader:
            self.publisher.send_string(json.dumps(message))
    
    def _send_leader_leaving(self):
        """Send leader leaving message"""
        message = {
            "type": MessageType.PLAYER_LEAVE.value,
            "data": {"playerId": self.player_id}
        }
        
        if self.is_leader:
            self.publisher.send_string(json.dumps(message))
    
    def send_message(self, message_type: MessageType, data: dict, target_ip: str = None):
        """Send a message"""
        message = {
            "type": message_type.value,
            "data": data
        }
        
        try:
            if message_type == MessageType.PADDLE_INPUT:
                # Send input via PUSH socket (non-leaders only)
                if self.pusher and not self.is_leader and self.pusher_connected:
                    self.pusher.send_string(json.dumps(message))
            elif message_type == MessageType.GAME_STATE:
                # Broadcast game state via PUB socket (leaders only)
                if self.publisher and self.is_leader:
                    self.publisher.send_string(json.dumps(message))
            else:
                # Use publisher for other broadcasts (leaders only)
                if self.publisher and self.is_leader:
                    self.publisher.send_string(json.dumps(message))
                    
        except Exception as e:
            print(f"Failed to send message: {e}")
    
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