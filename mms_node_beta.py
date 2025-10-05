"""
Mobile Mesh Sentinel 2.0 - Node Beta
Second client for testing P2P communication
"""

import socket
import requests
import json
import threading
import time
from datetime import datetime

class MeshNode:
    def __init__(self, node_id, server_url, listen_port=8002):
        self.node_id = node_id
        self.server_url = server_url
        self.listen_port = listen_port
        self.peers = {}
        self.running = False
        self.server_socket = None
        
    def start(self):
        """Start the mesh node"""
        print(f"\n{'='*60}")
        print(f"🚀 Mobile Mesh Sentinel 2.0 - Node Client")
        print(f"{'='*60}")
        print(f"Node ID: {self.node_id}")
        print(f"Signaling Server: {self.server_url}")
        print(f"Listening Port: {self.listen_port}")
        print(f"{'='*60}\n")
        
        # Register with signaling server
        if not self.register():
            print("❌ Failed to register with signaling server")
            return False
        
        self.running = True
        
        # Start listening for incoming connections
        listener_thread = threading.Thread(target=self.listen_for_connections, daemon=True)
        listener_thread.start()
        
        # Start heartbeat thread
        heartbeat_thread = threading.Thread(target=self.send_heartbeat, daemon=True)
        heartbeat_thread.start()
        
        # Start peer discovery thread
        discovery_thread = threading.Thread(target=self.discover_peers, daemon=True)
        discovery_thread.start()
        
        return True
    
    def register(self):
        """Register this node with the signaling server"""
        try:
            response = requests.post(
                f"{self.server_url}/register",
                json={
                    'node_id': self.node_id,
                    'port': self.listen_port
                },
                timeout=5
            )
            
            if response.status_code == 201:
                data = response.json()
                print(f"✅ Registered successfully!")
                print(f"   IP: {data['node_info']['ip_address']}")
                print(f"   Port: {data['node_info']['port']}\n")
                return True
            else:
                print(f"❌ Registration failed: {response.json()}")
                return False
                
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False
    
    def send_heartbeat(self):
        """Send periodic heartbeat to signaling server"""
        while self.running:
            try:
                response = requests.post(
                    f"{self.server_url}/heartbeat",
                    json={'node_id': self.node_id},
                    timeout=5
                )
                
                if response.status_code == 200:
                    print(f"💓 Heartbeat sent [{datetime.now().strftime('%H:%M:%S')}]")
                else:
                    print(f"⚠️  Heartbeat failed: {response.json()}")
                    
            except Exception as e:
                print(f"⚠️  Heartbeat error: {e}")
            
            time.sleep(15)  # Send heartbeat every 15 seconds
    
    def discover_peers(self):
        """Periodically discover peers from signaling server"""
        while self.running:
            try:
                response = requests.post(
                    f"{self.server_url}/discover",
                    json={'node_id': self.node_id},
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    new_peers = data['peers']
                    
                    if new_peers:
                        print(f"\n🔍 Discovered {len(new_peers)} peer(s):")
                        for peer in new_peers:
                            peer_id = peer['node_id']
                            if peer_id not in self.peers:
                                self.peers[peer_id] = peer
                                print(f"   ➕ {peer_id} @ {peer['ip_address']}:{peer['port']}")
                    else:
                        print(f"\n🔍 No peers discovered yet...")
                        
            except Exception as e:
                print(f"⚠️  Discovery error: {e}")
            
            time.sleep(20)  # Discover peers every 20 seconds
    
    def listen_for_connections(self):
        """Listen for incoming P2P connections"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.listen_port))
            self.server_socket.listen(5)
            
            print(f"👂 Listening for connections on port {self.listen_port}...\n")
            
            while self.running:
                try:
                    self.server_socket.settimeout(1.0)
                    client_socket, address = self.server_socket.accept()
                    print(f"\n📥 Incoming connection from {address}")
                    
                    # Handle connection in separate thread
                    handler = threading.Thread(
                        target=self.handle_peer_connection,
                        args=(client_socket, address),
                        daemon=True
                    )
                    handler.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"⚠️  Connection error: {e}")
                        
        except Exception as e:
            print(f"❌ Listen error: {e}")
    
    def handle_peer_connection(self, client_socket, address):
        """Handle incoming peer connection"""
        try:
            # Receive data
            data = client_socket.recv(4096).decode('utf-8')
            
            if data:
                message = json.loads(data)
                print(f"\n📨 Message from {message.get('source', 'Unknown')}:")
                print(f"   Type: {message.get('type', 'unknown')}")
                print(f"   Content: {message.get('payload', 'N/A')}")
                
                # Send acknowledgment
                response = {
                    'status': 'received',
                    'timestamp': datetime.now().isoformat()
                }
                client_socket.send(json.dumps(response).encode('utf-8'))
                
        except Exception as e:
            print(f"⚠️  Handler error: {e}")
        finally:
            client_socket.close()
    
    def send_message_to_peer(self, peer_id, message_type, payload):
        """Send a message to a specific peer"""
        if peer_id not in self.peers:
            print(f"❌ Peer {peer_id} not found")
            return False
        
        peer = self.peers[peer_id]
        
        try:
            # Create socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((peer['ip_address'], peer['port']))
            
            # Prepare message
            message = {
                'source': self.node_id,
                'destination': peer_id,
                'type': message_type,
                'payload': payload,
                'timestamp': datetime.now().isoformat()
            }
            
            # Send message
            sock.send(json.dumps(message).encode('utf-8'))
            
            # Wait for response
            response = sock.recv(4096).decode('utf-8')
            print(f"\n✅ Message sent to {peer_id}")
            print(f"   Response: {response}")
            
            sock.close()
            return True
            
        except Exception as e:
            print(f"❌ Send error: {e}")
            return False
    
    def list_peers(self):
        """List all discovered peers"""
        if not self.peers:
            print("\n📋 No peers discovered yet")
            return
        
        print(f"\n📋 Connected Peers ({len(self.peers)}):")
        print(f"{'='*60}")
        for peer_id, peer in self.peers.items():
            print(f"  • {peer_id}")
            print(f"    Address: {peer['ip_address']}:{peer['port']}")
            print(f"    Last seen: {peer.get('last_seen', 'N/A')}")
            print()
    
    def stop(self):
        """Stop the node"""
        print("\n🛑 Shutting down node...")
        self.running = False
        
        # Unregister from server
        try:
            requests.post(
                f"{self.server_url}/unregister",
                json={'node_id': self.node_id},
                timeout=5
            )
            print("✅ Unregistered from server")
        except:
            pass
        
        if self.server_socket:
            self.server_socket.close()
        
        print("👋 Goodbye!")


def main():
    """Main interactive loop"""
    # Configuration - DIFFERENT FROM NODE_ALPHA
    NODE_ID = "Node_Beta"
    SERVER_URL = "http://127.0.0.1:5000"
    LISTEN_PORT = 8002  # Different port!
    
    # Create and start node
    node = MeshNode(NODE_ID, SERVER_URL, LISTEN_PORT)
    
    if not node.start():
        return
    
    # Interactive menu
    print("\n" + "="*60)
    print("COMMANDS:")
    print("  list    - List all discovered peers")
    print("  send    - Send message to a peer")
    print("  quit    - Exit the application")
    print("="*60 + "\n")
    
    try:
        while True:
            command = input("\n> ").strip().lower()
            
            if command == 'quit':
                break
            elif command == 'list':
                node.list_peers()
            elif command == 'send':
                node.list_peers()
                peer_id = input("\nEnter peer ID: ").strip()
                message = input("Enter message: ").strip()
                node.send_message_to_peer(peer_id, 'text', message)
            else:
                print("Unknown command. Try: list, send, quit")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    finally:
        node.stop()


if __name__ == '__main__':
    main()