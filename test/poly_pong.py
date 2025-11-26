#!/usr/bin/env python3
"""
PolyPong – a distributed Pong‑style game for 3–6 computers on the same LAN.

• Discovery: UDP broadcast (discovery_request / discovery_response)
• Control channel (reliable): TCP to the current leader (join/leave, roster updates)
• Realtime input + state: UDP (clients -> leader: move_paddle) (leader -> clients: game_state @ 30Hz)
• Leader election: Bully algorithm over UDP (heartbeat, election, okay, new_leader)
• Arena: regular polygon (triangle, square, pentagon, hexagon) chosen by active player count
• Rendering: pygame

Run examples (in different terminals/computers):
  # Start the first node as leader
  python poly_pong.py --name Alice --start

  # Join from other machines on the LAN
  python poly_pong.py --name Bob
  python poly_pong.py --name Carol

Dependencies: pygame (pip install pygame)

This is a compact but complete reference implementation; networking/election are simplified
for clarity and to keep it single‑file. It is designed for local networks and trusted peers.
"""
import argparse
import json
import math
import random
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Tuple, List, Optional

try:
    import pygame
except Exception:
    pygame = None

# ------------------------------- Configuration ---------------------------------
BROADCAST_PORT = 50000
UDP_PORT = 50010                 # for unicast/multicast game messages
TCP_PORT = 50020                 # leader's control channel (join/roster)
HEARTBEAT_INTERVAL = 1.0
HEARTBEAT_TIMEOUT = 3.5          # if no heartbeat for this long -> suspect failure
STATE_HZ = 30                    # leader broadcast rate
MAX_PLAYERS = 6
MIN_PLAYERS = 3
WINDOW = (1000, 700)
BALL_SPEED = 360.0               # pixels per second, leader authority
PADDLE_SPEED = 500.0             # pixels per second (client local smoothing)
PADDLE_LEN = 140                 # paddle length along wall
WALL_MARGIN = 60

# ------------------------------- Utilities -------------------------------------

def now() -> float:
    return time.monotonic()


def make_udp_socket(bind_port: Optional[int] = None, broadcast: bool = False) -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if broadcast:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    if bind_port is not None:
        s.bind(("", bind_port))
    return s


def ip_of_this_host() -> str:
    # Best‑effort technique to figure out our LAN IP without external traffic
    ip = "127.0.0.1"
    try:
        temp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        temp.connect(("8.8.8.8", 80))
        ip = temp.getsockname()[0]
        temp.close()
    except Exception:
        pass
    return ip

# ------------------------------- Message helpers -------------------------------

def msg(type_: str, player_id: Optional[int] = None, **data) -> bytes:
    payload = {"type": type_, "player_id": player_id, "data": data}
    return json.dumps(payload).encode("utf-8")


def parse(data: bytes) -> dict:
    return json.loads(data.decode("utf-8"))

# ------------------------------- Data models -----------------------------------

@dataclass
class Player:
    player_id: int
    name: str
    addr: Tuple[str, int]  # last seen UDP addr
    edge_idx: int = 0      # which wall edge they own
    paddle_t: float = 0.5  # normalized along edge [0..1]
    last_ok: float = field(default_factory=now)


@dataclass
class GameState:
    w: int = WINDOW[0]
    h: int = WINDOW[1]
    vertices: List[Tuple[float, float]] = field(default_factory=list)
    ball_pos: Tuple[float, float] = (WINDOW[0]/2, WINDOW[1]/2)
    ball_vel: Tuple[float, float] = (BALL_SPEED, BALL_SPEED*0.35)
    paddles: Dict[int, float] = field(default_factory=dict)  # player_id -> t along their edge
    edges: Dict[int, int] = field(default_factory=dict)      # player_id -> edge index
    scores: Dict[int, int] = field(default_factory=dict)
    leader_id: Optional[int] = None

    def to_wire(self) -> dict:
        return {
            "w": self.w, "h": self.h,
            "vertices": self.vertices,
            "ball_pos": self.ball_pos,
            "ball_vel": self.ball_vel,
            "paddles": self.paddles,
            "edges": self.edges,
            "scores": self.scores,
            "leader_id": self.leader_id,
        }

# ------------------------------- Leader Node -----------------------------------

