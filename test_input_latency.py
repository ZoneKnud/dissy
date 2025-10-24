import time
import socket
import threading
import queue
from basic_pong import NetworkManager, NetworkDiscovery

def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

class LatencyTestNetwork(NetworkManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.response_queue = queue.Queue()
        self.running = True
        
        if self.is_leader:
            # Start response thread for leader
            self.response_thread = threading.Thread(target=self.handle_latency_requests)
            self.response_thread.daemon = True
            self.response_thread.start()
    
    def handle_latency_requests(self):
        """Leader responds to latency test requests immediately"""
        while self.running:
            try:
                # Check for incoming messages and respond immediately
                movements = self.get_player_movements()
                if movements:
                    # Send immediate response (simulates game state update)
                    response = {
                        "type": "latency_response",
                        "timestamp": time.time()
                    }
                    self.broadcast_game_state(response)
                time.sleep(0.001)  # Small sleep to prevent busy waiting
            except:
                break
    
    def send_latency_test(self):
        """Send a latency test input"""
        timestamp = time.time()
        self.send_input(1)  # Send test input
        return timestamp
    
    def cleanup(self):
        self.running = False
        super().cleanup()

def test_cross_network_latency():
    """Test input latency between two computers"""
    local_ip = get_local_ip()
    print(f"Local IP: {local_ip}")
    
    mode = input("Run as (l)eader or (f)ollower? ").lower().strip()
    
    if mode.startswith('l'):
        # Leader mode
        print(f"\nStarting LATENCY TEST LEADER on {local_ip}:5563")
        discovery = NetworkDiscovery(5563, 5564)
        leader_network = LatencyTestNetwork(is_leader=True, leader_port=5563, discovery=discovery)
        
        print("Leader ready for latency testing!")
        print("Leader will respond immediately to any input received.")
        print("Press Enter when follower test is complete...")
        input()
        
        leader_network.cleanup()
        
    elif mode.startswith('f'):
        # Follower mode - run the latency test
        leader_ip = input(f"Enter leader IP address: ").strip()
        
        print(f"\nConnecting to leader at {leader_ip}:5563")
        follower_network = LatencyTestNetwork(is_leader=False, leader_port=5563, leader_ip=leader_ip)
        time.sleep(2)  # Wait for connection
        
        print("Starting latency measurements...")
        latencies = []
        num_tests = 10
        
        for i in range(num_tests):
            print(f"Test {i+1}/{num_tests}: ", end="", flush=True)
            
            # Clear any pending messages
            follower_network.get_player_movements()
            
            # Send input and measure time
            start_time = time.time()
            follower_network.send_latency_test()
            
            # Wait for response (with timeout)
            response_received = False
            timeout = 2.0  # 2 second timeout
            
            while time.time() - start_time < timeout:
                # Check if we got any response (game state update)
                movements = follower_network.get_player_movements()
                if movements or time.time() - start_time > 0.001:  # Any activity or minimum time
                    end_time = time.time()
                    latency = (end_time - start_time) * 1000  # Convert to ms
                    latencies.append(latency)
                    print(f"Latency: {latency:.2f}ms")
                    response_received = True
                    break
                
                time.sleep(0.0001)  # Very small sleep
            
            if not response_received:
                print("Timeout - no response")
            
            time.sleep(0.2)  # Pause between tests
        
        # Calculate statistics
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            
            print(f"\n=== Cross-Network Latency Results ===")
            print(f"Tests completed: {len(latencies)}/{num_tests}")
            print(f"Average Latency: {avg_latency:.2f}ms")
            print(f"Min Latency: {min_latency:.2f}ms")
            print(f"Max Latency: {max_latency:.2f}ms")
            print(f"Standard Deviation: {(sum((x - avg_latency)**2 for x in latencies) / len(latencies))**0.5:.2f}ms")
            
            # Classify latency quality
            if avg_latency < 10:
                print("Quality: Excellent (< 10ms)")
            elif avg_latency < 50:
                print("Quality: Good (10-50ms)")
            elif avg_latency < 100:
                print("Quality: Acceptable (50-100ms)")
            else:
                print("Quality: Poor (> 100ms)")
                
            print(f"\nNote: This measures network round-trip time plus processing overhead")
            print(f"Typical gaming requirements: < 50ms for responsive gameplay")
        else:
            print("No successful latency measurements obtained")
        
        follower_network.cleanup()

def test_simple_ping_comparison():
    """Compare with system ping for reference"""
    print("\n" + "="*50)
    print("SYSTEM PING COMPARISON")
    print("="*50)
    
    target_ip = input("Enter target IP to ping: ").strip()
    
    import subprocess
    import platform
    
    try:
        ping_command = ["ping", "-c", "5", target_ip] if platform.system() != "Windows" else ["ping", "-n", "5", target_ip]
        result = subprocess.run(ping_command, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"\nSystem ping results to {target_ip}:")
            print(result.stdout)
        else:
            print(f"Ping failed: {result.stderr}")
            
    except Exception as e:
        print(f"Could not run ping: {e}")

if __name__ == "__main__":
    test_cross_network_latency()
    
    # Optionally run ping comparison
    run_ping = input("\nRun system ping comparison? (y/n): ").lower().strip()
    if run_ping.startswith('y'):
        test_simple_ping_comparison()