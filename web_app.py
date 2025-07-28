#!/usr/bin/env python3
"""
Web-based Hitec CAN Servo Programming Tool
Converts the desktop GUI to a Flask web application for Replit compatibility
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import threading
import time
from datetime import datetime

from can_interface import CANInterface
from servo_protocol import ServoProtocol
from config_manager import ConfigManager
import utils

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hitec_servo_tool_secret_key'

# Global application state
can_interface = CANInterface()
servo_protocol = ServoProtocol()
config_manager = ConfigManager()
config = config_manager.load_config()

# Application state variables
app_state = {
    'connected': False,
    'channel': '',
    'bitrate': 500000,
    'available_channels': [],
    'connection_status': 'Disconnected',
    'messages': [],
    'servo_id': 1,
    'register_address': '0x00',
    'register_value': '0x00',
    'register_data': {},
    'last_update': datetime.now().isoformat()
}

def update_available_channels():
    """Update list of available CAN channels"""
    try:
        channels = can_interface.get_available_channels()
        app_state['available_channels'] = channels
        return channels
    except Exception as e:
        app_state['available_channels'] = []
        return []

def setup_message_callback():
    """Setup callback for receiving CAN messages"""
    def message_callback(msg):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        message_data = {
            'timestamp': timestamp,
            'id': f"0x{msg.arbitration_id:03X}",
            'data': ' '.join([f"{b:02X}" for b in msg.data]),
            'length': len(msg.data)
        }
        
        # Keep only last 100 messages
        app_state['messages'].insert(0, message_data)
        if len(app_state['messages']) > 100:
            app_state['messages'] = app_state['messages'][:100]
        
        app_state['last_update'] = datetime.now().isoformat()
    
    can_interface.add_message_callback(message_callback)

@app.route('/')
def index():
    """Main application page"""
    update_available_channels()
    return render_template('index.html', state=app_state)

@app.route('/api/refresh_channels', methods=['POST'])
def refresh_channels():
    """Refresh available CAN channels"""
    channels = update_available_channels()
    return jsonify({
        'success': True,
        'channels': channels,
        'message': f'Found {len(channels)} CAN interfaces'
    })

@app.route('/api/connect', methods=['POST'])
def connect_can():
    """Connect to CAN interface"""
    try:
        data = request.json
        channel = data.get('channel')
        bitrate = int(data.get('bitrate', 500000))
        
        if not channel or channel == "Select CAN Interface...":
            return jsonify({
                'success': False,
                'message': 'Please select a CAN interface first'
            })
        
        can_interface.channel = channel
        can_interface.bitrate = bitrate
        
        if can_interface.connect():
            app_state['connected'] = True
            app_state['channel'] = channel
            app_state['bitrate'] = bitrate
            app_state['connection_status'] = f'Connected to {channel} @ {bitrate} bps'
            
            return jsonify({
                'success': True,
                'message': f'Connected to {channel} successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to connect to CAN interface'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Connection error: {str(e)}'
        })

@app.route('/api/disconnect', methods=['POST'])
def disconnect_can():
    """Disconnect from CAN interface"""
    try:
        can_interface.disconnect()
        app_state['connected'] = False
        app_state['connection_status'] = 'Disconnected'
        app_state['messages'] = []
        
        return jsonify({
            'success': True,
            'message': 'Disconnected successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Disconnect error: {str(e)}'
        })

@app.route('/api/read_register', methods=['POST'])
def read_register():
    """Read servo register"""
    try:
        data = request.json
        servo_id = int(data.get('servo_id', 1))
        register_addr = data.get('register_address', '0x00')
        
        if not app_state['connected']:
            return jsonify({
                'success': False,
                'message': 'Not connected to CAN interface'
            })
        
        # Convert register address from hex string to int
        addr = int(register_addr, 16) if register_addr.startswith('0x') else int(register_addr, 16)
        
        # Send read command
        arbitration_id, message_data = servo_protocol.create_read_message(servo_id, addr)
        if can_interface.send_message(arbitration_id, message_data):
            return jsonify({
                'success': True,
                'message': f'Read command sent to servo {servo_id}, register {register_addr}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send read command'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Read error: {str(e)}'
        })

@app.route('/api/write_register', methods=['POST'])
def write_register():
    """Write servo register"""
    try:
        data = request.json
        servo_id = int(data.get('servo_id', 1))
        register_addr = data.get('register_address', '0x00')
        register_value = data.get('register_value', '0x00')
        
        if not app_state['connected']:
            return jsonify({
                'success': False,
                'message': 'Not connected to CAN interface'
            })
        
        # Convert addresses from hex strings to int
        addr = int(register_addr, 16) if register_addr.startswith('0x') else int(register_addr, 16)
        value = int(register_value, 16) if register_value.startswith('0x') else int(register_value, 16)
        
        # Send write command
        arbitration_id, message_data = servo_protocol.create_write_message(servo_id, addr, value)
        if can_interface.send_message(arbitration_id, message_data):
            return jsonify({
                'success': True,
                'message': f'Write command sent to servo {servo_id}, register {register_addr} = {register_value}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send write command'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Write error: {str(e)}'
        })

@app.route('/api/send_custom_message', methods=['POST'])
def send_custom_message():
    """Send custom CAN message"""
    try:
        data = request.json
        can_id = data.get('can_id', '0x123')
        message_data = data.get('data', '00 00 00 00 00 00 00 00')
        
        if not app_state['connected']:
            return jsonify({
                'success': False,
                'message': 'Not connected to CAN interface'
            })
        
        # Parse CAN ID
        id_int = int(can_id, 16) if can_id.startswith('0x') else int(can_id, 16)
        
        # Parse data bytes
        data_bytes = []
        for byte_str in message_data.split():
            data_bytes.append(int(byte_str, 16))
        
        # Create and send custom message
        if can_interface.send_message(id_int, bytes(data_bytes)):
            return jsonify({
                'success': True,
                'message': f'Custom message sent: ID={can_id}, Data={message_data}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send custom message'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Send error: {str(e)}'
        })

@app.route('/api/get_messages')
def get_messages():
    """Get recent CAN messages"""
    return jsonify({
        'messages': app_state['messages'],
        'last_update': app_state['last_update']
    })

@app.route('/api/clear_messages', methods=['POST'])
def clear_messages():
    """Clear message history"""
    app_state['messages'] = []
    return jsonify({'success': True, 'message': 'Messages cleared'})

@app.route('/api/get_state')
def get_state():
    """Get current application state"""
    return jsonify(app_state)

if __name__ == '__main__':
    print("Starting Hitec CAN Servo Programming Tool (Web Version)")
    
    # Initialize message callback
    setup_message_callback()
    
    # Update available channels on startup
    update_available_channels()
    
    # Start Flask application
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)