class Leader:
    def __init__(self, me_id: int, name: str, my_ip: str):
        self.me_id = me_id
        self.name = name
        self.my_ip = my_ip
        self.udp = make_udp_socket(bind_port=UDP_PORT)
        self.broadcast_sock = make_udp_socket(broadcast=True)
        self.players: Dict[int, Player] = {}
        self.next_id = me_id + 1
        self.state = GameState()
        self.state.leader_id = me_id
        self.lock = threading.RLock()
        self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_server.bind(("", TCP_PORT))
        self.tcp_server.listen(8)
        self.running = True

        # The leader is also a player; reserve edge 0 for leader until roster built
        self.players[self.me_id] = Player(self.me_id, self.name, (self.my_ip, UDP_PORT), edge_idx=0)

    # ---------------- TCP accept / roster mgmt ----------------
    def tcp_accept_loop(self):
        while self.running:
            try:
                conn, addr = self.tcp_server.accept()
                threading.Thread(target=self.handle_join_conn, args=(conn, addr), daemon=True).start()
            except Exception:
                break

    def handle_join_conn(self, conn: socket.socket, addr):
        try:
            data = conn.recv(4096)
            hello = parse(data)
            if hello.get("type") != "join_hello":
                conn.close(); return
            name = hello.get("data", {}).get("name", f"P{self.next_id}")
            with self.lock:
                if len(self.players) >= MAX_PLAYERS:
                    conn.sendall(msg("join_reject", reason="room_full"))
                    conn.close(); return
                pid = self.next_id
                self.next_id += 1
                # Assign edge index in order of join
                edge_idx = len(self.players) % 6
                p = Player(pid, name, (addr[0], UDP_PORT), edge_idx=edge_idx)
                self.players[pid] = p
                self.state.paddles[pid] = 0.5
                self.state.edges[pid] = edge_idx
                self.state.scores.setdefault(pid, 0)
                # Recompute polygon based on player count
                self.recompute_polygon()
                # Respond with roster and my coordinates
                roster = [{"player_id": q.player_id, "name": q.name, "edge_idx": q.edge_idx} for q in self.players.values()]
                conn.sendall(msg("join_ok", leader_ip=self.my_ip, leader_id=self.me_id, tcp_port=TCP_PORT, udp_port=UDP_PORT, roster=roster, your_id=pid))
            conn.close()
            # Notify others (best‑effort over UDP)
            self.broadcast_sock.sendto(msg("player_join", player_id=self.me_id, joiner_id=pid, name=name, roster=roster), ("<broadcast>", BROADCAST_PORT))
        except Exception:
            try: conn.close()
            except Exception: pass

    def recompute_polygon(self):
        n = max(MIN_PLAYERS, min(MAX_PLAYERS, len(self.players)))
        cx, cy = self.state.w/2, self.state.h/2
        r = min(self.state.w, self.state.h)/2 - WALL_MARGIN
        verts = []
        for k in range(n):
            ang = 2*math.pi*k/n - math.pi/2
            verts.append((cx + r*math.cos(ang), cy + r*math.sin(ang)))
        self.state.vertices = verts
        # Reassign edges round‑robin
        for i, pid in enumerate(sorted(self.players.keys())):
            self.players[pid].edge_idx = i % n
            self.state.edges[pid] = self.players[pid].edge_idx

    # ---------------- Heartbeat + state broadcast --------------
    def heartbeat_loop(self):
        while self.running:
            hb = msg("heartbeat", player_id=self.me_id, leader_ip=self.my_ip)
            try:
                self.broadcast_sock.sendto(hb, ("<broadcast>", BROADCAST_PORT))
            except Exception:
                pass
            time.sleep(HEARTBEAT_INTERVAL)

    def physics_step(self, dt: float):
        # Move ball
        x, y = self.state.ball_pos
        vx, vy = self.state.ball_vel
        x += vx*dt
        y += vy*dt
        # Bounce off polygon walls, consider paddle intercepts
        verts = self.state.vertices
        if len(verts) < 3:
            self.state.ball_pos = (x, y)
            return
        # Iterate edges
        hit_any = False
        for i in range(len(verts)):
            a = verts[i]
            b = verts[(i+1) % len(verts)]
            # Edge normal via 2D line
            ax, ay = a; bx, by = b
            ex, ey = bx - ax, by - ay
            # Signed distance from ball to edge line (outward normal)
            nx, ny = -ey, ex
            nlen = math.hypot(nx, ny)
            nx, ny = nx/nlen, ny/nlen
            # Compute distance using point a as baseline (edge as infinite line)
            dist = (x-ax)*nx + (y-ay)*ny
            # Push back inside if outside (dist > 0 means outside assuming CCW verts)
            if dist > -6:  # small tolerance == collision
                # Project velocity onto normal; reflect if heading outward
                vdotn = vx*nx + vy*ny
                if vdotn > 0:
                    # Check if within edge segment bounds and whether paddle covers impact point
                    # Get closest point t along edge (0..1)
                    t = ((x-ax)*ex + (y-ay)*ey) / (ex*ex + ey*ey + 1e-9)
                    t = max(0.0, min(1.0, t))
                    # If this edge belongs to some player, get their paddle coverage interval
                    owner_pid = None
                    for pid, eidx in self.state.edges.items():
                        if eidx == i:
                            owner_pid = pid; break
                    paddle_hit = False
                    if owner_pid is not None:
                        pt = self.state.paddles.get(owner_pid, 0.5)
                        # Map paddle length to t‑interval length
                        plen = PADDLE_LEN / (math.hypot(ex, ey) + 1e-9)
                        if abs(t - pt) <= plen/2:
                            paddle_hit = True
                    # Reflect; add a little english if paddle hit
                    if paddle_hit:
                        # Add tangent component tweak based on where it hit the paddle
                        # Tangent unit
                        tx, ty = ex / (math.hypot(ex, ey)+1e-9), ey / (math.hypot(ex, ey)+1e-9)
                        off = (t - (pt))
                        vx, vy = (vx - 2*vdotn*nx + 160*off*tx, vy - 2*vdotn*ny + 160*off*ty)
                    else:
                        vx, vy = (vx - 2*vdotn*nx, vy - 2*vdotn*ny)
                    # Nudge inside
                    x -= (dist+6)*nx
                    y -= (dist+6)*ny
                    hit_any = True
        # Clamp speed a bit
        speed = math.hypot(vx, vy)
        target = BALL_SPEED
        if speed != 0:
            vx *= target/speed
            vy *= target/speed
        self.state.ball_pos = (x, y)
        self.state.ball_vel = (vx, vy)

    def game_loop(self):
        last = now()
        send_interval = 1.0/STATE_HZ
        accum = 0.0
        while self.running:
            t = now(); dt = t - last; last = t
            self.physics_step(dt)
            accum += dt
            if accum >= send_interval:
                with self.lock:
                    payload = msg("game_state", player_id=self.me_id, **self.state.to_wire())
                try:
                    self.broadcast_sock.sendto(payload, ("<broadcast>", BROADCAST_PORT))
                except Exception:
                    pass
                accum = 0.0
            # Process incoming UDP (paddle moves)
            self.udp.settimeout(0.0)
            try:
                while True:
                    data, addr = self.udp.recvfrom(8192)
                    pkt = parse(data)
                    tpe = pkt.get("type")
                    pid = pkt.get("player_id")
                    if tpe == "move_paddle" and pid in self.players:
                        tval = float(pkt["data"].get("t", 0.5))
                        self.state.paddles[pid] = max(0.0, min(1.0, tval))
                        self.players[pid].addr = addr
                    elif tpe == "leave" and pid in self.players:
                        with self.lock:
                            self.players.pop(pid, None)
                            self.state.paddles.pop(pid, None)
                            self.state.edges.pop(pid, None)
                            self.state.scores.pop(pid, None)
                            self.recompute_polygon()
                    # ignore others on leader
            except BlockingIOError:
                pass
            except socket.timeout:
                pass

    # ---------------- Shutdown ----------------
    def stop(self):
        self.running = False
        try: self.tcp_server.close()
        except Exception: pass
        try: self.udp.close()
        except Exception: pass
        try: self.broadcast_sock.close()
        except Exception: pass

