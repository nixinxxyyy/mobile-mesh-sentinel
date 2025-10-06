"""
Mobile Mesh Sentinel 2.0 - Signaling Server
Phase 1: Node Registration & Discovery
"""

from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import threading
import time

app = Flask(__name__)

# In-memory storage for active nodes
active_nodes = {}
node_lock = threading.Lock()

# Configuration
HEARTBEAT_TIMEOUT = 30  # seconds
CLEANUP_INTERVAL = 10   # seconds

@app.route('/')
def index():
    """Root endpoint - Service information"""
    return jsonify({
        'service': 'Mobile Mesh Sentinel 2.0 - Signaling Server',
        'status': 'online',
        'version': '2.0',
        'endpoints': {
            'health': '/health',
            'register': '/register (POST)',
            'heartbeat': '/heartbeat (POST)',
            'discover': '/discover (POST)',
            'unregister': '/unregister (POST)',
            'nodes': '/nodes (GET)'
        },
        'active_nodes': len(active_nodes),
        'timestamp': datetime.now().isoformat()
    })
class Node:
    def __init__(self, node_id, ip_address, port, public_key=None):
        self.node_id = node_id
        self.ip_address = ip_address
        self.port = port
        self.public_key = public_key
        self.last_heartbeat = datetime.now()
        self.registered_at = datetime.now()
    
    def to_dict(self):
        return {
            'node_id': self.node_id,
            'ip_address': self.ip_address,
            'port': self.port,
            'public_key': self.public_key,
            'last_seen': self.last_heartbeat.isoformat(),
            'uptime_seconds': (datetime.now() - self.registered_at).total_seconds()
        }

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'active_nodes': len(active_nodes)
    })

@app.route('/register', methods=['POST'])
def register_node():
    """Register a new node in the mesh network"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['node_id', 'port']
        if not all(field in data for field in required_fields):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: node_id, port'
            }), 400
        
        node_id = data['node_id']
        port = data['port']
        public_key = data.get('public_key', None)
        
        # Get client IP
        ip_address = request.remote_addr
        
        with node_lock:
            # Create or update node
            node = Node(node_id, ip_address, port, public_key)
            active_nodes[node_id] = node
        
        return jsonify({
            'success': True,
            'message': f'Node {node_id} registered successfully',
            'node_info': node.to_dict()
        }), 201
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    """Update node's last seen timestamp"""
    try:
        data = request.get_json()
        node_id = data.get('node_id')
        
        if not node_id:
            return jsonify({
                'success': False,
                'error': 'node_id required'
            }), 400
        
        with node_lock:
            if node_id in active_nodes:
                active_nodes[node_id].last_heartbeat = datetime.now()
                return jsonify({
                    'success': True,
                    'message': 'Heartbeat received'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Node not registered'
                }), 404
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/discover', methods=['POST'])
def discover_peers():
    """Get list of active peers in the network"""
    try:
        data = request.get_json()
        requesting_node = data.get('node_id')
        
        if not requesting_node:
            return jsonify({
                'success': False,
                'error': 'node_id required'
            }), 400
        
        with node_lock:
            # Return all active nodes except the requesting one
            peers = [
                node.to_dict() 
                for node_id, node in active_nodes.items() 
                if node_id != requesting_node
            ]
        
        return jsonify({
            'success': True,
            'peer_count': len(peers),
            'peers': peers
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/unregister', methods=['POST'])
def unregister_node():
    """Manually unregister a node"""
    try:
        data = request.get_json()
        node_id = data.get('node_id')
        
        if not node_id:
            return jsonify({
                'success': False,
                'error': 'node_id required'
            }), 400
        
        with node_lock:
            if node_id in active_nodes:
                del active_nodes[node_id]
                return jsonify({
                    'success': True,
                    'message': f'Node {node_id} unregistered'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Node not found'
                }), 404
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/nodes', methods=['GET'])
def list_nodes():
    """List all active nodes (admin endpoint)"""
    with node_lock:
        nodes = [node.to_dict() for node in active_nodes.values()]
    
    return jsonify({
        'success': True,
        'total_nodes': len(nodes),
        'nodes': nodes
    })

def cleanup_stale_nodes():
    """Background task to remove inactive nodes"""
    while True:
        time.sleep(CLEANUP_INTERVAL)
        
        current_time = datetime.now()
        timeout_threshold = current_time - timedelta(seconds=HEARTBEAT_TIMEOUT)
        
        with node_lock:
            stale_nodes = [
                node_id for node_id, node in active_nodes.items()
                if node.last_heartbeat < timeout_threshold
            ]
            
            for node_id in stale_nodes:
                print(f"[CLEANUP] Removing stale node: {node_id}")
                del active_nodes[node_id]

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_stale_nodes, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    print("=" * 50)
    print("Mobile Mesh Sentinel 2.0 - Signaling Server")
    print("=" * 50)
    print(f"Heartbeat timeout: {HEARTBEAT_TIMEOUT}s")
    print(f"Cleanup interval: {CLEANUP_INTERVAL}s")
    print("Server starting on http://0.0.0.0:5000")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True)