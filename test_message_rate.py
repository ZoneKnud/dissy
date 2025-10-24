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

def test_cross_network_throughput():
    """Test throughput between two computers"""
    local_ip = get_local_ip()
    print(f"Local IP: {local_ip}")
    
    mode = input("Run as (l)eader or (f)ollower? ").lower().strip()
    
    if mode.startswith('l'):
        # Leader mode
        print(f"\nStarting LEADER on {local_ip}:5561")
        discovery = NetworkDiscovery(5561, 5562)
        leader_network = NetworkManager(is_leader=True, leader_port=5561, discovery=discovery)
        
        print("Leader ready! Start follower test on other computer...")
        print("Press Enter when follower test is complete...")
        input()
        
        leader_network.cleanup()
        
    elif mode.startswith('f'):
        # Follower mode - run the throughput test
        leader_ip = input(f"Enter leader IP address: ").strip()
        
        print(f"\nConnecting to leader at {leader_ip}:5561")
        follower_network = NetworkManager(is_leader=False, leader_port=5561, leader_ip=leader_ip)
        time.sleep(2)
        
        # Run throughput test
        rates_to_test = [10, 30, 60, 120, 240]
        results = {}
        
        for target_rate in rates_to_test:
            print(f"\nTesting {target_rate} messages/second...")
            
            messages_sent = 0
            start_time = time.time()
            test_duration = 5
            interval = 1.0 / target_rate
            last_send_time = start_time
            
            while time.time() - start_time < test_duration:
                current_time = time.time()
                
                if current_time - last_send_time >= interval:
                    follower_network.send_input(1 if messages_sent % 2 == 0 else -1)
                    messages_sent += 1
                    last_send_time = current_time
            
            actual_duration = time.time() - start_time
            actual_rate = messages_sent / actual_duration
            efficiency = (actual_rate / target_rate) * 100
            
            results[target_rate] = {
                'actual_rate': actual_rate,
                'efficiency': efficiency,
                'messages_sent': messages_sent
            }
            
            print(f"  Target: {target_rate} msg/s")
            print(f"  Actual: {actual_rate:.1f} msg/s")
            print(f"  Efficiency: {efficiency:.1f}%")
        
        # Results
        print(f"\n=== Cross-Network Throughput Results ===")
        print(f"{'Target':<8} {'Actual':<8} {'Efficiency':<12} {'Messages':<10}")
        print("-" * 40)
        
        for target, data in results.items():
            print(f"{target:<8} {data['actual_rate']:<8.1f} {data['efficiency']:<12.1f}% {data['messages_sent']:<10}")
        
        follower_network.cleanup()

if __name__ == "__main__":
    test_cross_network_throughput()