# ------------------------------- Client Node -----------------------------------

class Client:
    def __init__(self, name: str):
        self.name = name
        self.me_id: Optional[int] = None
        self.leader_id: Optional[int] = None
        self.leader_ip: Optional[str] = None
        self.udp = make_udp_socket(bind_port=BROADCAST_PORT)
        self.unicast = make_udp_socket()  # ephemeral port for unicast
        self.tcp: Optional[socket.socket] = None
        self.running = True
        self.roster: Dict[int, Dict] = {}
        self.last_heartbeat = now()
        self.edge_idx = 0
        self.paddle_t = 0.5
        self.state = GameState()
        self.state.vertices = []
        self.state.paddles = {}
        self.state.edges = {}
        self.state.scores = {}
        self.key_dir = 0  # -1, 0, +1 along edge tangent
        self.election_in_progress = False

    # ---------------- Discovery / Join ----------------
    def discover_and_join(self):
        # Broadcast discovery_request and wait briefly for discovery_response
        bcast = make_udp_socket(broadcast=True)
        req = msg("discovery_request", data={"name": self.name})
        bcast.sendto(req, ("<broadcast>", BROADCAST_PORT))
        bcast.close()
        # Listen for a short window for response
        end = now() + 1.0
        got = None
        self.udp.settimeout(0.5)
        while now() < end:
            try:
                data, addr = self.udp.recvfrom(8192)
                pkt = parse(data)
                if pkt.get("type") == "discovery_response":
                    got = (pkt, addr)
                    break
            except socket.timeout:
                pass
        if not got:
            return False
        pkt, addr = got
        self.leader_ip = pkt["data"].get("leader_ip")
        tcp_port = pkt["data"].get("tcp_port", TCP_PORT)
        # Connect TCP and send join_hello
        self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp.settimeout(2.0)
        self.tcp.connect((self.leader_ip, tcp_port))
        self.tcp.sendall(msg("join_hello", data={"name": self.name}))
        data = self.tcp.recv(65536)
        resp = parse(data)
        if resp.get("type") != "join_ok":
            return False
        self.me_id = resp["data"].get("your_id")
        self.leader_id = resp["data"].get("leader_id")
        roster = resp["data"].get("roster", [])
        for r in roster:
            self.roster[r["player_id"]] = r
        # Find our edge
        for r in roster:
            if r["player_id"] == self.me_id:
                self.edge_idx = r["edge_idx"]
        return True

    # ---------------- UDP listener (game_state, heartbeat, discovery, election) --
    def udp_listener(self):
        self.udp.settimeout(0.5)
        while self.running:
            try:
                data, addr = self.udp.recvfrom(65536)
            except socket.timeout:
                # heartbeat timeout check
                if self.leader_ip and (now() - self.last_heartbeat) > HEARTBEAT_TIMEOUT:
                    print("[WARN] Leader heartbeat missed. Starting election…")
                    threading.Thread(target=self.start_election, daemon=True).start()
                continue
            try:
                pkt = parse(data)
            except Exception:
                continue
            tpe = pkt.get("type")
            if tpe == "heartbeat" and pkt.get("player_id") == self.leader_id:
                self.last_heartbeat = now()
            elif tpe == "game_state":
                d = pkt.get("data", {})
                self.state.ball_pos = tuple(d.get("ball_pos", self.state.ball_pos))
                self.state.ball_vel = tuple(d.get("ball_vel", self.state.ball_vel))
                self.state.vertices = [tuple(v) for v in d.get("vertices", self.state.vertices)]
                self.state.paddles = {int(k): float(v) for k, v in d.get("paddles", {}).items()}
                self.state.edges = {int(k): int(v) for k, v in d.get("edges", {}).items()}
                self.state.scores = {int(k): int(v) for k, v in d.get("scores", {}).items()}
                self.state.leader_id = d.get("leader_id", self.state.leader_id)
                # update our edge index if provided
                if self.me_id in self.state.edges:
                    self.edge_idx = self.state.edges[self.me_id]
            elif tpe == "discovery_request":
                # If we believe we are leader (rare on client): ignore here
                pass
            elif tpe == "discovery_response":
                # handled in discover_and_join
                pass
            elif tpe == "player_join":
                # Update roster best‑effort
                r = pkt.get("data", {}).get("roster", [])
                for x in r:
                    self.roster[x["player_id"]] = x
            # ----- Election messages -----
            elif tpe == "election":
                their_id = pkt.get("player_id")
                if self.me_id is not None and their_id is not None and their_id < self.me_id:
                    # We have a higher ID – reply OK
                    self.unicast.sendto(msg("okay", player_id=self.me_id), addr)
                    # And start our own election if not already
                    if not self.election_in_progress:
                        threading.Thread(target=self.start_election, daemon=True).start()
            elif tpe == "okay":
                # Notified that someone higher exists; mark
                self._election_ok_received = True
            elif tpe == "new_leader":
                nl = pkt.get("data", {})
                self.leader_id = nl.get("leader_id")
                self.leader_ip = nl.get("leader_ip")
                self.last_heartbeat = now()
                print(f"[INFO] New leader is {self.leader_id} @ {self.leader_ip}")
                # Reconnect TCP control channel
                try:
                    if self.tcp:
                        self.tcp.close()
                    self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.tcp.settimeout(2.0)
                    self.tcp.connect((self.leader_ip, TCP_PORT))
                    self.tcp.sendall(msg("join_hello", data={"name": self.name}))
                    resp = parse(self.tcp.recv(65536))
                    if resp.get("type") == "join_ok":
                        # accept rejoin (we keep same me_id logically; leader may reassign)
                        pass
                except Exception as e:
                    print("[ERR] TCP reconnect failed:", e)

    # ---------------- Bully election ----------------
    def start_election(self):
        if self.election_in_progress or self.me_id is None:
            return
        self.election_in_progress = True
        higher = [pid for pid in self.roster.keys() if pid > self.me_id]
        print(f"[ELECTION] Starting election; higher IDs: {higher}")
        self._election_ok_received = False
        # Send election to higher IDs
        for pid in higher:
            # We don't track per‑peer IPs; broadcast with pid in payload
            self.unicast.sendto(msg("election", player_id=self.me_id, target=pid), ("<broadcast>", BROADCAST_PORT))
        # Wait a moment for OKs
        time.sleep(1.0)
        if not higher or not self._election_ok_received:
            # We win – announce new leader
            self.leader_id = self.me_id
            self.leader_ip = ip_of_this_host()
            self.unicast.sendto(msg("new_leader", player_id=self.me_id, leader_id=self.me_id, leader_ip=self.leader_ip), ("<broadcast>", BROADCAST_PORT))
            print("[ELECTION] I am the new leader.")
        else:
            print("[ELECTION] Higher node exists; waiting for announcement…")
        self.election_in_progress = False

    # ---------------- Input sender ----------------
    def input_loop(self):
        # Send paddle moves as we update our local t
        while self.running:
            if self.me_id is not None and self.leader_ip:
                try:
                    self.unicast.sendto(msg("move_paddle", player_id=self.me_id, t=self.paddle_t), (self.leader_ip, UDP_PORT))
                except Exception:
                    pass
            time.sleep(1.0/60.0)

    # ---------------- Rendering ----------------
    def render_loop(self):
        if pygame is None:
            print("pygame not installed; running headless (no rendering)")
            while self.running:
                time.sleep(1)
            return
        pygame.init()
        screen = pygame.display.set_mode(WINDOW)
        clock = pygame.time.Clock()
        font = pygame.font.SysFont(None, 22)

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_q, pygame.K_ESCAPE):
                        self.running = False
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        self.key_dir = -1
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.key_dir = +1
                elif event.type == pygame.KEYUP:
                    if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                        self.key_dir = 0
            # Move paddle locally
            # Determine our edge vector
            verts = self.state.vertices
            if len(verts) >= 3 and self.me_id is not None and self.me_id in self.state.edges:
                eidx = self.state.edges[self.me_id]
                a = verts[eidx]
                b = verts[(eidx+1) % len(verts)]
                seg_len = math.hypot(b[0]-a[0], b[1]-a[1])
                if seg_len > 1e-6:
                    self.paddle_t = max(0.0, min(1.0, self.paddle_t + self.key_dir * (PADDLE_SPEED/seg_len) * (clock.get_time()/1000.0)))
            # Draw
            screen.fill((12, 12, 16))
            # Draw polygon
            if len(verts) >= 3:
                pygame.draw.polygon(screen, (90, 100, 120), verts, 3)
                # paddles
                for pid, eidx in self.state.edges.items():
                    a = verts[eidx]
                    b = verts[(eidx+1) % len(verts)]
                    t = self.state.paddles.get(pid, 0.5)
                    ax, ay = a; bx, by = b
                    px = ax + (bx-ax)*t
                    py = ay + (by-ay)*t
                    # tangent unit
                    seg_len = math.hypot(bx-ax, by-ay)
                    if seg_len < 1e-6:
                        continue
                    tx = (bx-ax)/seg_len; ty = (by-ay)/seg_len
                    # normal to draw paddle thickness
                    nx = -ty; ny = tx
                    half = PADDLE_LEN/2
                    p1 = (px - tx*half - nx*6, py - ty*half - ny*6)
                    p2 = (px + tx*half - nx*6, py + ty*half - ny*6)
                    p3 = (px + tx*half + nx*6, py + ty*half + ny*6)
                    p4 = (px - tx*half + nx*6, py - ty*half + ny*6)
                    color = (190, 220, 255) if pid == self.me_id else (180, 160, 120)
                    pygame.draw.polygon(screen, color, [p1,p2,p3,p4])
            # ball
            bx, by = self.state.ball_pos
            pygame.draw.circle(screen, (240, 240, 240), (int(bx), int(by)), 8)
            # HUD
            hud1 = f"You: {self.name} (id={self.me_id})  Leader: {self.leader_id}  Players: {len(self.state.edges)}"
            hud2 = f"Heartbeat age: {now()-self.last_heartbeat:.1f}s  Edge={self.edge_idx}  t={self.paddle_t:.2f}"
            screen.blit(font.render(hud1, True, (220,220,220)), (10, 10))
            screen.blit(font.render(hud2, True, (150,150,150)), (10, 34))
            pygame.display.flip()
            clock.tick(60)
        pygame.quit()

    # ---------------- Lifecycle ----------------
    def stop(self):
        self.running = False
        try:
            if self.tcp:
                self.tcp.close()
        except Exception:
            pass
        try:
            self.udp.close()
            self.unicast.close()
        except Exception:
            pass

