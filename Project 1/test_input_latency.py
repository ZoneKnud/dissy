import time
import socket
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

def test_simple_network_latency():
    """Simple network latency test using basic socket ping"""
    local_ip = get_local_ip()
    print(f"Local IP: {local_ip}")
    
    mode = input("Run as (s)erver or (c)lient? ").lower().strip()
    
    if mode.startswith('s'):
        # Simple server that echoes back messages
        print(f"\nStarting echo server on {local_ip}:5565")
        
        import zmq
        context = zmq.Context()
        socket = context.socket(zmq.REP)  # Reply socket
        socket.bind("tcp://*:5565")
        
        print("Echo server ready! Waiting for ping requests...")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                # Wait for request
                message = socket.recv()
                # Send back immediately
                socket.send(message)
        except KeyboardInterrupt:
            print("\nStopping server...")
        finally:
            socket.close()
            context.term()
            
    elif mode.startswith('c'):
        # Client that measures ping time
        server_ip = input(f"Enter server IP address: ").strip()
        
        print(f"\nConnecting to echo server at {server_ip}:5565")
        
        import zmq
        context = zmq.Context()
        socket = zmq.Socket(context, zmq.REQ)  # Request socket
        socket.connect(f"tcp://{server_ip}:5565")
        socket.setsockopt(zmq.RCVTIMEO, 2000)  # 2 second timeout
        
        print("Starting ping measurements...")
        latencies = []
        num_tests = 10
        
        for i in range(num_tests):
            print(f"Ping {i+1}/{num_tests}: ", end="", flush=True)
            
            try:
                # Send ping
                start_time = time.time()
                socket.send(b"ping")
                
                # Wait for echo
                response = socket.recv()
                end_time = time.time()
                
                latency = (end_time - start_time) * 1000  # Convert to ms
                latencies.append(latency)
                print(f"{latency:.2f}ms")
                
            except zmq.Again:
                print("Timeout")
            except Exception as e:
                print(f"Error: {e}")
            
            time.sleep(0.1)  # Small pause between pings
        
        # Results
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            
            print(f"\n=== Network Ping Results ===")
            print(f"Successful pings: {len(latencies)}/{num_tests}")
            print(f"Average Latency: {avg_latency:.2f}ms")
            print(f"Min Latency: {min_latency:.2f}ms")
            print(f"Max Latency: {max_latency:.2f}ms")
            
            if len(latencies) > 1:
                std_dev = (sum((x - avg_latency)**2 for x in latencies) / len(latencies))**0.5
                print(f"Standard Deviation: {std_dev:.2f}ms")
            
            print(f"\nThis measures pure ZeroMQ network round-trip time")
        else:
            print("No successful ping measurements")
        
        socket.close()
        context.term()

def test_system_ping():
    """Compare with system ping"""
    target_ip = input("\nEnter IP to ping for comparison: ").strip()
    
    import subprocess
    import platform
    
    try:
        ping_command = ["ping", "-c", "3", target_ip] if platform.system() != "Windows" else ["ping", "-n", "3", target_ip]
        result = subprocess.run(ping_command, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"\nSystem ping to {target_ip}:")
            # Extract just the relevant lines
            lines = result.stdout.split('\n')
            for line in lines:
                if 'time=' in line or 'min/avg/max' in line or 'round-trip' in line:
                    print(line)
        else:
            print(f"Ping failed")
            
    except Exception as e:
        print(f"Could not run ping: {e}")

if __name__ == "__main__":
    print("Simple Network Latency Test")
    print("="*30)
    test_simple_network_latency()
    
    run_comparison = input("\nRun system ping comparison? (y/n): ").lower().strip()
    if run_comparison.startswith('y'):
        test_system_ping()