# ------------------------------- Discovery Responder (Leader) ------------------

def discovery_responder(leader: Leader):
    sock = make_udp_socket(bind_port=BROADCAST_PORT)
    sock.settimeout(0.3)
    while leader.running:
        try:
            data, addr = sock.recvfrom(4096)
        except socket.timeout:
            continue
        try:
            pkt = parse(data)
        except Exception:
            continue
        if pkt.get("type") == "discovery_request":
            # reply unicast with leader info
            resp = msg("discovery_response", player_id=leader.me_id, leader_ip=leader.my_ip, tcp_port=TCP_PORT, udp_port=UDP_PORT,
                       roster=[{"player_id": p.player_id, "name": p.name, "edge_idx": p.edge_idx} for p in leader.players.values()])
            try:
                sock.sendto(resp, (addr[0], BROADCAST_PORT))
            except Exception:
                pass

# ------------------------------- Main ------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="PolyPong – distributed Pong with Bully election")
    parser.add_argument("--start", action="store_true", help="Start as leader (first node)")
    parser.add_argument("--name", type=str, default=None, help="Display name")
    args = parser.parse_args()

    my_ip = ip_of_this_host()
    name = args.name or (socket.gethostname()[:8])
    my_base_id = int.from_bytes(socket.inet_aton(my_ip), 'big') % 100000  # derive stable-ish ID

    if args.start:
        # Become leader immediately
        print(f"[LEADER] Starting leader on {my_ip}:{TCP_PORT}/{UDP_PORT}")
        leader = Leader(me_id=my_base_id, name=name, my_ip=my_ip)
        leader.recompute_polygon()
        threads = [
            threading.Thread(target=leader.tcp_accept_loop, daemon=True),
            threading.Thread(target=leader.heartbeat_loop, daemon=True),
            threading.Thread(target=leader.game_loop, daemon=True),
            threading.Thread(target=discovery_responder, args=(leader,), daemon=True),
        ]
        for th in threads: th.start()
        # Run a local client so the leader can also play
        client = Client(name=name)
        client.me_id = leader.me_id
        client.leader_id = leader.me_id
        client.leader_ip = leader.my_ip
        # Seed with leader‑provided state
        client.state = leader.state
        threading.Thread(target=client.udp_listener, daemon=True).start()
        threading.Thread(target=client.input_loop, daemon=True).start()
        try:
            client.render_loop()
        finally:
            leader.stop(); client.stop()
    else:
        # Regular client: discover and join
        client = Client(name=name)
        print("[CLIENT] Discovering leader…")
        ok = client.discover_and_join()
        if not ok:
            print("[CLIENT] No leader found on the LAN. Start one with --start")
            return
        print(f"[CLIENT] Joined as id={client.me_id}; leader id={client.leader_id} @ {client.leader_ip}")
        t1 = threading.Thread(target=client.udp_listener, daemon=True)
        t2 = threading.Thread(target=client.input_loop, daemon=True)
        t1.start(); t2.start()
        try:
            client.render_loop()
        finally:
            client.stop()

if __name__ == "__main__":
    main()