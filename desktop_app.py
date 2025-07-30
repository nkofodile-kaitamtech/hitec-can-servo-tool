#!/usr/bin/env python3
"""
Desktop GUI Hitec CAN Servo Programming Tool
Fixed version that works properly in all environments
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional

from can_interface import CANInterface
from servo_protocol import ServoProtocol
from config_manager import ConfigManager
import utils

class ServoControlGUI:
    def __init__(self):
        """Initialize the Servo Control GUI"""
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('servo_control.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.can_interface = CANInterface()
        self.servo_protocol = ServoProtocol()
        self.config_manager = ConfigManager()
        
        # Load configuration
        self.config = self.config_manager.load_config()
        
        # Create main window first
        self.root = tk.Tk()
        self.root.title("Hitec CAN Servo Programming Tool")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Initialize GUI variables after root window exists
        self.setup_variables()
        
        # Setup GUI
        self.setup_gui()
        self.setup_message_callback()
        self.setup_error_callback()
        
        # Apply saved configuration
        self.apply_config()
        
        # Initial channel refresh after GUI is ready
        self.root.after(100, self.refresh_channels)
        
    def setup_variables(self):
        """Initialize tkinter variables"""
        self.channel_var = tk.StringVar(self.root)
        self.bitrate_var = tk.StringVar(self.root, value="500000")
        self.connection_status_var = tk.StringVar(self.root, value="Disconnected")
        self.servo_id_var = tk.StringVar(self.root, value="1")
        self.register_addr_var = tk.StringVar(self.root, value="0x00")
        self.register_value_var = tk.StringVar(self.root, value="0x00")
        self.can_id_var = tk.StringVar(self.root, value="0x123")
        self.can_data_var = tk.StringVar(self.root, value="00 00 00 00 00 00 00 00")
        self.connected = False
        
        # Additional variables for enhanced functionality
        self.message_count = 0
        self.is_monitoring = False
        
    def setup_gui(self):
        """Setup the main GUI layout"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_connection_tab()
        self.create_servo_control_tab()
        self.create_message_monitor_tab()
        self.create_config_tab()
        
        # Create status bar
        self.create_status_bar()
        
    def create_connection_tab(self):
        """Create connection configuration tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Connection")
        
        # Main container with padding
        container = ttk.Frame(frame)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Connection controls
        controls_frame = ttk.LabelFrame(container, text="CAN Interface Settings", padding="10")
        controls_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Channel selection
        ttk.Label(controls_frame, text="CAN Interface:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.channel_combo = ttk.Combobox(controls_frame, textvariable=self.channel_var, width=20, state="readonly")
        self.channel_combo.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        self.channel_combo.set("Select CAN Interface...")
        
        ttk.Button(controls_frame, text="Refresh", command=self.refresh_channels).grid(row=0, column=2, padx=(0, 10))
        
        # Bitrate selection
        ttk.Label(controls_frame, text="Bitrate:").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(10, 0))
        bitrate_combo = ttk.Combobox(controls_frame, textvariable=self.bitrate_var, width=20, state="readonly")
        bitrate_combo['values'] = ("125000", "250000", "500000", "1000000")
        bitrate_combo.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(10, 0))
        
        # Connection buttons
        button_frame = ttk.Frame(controls_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=(20, 0), sticky="ew")
        
        self.connect_button = ttk.Button(button_frame, text="Connect", command=self.toggle_connection)
        self.connect_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.reset_button = ttk.Button(button_frame, text="Reset Bus", command=self.manual_reset_bus, state=tk.DISABLED)
        self.reset_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Auto-reset checkbox
        self.auto_reset_var = tk.BooleanVar(self.root, value=True)
        auto_reset_cb = ttk.Checkbutton(button_frame, text="Auto Reset", variable=self.auto_reset_var, command=self.toggle_auto_reset)
        auto_reset_cb.pack(side=tk.LEFT, padx=(10, 0))
        
        # Status display
        status_frame = ttk.Frame(controls_frame)
        status_frame.grid(row=3, column=0, columnspan=3, pady=(10, 0), sticky="ew")
        
        ttk.Label(status_frame, text="Status:").pack(side=tk.LEFT)
        status_label = ttk.Label(status_frame, textvariable=self.connection_status_var, foreground="red")
        status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Bus error status
        self.bus_error_var = tk.StringVar(self.root, value="No errors")
        ttk.Label(status_frame, text="Bus Errors:").pack(side=tk.LEFT, padx=(20, 5))
        self.error_label = ttk.Label(status_frame, textvariable=self.bus_error_var, foreground="green")
        self.error_label.pack(side=tk.LEFT)
        
        # Configure grid weights
        controls_frame.columnconfigure(1, weight=1)
        
        # Connection info
        info_frame = ttk.LabelFrame(container, text="Getting Started", padding="10")
        info_frame.pack(fill=tk.BOTH, expand=True)
        
        self.info_text = scrolledtext.ScrolledText(info_frame, height=15, wrap=tk.WORD)
        self.info_text.pack(fill=tk.BOTH, expand=True)
        
        # Add helpful information
        info_content = """Welcome to Hitec CAN Servo Programming Tool

Getting Started:
1. Click 'Refresh' to scan for available PCAN interfaces
2. Select your CAN interface from the dropdown
3. Choose appropriate bitrate (typically 500000 bps)
4. Click 'Connect' to establish connection
5. Use the 'Servo Control' tab to program your servos

Requirements:
• PCAN USB adapter connected to your computer
• PCAN drivers installed on your system
• CAN bus network with connected Hitec servos
• Proper CAN bus termination (120Ω resistors)

Common Register Addresses:
• 0x06 - CAN ID configuration
• 0x07 - Baud rate setting
• 0x0A - Minimum position limit
• 0x0B - Maximum position limit
• 0x0C - Current position command
• 0x20 - Operating mode

Troubleshooting:
• If no interfaces are found, check PCAN driver installation
• Ensure CAN hardware is properly connected
• Verify CAN bus has proper termination
• Check that servos are powered and connected to CAN bus
"""
        self.info_text.insert(1.0, info_content)
        self.info_text.config(state=tk.DISABLED)
        
    def create_servo_control_tab(self):
        """Create servo control and programming tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Servo Control")
        
        container = ttk.Frame(frame)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Left column - Settings and Controls
        left_frame = ttk.Frame(container)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Servo ID Settings
        servo_frame = ttk.LabelFrame(left_frame, text="Servo Programming", padding="10")
        servo_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(servo_frame, text="Target Servo ID:").grid(row=0, column=0, sticky="w", pady=2)
        self.target_servo_var = tk.StringVar(value="0")
        ttk.Entry(servo_frame, textvariable=self.target_servo_var, width=10).grid(row=0, column=1, sticky="w", padx=(10, 0), pady=2)
        
        # Extended ID checkbox
        self.extended_id_var = tk.BooleanVar()
        ttk.Checkbutton(servo_frame, text="Extended CAN ID (29-bit)", 
                       variable=self.extended_id_var).grid(row=1, column=0, columnspan=2, sticky="w", pady=2)
        
        # CAN ID Programming
        can_id_frame = ttk.LabelFrame(left_frame, text="CAN ID Programming", padding="10")
        can_id_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(can_id_frame, text="CAN ID LOW (dec):").grid(row=0, column=0, sticky="w", pady=2)
        self.new_can_id_low_var = tk.StringVar(value="32816")
        ttk.Entry(can_id_frame, textvariable=self.new_can_id_low_var, width=10).grid(row=0, column=1, sticky="w", padx=(10, 0), pady=2)
        ttk.Button(can_id_frame, text="Set CAN ID LOW", command=self.set_servo_can_id_low).grid(row=0, column=2, padx=(10, 0), pady=2)
        
        ttk.Label(can_id_frame, text="CAN ID HIGH (dec):").grid(row=1, column=0, sticky="w", pady=2)
        self.new_can_id_high_var = tk.StringVar(value="5240")
        ttk.Entry(can_id_frame, textvariable=self.new_can_id_high_var, width=10).grid(row=1, column=1, sticky="w", padx=(10, 0), pady=2)
        ttk.Button(can_id_frame, text="Set CAN ID HIGH", command=self.set_servo_can_id_high).grid(row=1, column=2, padx=(10, 0), pady=2)
        
        ttk.Label(can_id_frame, text="CAN Mode:").grid(row=2, column=0, sticky="w", pady=2)
        self.can_mode_var = tk.StringVar(value="1")
        can_mode_combo = ttk.Combobox(can_id_frame, textvariable=self.can_mode_var, width=15)
        can_mode_combo['values'] = ('0 - Standard', '1 - Extended')
        can_mode_combo.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=2)
        ttk.Button(can_id_frame, text="Set CAN Mode", command=self.set_servo_can_mode).grid(row=2, column=2, padx=(10, 0), pady=2)
        
        ttk.Label(can_id_frame, text="SERVO NODE ID (dec):").grid(row=3, column=0, sticky="w", pady=2)
        self.servoid_var = tk.StringVar(value="48")
        ttk.Entry(can_id_frame, textvariable=self.servoid_var, width=10).grid(row=3, column=1, sticky="w", padx=(10, 0), pady=2)
        ttk.Button(can_id_frame, text="Set SERVO NODE ID", command=self.set_servo_node_id).grid(row=3, column=2, padx=(10, 0), pady=2)
        
        # Position Control
        position_frame = ttk.LabelFrame(left_frame, text="Position Control", padding="10")
        position_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(position_frame, text="Position:").grid(row=0, column=0, sticky="w", pady=2)
        self.position_var = tk.StringVar(value="1500")
        ttk.Entry(position_frame, textvariable=self.position_var, width=10).grid(row=0, column=1, sticky="w", padx=(10, 0), pady=2)
        ttk.Button(position_frame, text="Set Position", command=self.set_servo_position).grid(row=0, column=2, padx=(10, 0), pady=2)
        
        # Right column - Data Reading and Results
        right_frame = ttk.Frame(container)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Data Reading Frame
        read_frame = ttk.LabelFrame(right_frame, text="Data Reading", padding="10")
        read_frame.pack(fill=tk.BOTH, expand=True)
        
        # Register reading
        ttk.Label(read_frame, text="Register Address:").grid(row=0, column=0, sticky="w", pady=2)
        self.read_address_var = tk.StringVar(value="0x32")
        ttk.Entry(read_frame, textvariable=self.read_address_var, width=10).grid(row=0, column=1, sticky="w", padx=(10, 0), pady=2)
        ttk.Button(read_frame, text="Read Register", command=self.read_servo_register).grid(row=0, column=2, padx=(10, 0), pady=2)
        
        # Common operations
        ttk.Button(read_frame, text="Read Servo ID", command=lambda: self.read_servo_register(0x32)).grid(row=1, column=0, columnspan=3, sticky="ew", pady=2)
        ttk.Button(read_frame, text="Read CAN Mode", command=lambda: self.read_servo_register(0x6A)).grid(row=2, column=0, columnspan=3, sticky="ew", pady=2)
        ttk.Button(read_frame, text="Read Servo Position", command=lambda: self.read_servo_register(0x0C)).grid(row=3, column=0, columnspan=3, sticky="ew", pady=2)
        ttk.Button(read_frame, text="Read CAN ID", command=self.read_can_id_registers).grid(row=4, column=0, columnspan=3, sticky="ew", pady=2)
        ttk.Button(read_frame, text="Save & Reset", command=self.save_and_reset_servo).grid(row=5, column=0, columnspan=3, sticky="ew", pady=10)
        
        # Results area
        ttk.Label(read_frame, text="Results:").grid(row=6, column=0, sticky="w", pady=(10, 2))
        self.results_text = scrolledtext.ScrolledText(read_frame, height=15, width=40)
        self.results_text.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=2)
        
        read_frame.columnconfigure(0, weight=1)
        read_frame.rowconfigure(7, weight=1)
        
        # Register reference
        ref_frame = ttk.LabelFrame(container, text="Common Registers", padding="10")
        ref_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview for register reference
        columns = ("Address", "Name", "Description", "Range")
        self.reg_tree = ttk.Treeview(ref_frame, columns=columns, show="headings", height=12)
        
        for col in columns:
            self.reg_tree.heading(col, text=col)
            self.reg_tree.column(col, width=150)
        
        # Add register data
        registers = [
            ("0x32", "CAN_NODE_ID", "CAN NODE ID", "1-127"),
            ("0x07", "BAUD_RATE", "Communication Speed", "0-7"),
            ("0x0A", "MIN_POSITION", "Minimum Position", "0-1023"),
            ("0x0B", "MAX_POSITION", "Maximum Position", "0-1023"),
            ("0x0C", "POSITION", "Current Position", "0-1023"),
            ("0x20", "OPERATING_MODE", "Control Mode", "0-3"),
            ("0x21", "SPEED", "Movement Speed", "0-255"),
            ("0x22", "TORQUE_LIMIT", "Maximum Torque", "0-255")
        ]
        
        for reg in registers:
            self.reg_tree.insert("", tk.END, values=reg)
        
        self.reg_tree.pack(fill=tk.BOTH, expand=True)
        
        # Add scrollbar to treeview
        reg_scrollbar = ttk.Scrollbar(ref_frame, orient=tk.VERTICAL, command=self.reg_tree.yview)
        self.reg_tree.configure(yscrollcommand=reg_scrollbar.set)
        reg_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.reg_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
    def create_message_monitor_tab(self):
        """Create message monitoring tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Message Monitor")
        
        container = ttk.Frame(frame)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Controls frame
        controls_frame = ttk.Frame(container)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.monitor_btn = ttk.Button(controls_frame, text="Start Monitoring", command=self.toggle_monitoring)
        self.monitor_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(controls_frame, text="Clear Messages", command=self.clear_messages).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(controls_frame, text="Save Log", command=self.save_message_log).pack(side=tk.LEFT, padx=(0, 10))
        
        # Message count
        self.message_count_var = tk.StringVar(value="Messages: 0")
        ttk.Label(controls_frame, textvariable=self.message_count_var).pack(side=tk.RIGHT)
        
        # Custom message frame
        custom_frame = ttk.LabelFrame(container, text="Send Custom Message", padding="10")
        custom_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(custom_frame, text="Message ID:").grid(row=0, column=0, sticky="w", pady=2)
        self.custom_id_var = tk.StringVar(value="0x000")
        ttk.Entry(custom_frame, textvariable=self.custom_id_var, width=10).grid(row=0, column=1, sticky="w", padx=(10, 0), pady=2)
        
        self.custom_extended_var = tk.BooleanVar()
        ttk.Checkbutton(custom_frame, text="Extended ID", variable=self.custom_extended_var).grid(row=0, column=2, padx=(10, 0), pady=2)
        
        ttk.Label(custom_frame, text="Data (hex):").grid(row=1, column=0, sticky="w", pady=2)
        self.custom_data_var = tk.StringVar(value="72 00 32")
        ttk.Entry(custom_frame, textvariable=self.custom_data_var, width=30).grid(row=1, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=2)
        
        ttk.Button(custom_frame, text="Send Message", command=self.send_custom_message).grid(row=2, column=0, columnspan=3, pady=10)
        
        custom_frame.columnconfigure(1, weight=1)
        
        # Message display
        self.message_tree = ttk.Treeview(container, columns=('Time', 'ID', 'Data', 'Description'), show='headings', height=20)
        self.message_tree.pack(fill=tk.BOTH, expand=True)
        
        # Configure columns
        self.message_tree.heading('Time', text='Time')
        self.message_tree.heading('ID', text='CAN ID')
        self.message_tree.heading('Data', text='Data')
        self.message_tree.heading('Description', text='Description')
        
        self.message_tree.column('Time', width=100)
        self.message_tree.column('ID', width=80)
        self.message_tree.column('Data', width=200)
        self.message_tree.column('Description', width=300)
        
        # Scrollbar for tree
        tree_scroll = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.message_tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.message_tree.configure(yscrollcommand=tree_scroll.set)
        
        # Auto scroll variable
        self.auto_scroll_var = tk.BooleanVar(value=True)
        
    def create_config_tab(self):
        """Create configuration tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Configuration")
        
        container = ttk.Frame(frame)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Configuration file management
        file_frame = ttk.LabelFrame(container, text="Configuration Files", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(file_frame, text="Save Configuration", command=self.save_configuration).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(file_frame, text="Load Configuration", command=self.load_configuration).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(file_frame, text="Reset to Defaults", command=self.reset_configuration).pack(side=tk.LEFT, padx=(0, 10))
        
        # Current configuration display
        config_frame = ttk.LabelFrame(container, text="Current Configuration", padding="10")
        config_frame.pack(fill=tk.BOTH, expand=True)
        
        self.config_text = scrolledtext.ScrolledText(config_frame, height=20, width=80)
        self.config_text.pack(fill=tk.BOTH, expand=True)
        
        # Update configuration display
        self.update_config_display()
        
    def create_status_bar(self):
        """Create status bar at bottom of window"""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
        
        self.status_label = ttk.Label(self.status_bar, text="Ready")
        self.status_label.pack(side=tk.LEFT)
        
    def setup_message_callback(self):
        """Setup callback for receiving CAN messages"""
        self.can_interface.add_message_callback(self.on_can_message_received)
    
    def setup_error_callback(self):
        """Setup callback for CAN bus errors"""
        def error_callback(error_message):
            # Schedule GUI update in main thread
            self.root.after(0, lambda: self.handle_bus_error(error_message))
        
        self.can_interface.add_error_callback(error_callback)
        
    def add_message_to_display(self, timestamp, msg_id, data, length):
        """Add message to display (called from main thread)"""
        try:
            self.message_tree.insert("", 0, values=(timestamp, msg_id, data, length))
            
            # Limit number of displayed messages
            children = self.message_tree.get_children()
            if len(children) > 1000:
                self.message_tree.delete(children[-1])
            
            # Auto scroll to top if enabled
            if self.auto_scroll_var.get():
                self.message_tree.selection_set(children[0])
                self.message_tree.see(children[0])
                
        except Exception as e:
            self.logger.error(f"Error adding message to display: {e}")
    
    def refresh_channels(self):
        """Refresh available CAN channels"""
        try:
            self.status_label.config(text="Scanning for CAN interfaces...")
            self.root.update()
            
            channels = self.can_interface.get_available_channels()
            
            if channels:
                self.channel_combo['values'] = channels
                self.status_label.config(text=f"Found {len(channels)} CAN interface(s)")
                self.logger.info(f"Found {len(channels)} available CAN channels")
            else:
                self.channel_combo['values'] = ["No CAN interfaces found"]
                self.status_label.config(text="No CAN interfaces found")
                self.logger.warning("No CAN interfaces found")
                
        except Exception as e:
            self.logger.error(f"Error refreshing channels: {e}")
            self.status_label.config(text="Error scanning interfaces")
            messagebox.showerror("Error", f"Failed to scan for CAN interfaces: {e}")
    
    def toggle_connection(self):
        """Toggle CAN connection"""
        if self.connected:
            self.disconnect_can()
        else:
            self.connect_can()
    
    def connect_can(self):
        """Connect to CAN interface"""
        try:
            channel = self.channel_var.get()
            
            # Validate channel selection
            if not channel or channel == "Select CAN Interface..." or channel == "No CAN interfaces found":
                messagebox.showerror("No Interface Selected", 
                                   "Please select a CAN interface from the dropdown first.\n\n" +
                                   "Click 'Refresh' to scan for available interfaces.")
                return
            
            bitrate = int(self.bitrate_var.get())
            
            self.can_interface.channel = channel
            self.can_interface.bitrate = bitrate
            
            self.status_label.config(text="Connecting...")
            self.root.update()
            
            if self.can_interface.connect():
                self.connected = True
                self.connect_button.config(text="Disconnect")
                self.reset_button.config(state=tk.NORMAL)
                self.connection_status_var.set(f"Connected to {channel}")
                self.status_label.config(text=f"Connected to {channel} @ {bitrate} bps")
                self.bus_error_var.set("No errors")
                self.error_label.config(foreground="green")
                
                # Update info text
                self.info_text.config(state=tk.NORMAL)
                self.info_text.delete(1.0, tk.END)
                self.info_text.insert(1.0, f"Connected to {channel} @ {bitrate} bps\n\n" +
                                     "Connection established successfully!\n" +
                                     "You can now use the Servo Control tab to communicate with servos.\n\n" +
                                     "Monitor the Message Monitor tab to see CAN traffic.\n")
                self.info_text.config(state=tk.DISABLED)
                
                self.logger.info(f"Connected to {channel} successfully")
                
            else:
                messagebox.showerror("Connection Failed", 
                                   f"Failed to connect to {channel}.\n\n" +
                                   "Please check:\n" +
                                   "• PCAN hardware is connected\n" +
                                   "• PCAN drivers are installed\n" +
                                   "• Interface is not used by another application")
                self.status_label.config(text="Connection failed")
                
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            messagebox.showerror("Connection Error", f"Error connecting to CAN interface:\n{e}")
            self.status_label.config(text="Connection error")
    
    def disconnect_can(self):
        """Disconnect from CAN interface"""
        try:
            self.can_interface.disconnect()
            self.connected = False
            self.connect_button.config(text="Connect")
            self.reset_button.config(state=tk.DISABLED)
            self.connection_status_var.set("Disconnected")
            self.status_label.config(text="Disconnected")
            self.bus_error_var.set("Disconnected")
            self.error_label.config(foreground="gray")
            
            # Clear messages
            self.clear_messages()
            
            # Update info text
            self.info_text.config(state=tk.NORMAL)
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(1.0, "Disconnected from CAN interface.\n\n" +
                                 "Select an interface and click Connect to start communication.")
            self.info_text.config(state=tk.DISABLED)
            
            self.logger.info("Disconnected from CAN interface")
            
        except Exception as e:
            self.logger.error(f"Disconnect error: {e}")
            messagebox.showerror("Disconnect Error", f"Error disconnecting:\n{e}")
    
    def read_register(self):
        """Read servo register"""
        if not self.connected:
            messagebox.showerror("Not Connected", "Please connect to CAN interface first")
            return
            
        try:
            servo_id = int(self.servo_id_var.get())
            register_addr = self.register_addr_var.get()
            addr = int(register_addr, 16) if register_addr.startswith('0x') else int(register_addr, 16)
            
            is_extended = self.extended_id_var.get()
            arbitration_id, message_data = self.servo_protocol.create_read_message(servo_id, addr, is_extended)
            
            if self.can_interface.send_message(arbitration_id, message_data, is_extended):
                self.status_label.config(text=f"Read command sent to servo {servo_id}, register {register_addr}")
                self.logger.info(f"Read command sent: Servo {servo_id}, Register {register_addr}")
            else:
                messagebox.showerror("Send Failed", "Failed to send read command")
                
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Invalid servo ID or register address:\n{e}")
        except Exception as e:
            self.logger.error(f"Read register error: {e}")
            messagebox.showerror("Read Error", f"Error reading register:\n{e}")
    
    def write_register(self):
        """Write servo register"""
        if not self.connected:
            messagebox.showerror("Not Connected", "Please connect to CAN interface first")
            return
            
        try:
            servo_id = int(self.servo_id_var.get())
            register_addr = self.register_addr_var.get()
            register_value = self.register_value_var.get()
            
            addr = int(register_addr, 16) if register_addr.startswith('0x') else int(register_addr, 16)
            value = int(register_value, 16) if register_value.startswith('0x') else int(register_value, 16)
            
            is_extended = self.extended_id_var.get()
            arbitration_id, message_data = self.servo_protocol.create_write_message(servo_id, addr, value, is_extended)
            
            if self.can_interface.send_message(arbitration_id, message_data, is_extended):
                self.status_label.config(text=f"Write command sent to servo {servo_id}, register {register_addr} = {register_value}")
                self.logger.info(f"Write command sent: Servo {servo_id}, Register {register_addr} = {register_value}")
            else:
                messagebox.showerror("Send Failed", "Failed to send write command")
                
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Invalid input values:\n{e}")
        except Exception as e:
            self.logger.error(f"Write register error: {e}")
            messagebox.showerror("Write Error", f"Error writing register:\n{e}")
    
    def send_custom_message(self):
        """Send custom CAN message"""
        if not self.connected:
            messagebox.showerror("Not Connected", "Please connect to CAN interface first")
            return
            
        try:
            can_id = self.can_id_var.get()
            can_data = self.can_data_var.get()
            
            id_int = int(can_id, 16) if can_id.startswith('0x') else int(can_id, 16)
            
            # Parse data bytes
            data_bytes = []
            for byte_str in can_data.split():
                data_bytes.append(int(byte_str, 16))
            
            # Use extended ID checkbox from the form
            is_extended = self.extended_id_var.get()
            if self.can_interface.send_message(id_int, bytes(data_bytes), is_extended):
                self.status_label.config(text=f"Custom message sent: ID={can_id}, Data={can_data}")
                self.logger.info(f"Custom message sent: ID={can_id}, Data={can_data}")
            else:
                messagebox.showerror("Send Failed", "Failed to send custom message")
                
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Invalid CAN ID or data format:\n{e}")
        except Exception as e:
            self.logger.error(f"Send custom message error: {e}")
            messagebox.showerror("Send Error", f"Error sending custom message:\n{e}")
    
    def clear_messages(self):
        """Clear message display"""
        try:
            for item in self.message_tree.get_children():
                self.message_tree.delete(item)
            
            # Reset message count
            self.message_count = 0
            self.message_count_var.set("Messages: 0")
            
            self.status_label.config(text="Messages cleared")
        except Exception as e:
            self.logger.error(f"Error clearing messages: {e}")
    
    def handle_bus_error(self, error_message):
        """Handle bus error notification from CAN interface"""
        try:
            self.bus_error_var.set(error_message)
            
            # Change error label color based on error type
            if "auto-reset completed" in error_message.lower():
                self.error_label.config(foreground="blue")
            elif "error" in error_message.lower():
                self.error_label.config(foreground="red")
            else:
                self.error_label.config(foreground="orange")
            
            # Show popup for serious errors
            if "too many" in error_message.lower() or "heavy" in error_message.lower():
                messagebox.showwarning("CAN Bus Warning", 
                                     f"CAN Bus Error Detected:\n{error_message}\n\n" +
                                     "The bus may be experiencing heavy traffic or errors.\n" +
                                     "Auto-reset will attempt to recover the connection.")
            
            # Update status bar
            self.status_label.config(text=error_message[:50] + "..." if len(error_message) > 50 else error_message)
            
        except Exception as e:
            self.logger.error(f"Error handling bus error notification: {e}")
    
    def manual_reset_bus(self):
        """Manually reset the CAN bus"""
        try:
            if not self.connected:
                messagebox.showinfo("Not Connected", "CAN interface is not connected")
                return
            
            result = messagebox.askyesno("Reset CAN Bus", 
                                       "Are you sure you want to reset the CAN bus?\n\n" +
                                       "This will disconnect and reconnect the interface,\n" +
                                       "clearing all queued messages.")
            
            if result:
                self.status_label.config(text="Resetting CAN bus...")
                self.root.update()
                
                self.can_interface.manual_reset_bus()
                self.clear_messages()
                
                # Update status
                bus_status = self.can_interface.get_bus_status()
                if bus_status['connected']:
                    self.bus_error_var.set("Manual reset completed")
                    self.error_label.config(foreground="blue")
                    self.status_label.config(text="Bus reset successful")
                else:
                    self.bus_error_var.set("Reset failed - disconnected")
                    self.error_label.config(foreground="red")
                    self.status_label.config(text="Bus reset failed")
                
        except Exception as e:
            self.logger.error(f"Error during manual bus reset: {e}")
            messagebox.showerror("Reset Error", f"Failed to reset CAN bus:\n{e}")
    
    def toggle_auto_reset(self):
        """Toggle automatic bus reset feature"""
        try:
            enabled = self.auto_reset_var.get()
            self.can_interface.enable_auto_reset(enabled)
            
            if enabled:
                self.status_label.config(text="Auto-reset enabled")
            else:
                self.status_label.config(text="Auto-reset disabled")
                
        except Exception as e:
            self.logger.error(f"Error toggling auto-reset: {e}")
    
    # Servo Control Methods
    def set_servo_can_id_low(self):
        """Set servo CAN ID LOW register"""
        try:
            servo_id = int(self.target_servo_var.get())
            new_id = int(self.new_can_id_low_var.get())
            is_extended = self.extended_id_var.get()
            
            # Send CAN message to set CAN ID LOW (register 0x06)
            arbitration_id, data = self.servo_protocol.create_write_message(servo_id, 0x3E, new_id, is_extended)
            if self.can_interface.send_message(arbitration_id, data, is_extended):
                self.results_text.insert(tk.END, f"Set CAN ID LOW to {new_id} for servo {servo_id}\n")
                self.results_text.see(tk.END)
                self.status_label.config(text=f"CAN ID LOW set to {new_id}")
            else:
                self.results_text.insert(tk.END, f"Failed to set CAN ID LOW\n")
                self.results_text.see(tk.END)
                
        except Exception as e:
            self.logger.error(f"Error setting CAN ID LOW: {e}")
            messagebox.showerror("Error", f"Failed to set CAN ID LOW: {e}")
    
    def set_servo_can_id_high(self):
        """Set servo CAN ID HIGH register"""
        try:
            servo_id = int(self.target_servo_var.get())
            new_id = int(self.new_can_id_high_var.get())
            is_extended = self.extended_id_var.get()
            
            # Send CAN message to set CAN ID HIGH (register 0x07)
            arbitration_id, data = self.servo_protocol.create_write_message(servo_id, 0x3C, new_id, is_extended)
            if self.can_interface.send_message(arbitration_id, data, is_extended):
                self.results_text.insert(tk.END, f"Set CAN ID HIGH to {new_id} for servo {servo_id}\n")
                self.results_text.see(tk.END)
                self.status_label.config(text=f"CAN ID HIGH set to {new_id}")
            else:
                self.results_text.insert(tk.END, f"Failed to set CAN ID HIGH\n")
                self.results_text.see(tk.END)
                
        except Exception as e:
            self.logger.error(f"Error setting CAN ID HIGH: {e}")
            messagebox.showerror("Error", f"Failed to set CAN ID HIGH: {e}")
    
    def set_servo_can_mode(self):
        """Set servo CAN mode"""
        try:
            servo_id = int(self.target_servo_var.get())
            mode = int(self.can_mode_var.get().split()[0])  # Extract number from "0 - Standard"
            is_extended = self.extended_id_var.get()
            
            # Send CAN message to set CAN mode (register 0x6A)
            arbitration_id, data = self.servo_protocol.create_write_message(servo_id, 0x6A, mode, is_extended)
            if self.can_interface.send_message(arbitration_id, data, is_extended):
                mode_str = "Extended" if mode == 1 else "Standard"
                self.results_text.insert(tk.END, f"Set CAN mode to {mode_str} for servo {servo_id}\n")
                self.results_text.see(tk.END)
                self.status_label.config(text=f"CAN mode set to {mode_str}")
            else:
                self.results_text.insert(tk.END, f"Failed to set CAN mode\n")
                self.results_text.see(tk.END)
                
        except Exception as e:
            self.logger.error(f"Error setting CAN mode: {e}")
            messagebox.showerror("Error", f"Failed to set CAN mode: {e}")
    
    def set_servo_node_id(self):
        """Set servo node ID"""
        try:
            servo_id = int(self.target_servo_var.get())
            new_node_id = int(self.servoid_var.get())
            is_extended = self.extended_id_var.get()
            
            # Send CAN message to set servo node ID (register 0x32)
            arbitration_id, data = self.servo_protocol.create_write_message(servo_id, 0x32, new_node_id, is_extended)
            if self.can_interface.send_message(arbitration_id, data, is_extended):
                self.results_text.insert(tk.END, f"Set servo node ID to {new_node_id} for servo {servo_id}\n")
                self.results_text.see(tk.END)
                self.status_label.config(text=f"Servo node ID set to {new_node_id}")
            else:
                self.results_text.insert(tk.END, f"Failed to set servo node ID\n")
                self.results_text.see(tk.END)
                
        except Exception as e:
            self.logger.error(f"Error setting servo node ID: {e}")
            messagebox.showerror("Error", f"Failed to set servo node ID: {e}")
    
    def set_servo_position(self):
        """Set servo position"""
        try:
            servo_id = int(self.target_servo_var.get())
            position = int(self.position_var.get())
            is_extended = self.extended_id_var.get()
            
            # Send CAN message to set position (register 0x0C)
            arbitration_id, data = self.servo_protocol.create_write_message(servo_id, 0x1E, position, is_extended)
            if self.can_interface.send_message(arbitration_id, data, is_extended):
                self.results_text.insert(tk.END, f"Set position to {position} for servo {servo_id}\n")
                self.results_text.see(tk.END)
                self.status_label.config(text=f"Position set to {position}")
            else:
                self.results_text.insert(tk.END, f"Failed to set position\n")
                self.results_text.see(tk.END)
                
        except Exception as e:
            self.logger.error(f"Error setting position: {e}")
            messagebox.showerror("Error", f"Failed to set position: {e}")
    
    def read_servo_register(self, register_addr=None):
        """Read a servo register"""
        try:
            servo_id = int(self.target_servo_var.get())
            is_extended = self.extended_id_var.get()
            
            if register_addr is None:
                # Parse from GUI
                addr_str = self.read_address_var.get()
                if addr_str.startswith('0x'):
                    register_addr = int(addr_str, 16)
                else:
                    register_addr = int(addr_str)
            
            # Check if CAN interface is connected
            if not self.can_interface.is_connected:
                self.results_text.insert(tk.END, f"❌ CAN interface not connected. Please connect first.\n")
                self.results_text.see(tk.END)
                messagebox.showerror("Error", "CAN interface not connected")
                return
            
            # Send CAN message to read register
            arbitration_id, data = self.servo_protocol.create_read_message(servo_id, register_addr, is_extended)
            if self.can_interface.send_message(arbitration_id, data, is_extended):
                self.results_text.insert(tk.END, f"📤 Reading register 0x{register_addr:02X} from servo {servo_id}...\n")
                self.results_text.see(tk.END)
                self.status_label.config(text=f"Reading register 0x{register_addr:02X}")
                
                # Note: Responses will be handled by handle_servo_response() when received
                # No timeout check needed as responses show up immediately in message monitor
            else:
                self.results_text.insert(tk.END, f"❌ Failed to send read request for register 0x{register_addr:02X}\n")
                self.results_text.see(tk.END)
                
        except Exception as e:
            self.logger.error(f"Error reading register: {e}")
            messagebox.showerror("Error", f"Failed to read register: {e}")
    
    def handle_servo_response(self, msg):
        """Handle servo response message in results section"""
        try:
            # Check if this is a servo protocol response message
            if len(msg.data) >= 3:
                command = msg.data[0]
                servo_id = msg.data[1]
                register = msg.data[2]
                
                # Handle single register response (0x76)
                if command == 0x76 and len(msg.data) >= 5:
                    value = msg.data[3] | (msg.data[4] << 8)  # Little endian
                    reg_name = self.get_register_name(register)
                    
                    self.results_text.insert(tk.END, f"✅ Servo {servo_id} register 0x{register:02X} ({reg_name}) = {value}\n")
                    self.results_text.see(tk.END)
                    
                # Handle dual register response (0x56)
                elif command == 0x56 and len(msg.data) >= 7:
                    reg1 = register
                    val1 = msg.data[3] | (msg.data[4] << 8) 
                    reg2 = msg.data[5] if len(msg.data) > 5 else 0
                    val2 = msg.data[6] | (msg.data[7] << 8) if len(msg.data) > 7 else 0
                    
                    reg1_name = self.get_register_name(reg1)
                    reg2_name = self.get_register_name(reg2)
                    
                    self.results_text.insert(tk.END, f"✅ Servo {servo_id} dual response:\n")
                    self.results_text.insert(tk.END, f"   0x{reg1:02X} ({reg1_name}) = {val1}\n")
                    self.results_text.insert(tk.END, f"   0x{reg2:02X} ({reg2_name}) = {val2}\n")
                    self.results_text.see(tk.END)
                    
        except Exception as e:
            self.logger.error(f"Error handling servo response: {e}")
    
    def check_read_timeout(self, servo_id, register_addr):
        """Check if servo register read timed out"""
        try:
            # This is a simplified timeout check - in a real implementation, 
            # you would track pending requests and their responses
            self.results_text.insert(tk.END, f"⏰ No response from servo {servo_id} for register 0x{register_addr:02X}\n")
            self.results_text.insert(tk.END, f"   This is normal if no servo is connected to CAN bus.\n")
            self.results_text.insert(tk.END, f"   Check:\n")
            self.results_text.insert(tk.END, f"   • Servo is powered and connected to CAN bus\n")
            self.results_text.insert(tk.END, f"   • Correct servo ID (current: {servo_id})\n")
            self.results_text.insert(tk.END, f"   • CAN bus termination is proper\n")
            self.results_text.insert(tk.END, f"   • Bitrate matches servo settings\n\n")
            self.results_text.see(tk.END)
        except Exception as e:
            self.logger.error(f"Error in timeout check: {e}")
    
    def read_can_id_registers(self):
        """Read both CAN ID registers"""
        try:
            # Read CAN ID LOW (0x3E) and HIGH (0x3C)
            self.read_servo_register(0x3E)
            self.read_servo_register(0x3C)
            
        except Exception as e:
            self.logger.error(f"Error reading CAN ID registers: {e}")
    
    def save_and_reset_servo(self):
        """Save servo configuration and reset"""
        try:
            servo_id = int(self.target_servo_var.get())
            is_extended = self.extended_id_var.get()
            
            # Send save configuration command
            arbitration_id, data = self.servo_protocol.create_save_reset_message(servo_id, is_extended)
            if self.can_interface.send_message(arbitration_id, data, is_extended):
                self.results_text.insert(tk.END, f"Saving configuration for servo {servo_id}\n")
                self.results_text.see(tk.END)
                self.status_label.config(text="Configuration saved")
                
                # Optional: Send reset command after save
                time.sleep(0.1)  # Brief delay
                arbitration_id, data = self.servo_protocol.create_save_reset_message(servo_id, is_extended)
                if self.can_interface.send_message(arbitration_id, data, is_extended):
                    self.results_text.insert(tk.END, f"Reset command sent to servo {servo_id}\n")
                    self.results_text.see(tk.END)
            else:
                self.results_text.insert(tk.END, f"Failed to save configuration\n")
                self.results_text.see(tk.END)
                
        except Exception as e:
            self.logger.error(f"Error saving and resetting servo: {e}")
            messagebox.showerror("Error", f"Failed to save and reset servo: {e}")
    
    # Message Monitoring Methods
    def toggle_monitoring(self):
        """Toggle message monitoring"""
        try:
            if hasattr(self, 'is_monitoring') and self.is_monitoring:
                self.is_monitoring = False
                self.monitor_btn.config(text="Start Monitoring")
                self.status_label.config(text="Monitoring stopped")
            else:
                self.is_monitoring = True
                self.monitor_btn.config(text="Stop Monitoring")
                self.status_label.config(text="Monitoring started")
                
        except Exception as e:
            self.logger.error(f"Error toggling monitoring: {e}")
    
    def save_message_log(self):
        """Save message log to file"""
        try:
            filename = f"can_messages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            with open(filename, 'w') as f:
                f.write("CAN Message Log\n")
                f.write("=" * 50 + "\n\n")
                
                for item in self.message_tree.get_children():
                    values = self.message_tree.item(item)['values']
                    f.write(f"Time: {values[0]}, ID: {values[1]}, Data: {values[2]}, Description: {values[3]}\n")
            
            self.status_label.config(text=f"Log saved to {filename}")
            messagebox.showinfo("Log Saved", f"Message log saved to {filename}")
            
        except Exception as e:
            self.logger.error(f"Error saving message log: {e}")
            messagebox.showerror("Error", f"Failed to save message log: {e}")
    
    # Configuration Methods
    def save_configuration(self):
        """Save current configuration to file"""
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                config = {
                    'can_channel': self.channel_var.get(),
                    'can_bitrate': int(self.bitrate_var.get()),
                    'target_servo_id': self.target_servo_var.get(),
                    'auto_reset_enabled': self.auto_reset_var.get()
                }
                
                with open(filename, 'w') as f:
                    import json
                    json.dump(config, f, indent=2)
                
                self.status_label.config(text=f"Configuration saved to {filename}")
                messagebox.showinfo("Configuration Saved", f"Configuration saved to {filename}")
                
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            messagebox.showerror("Error", f"Failed to save configuration: {e}")
    
    def load_configuration(self):
        """Load configuration from file"""
        try:
            from tkinter import filedialog
            filename = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                with open(filename, 'r') as f:
                    import json
                    config = json.load(f)
                
                # Apply loaded configuration
                if 'can_channel' in config:
                    self.channel_var.set(config['can_channel'])
                if 'can_bitrate' in config:
                    self.bitrate_var.set(str(config['can_bitrate']))
                if 'target_servo_id' in config:
                    self.target_servo_var.set(config['target_servo_id'])
                if 'auto_reset_enabled' in config:
                    self.auto_reset_var.set(config['auto_reset_enabled'])
                
                self.update_config_display()
                self.status_label.config(text=f"Configuration loaded from {filename}")
                messagebox.showinfo("Configuration Loaded", f"Configuration loaded from {filename}")
                
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            messagebox.showerror("Error", f"Failed to load configuration: {e}")
    
    def reset_configuration(self):
        """Reset configuration to defaults"""
        try:
            result = messagebox.askyesno("Reset Configuration", "Are you sure you want to reset to default configuration?")
            
            if result:
                # Reset to defaults
                self.channel_var.set("")
                self.bitrate_var.set("500000")
                self.target_servo_var.set("30")
                self.auto_reset_var.set(True)
                
                self.update_config_display()
                self.status_label.config(text="Configuration reset to defaults")
                
        except Exception as e:
            self.logger.error(f"Error resetting configuration: {e}")
            messagebox.showerror("Error", f"Failed to reset configuration: {e}")
    
    def send_custom_message(self):
        """Send custom CAN message"""
        try:
            # Parse message ID
            msg_id_str = self.custom_id_var.get()
            if msg_id_str.startswith('0x'):
                msg_id = int(msg_id_str, 16)
            else:
                msg_id = int(msg_id_str)
            
            # Parse data
            data_str = self.custom_data_var.get()
            data_bytes = []
            
            # Split by spaces and convert to bytes
            for hex_str in data_str.split():
                data_bytes.append(int(hex_str, 16))
            
            # Create and send message
            extended = self.custom_extended_var.get()
            arbitration_id, data = self.servo_protocol.create_custom_message(msg_id, data_bytes, extended)
            
            if self.can_interface.send_message(arbitration_id, data, extended):
                self.status_label.config(text=f"Sent custom message ID: 0x{msg_id:03X}")
                self.logger.info(f"Sent custom CAN message: ID=0x{msg_id:03X}, Data={data_str}")
            else:
                self.status_label.config(text="Failed to send custom message")
                
        except Exception as e:
            self.logger.error(f"Error sending custom message: {e}")
            messagebox.showerror("Error", f"Failed to send custom message: {e}")
    
    def decode_message_description(self, msg_id, data):
        """Decode CAN message to provide description"""
        try:
            # Basic servo protocol decoding
            if len(data) >= 3:
                command = data[0]
                servo_id = data[1] if len(data) > 1 else 0
                register = data[2] if len(data) > 2 else 0
                
                # Command decoding based on Hitec protocol
                if command == 0x72:  # Read single register command
                    reg_name = self.get_register_name(register)
                    return f"Read {reg_name} (0x{register:02X}) from servo {servo_id}"
                elif command == 0x52:  # Read dual register command
                    reg_name = self.get_register_name(register)
                    return f"Read dual {reg_name} (0x{register:02X}) from servo {servo_id}"
                elif command == 0x77:  # Write single register command
                    reg_name = self.get_register_name(register)
                    if len(data) >= 5:
                        value = data[3] | (data[4] << 8)  # Little endian 16-bit value
                        return f"Write {reg_name} (0x{register:02X}) = {value} to servo {servo_id}"
                    else:
                        return f"Write {reg_name} (0x{register:02X}) to servo {servo_id}"
                elif command == 0x57:  # Write dual register command
                    return f"Write dual registers to servo {servo_id}"
                elif command == 0x76:  # Single register response
                    reg_name = self.get_register_name(register)
                    if len(data) >= 5:
                        value = data[3] | (data[4] << 8)  # Little endian 16-bit value
                        return f"Response {reg_name} (0x{register:02X}) = {value} from servo {servo_id}"
                    else:
                        return f"Response {reg_name} (0x{register:02X}) from servo {servo_id}"
                elif command == 0x56:  # Dual register response
                    return f"Dual register response from servo {servo_id}"
                else:
                    return f"Command 0x{command:02X} to servo {servo_id}, register 0x{register:02X}"
            
            return "CAN message"
            
        except Exception as e:
            self.logger.error(f"Error decoding message: {e}")
            return "Unknown message"
    
    def get_register_name(self, register):
        """Get human-readable register name"""
        register_names = {
            0x06: "CAN_ID_LOW",
            0x07: "CAN_ID_HIGH", 
            0x0A: "MIN_POSITION",
            0x0B: "MAX_POSITION",
            0x0C: "POSITION",
            0x20: "OPERATING_MODE",
            0x21: "SPEED",
            0x22: "TORQUE_LIMIT",
            0x32: "SERVO_ID",
            0x6A: "CAN_MODE"
        }
        return register_names.get(register, f"REG_0x{register:02X}")
    
    def on_can_message_received(self, msg):
        """Handle received CAN message with description"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            msg_id_str = f"0x{msg.arbitration_id:03X}"
            data_str = ' '.join([f"{b:02X}" for b in msg.data])
            description = self.decode_message_description(msg.arbitration_id, msg.data)
            
            # Update message count
            self.message_count += 1
            
            # Schedule GUI update in main thread
            self.root.after(0, lambda: self.add_message_to_tree(timestamp, msg_id_str, data_str, description))
            
            # Also update servo control results if this is a servo response
            self.root.after(0, lambda: self.handle_servo_response(msg))
            
        except Exception as e:
            self.logger.error(f"Error processing received message: {e}")
    
    def add_message_to_tree(self, timestamp, msg_id, data, description):
        """Add message to tree view with description"""
        try:
            # Only add if monitoring is enabled or always show
            if not hasattr(self, 'is_monitoring') or self.is_monitoring:
                self.message_tree.insert("", 0, values=(timestamp, msg_id, data, description))
                
                # Update message count
                self.message_count_var.set(f"Messages: {self.message_count}")
                
                # Limit number of displayed messages
                children = self.message_tree.get_children()
                if len(children) > 1000:
                    # Remove oldest messages
                    for item in children[-100:]:  # Remove last 100 items
                        self.message_tree.delete(item)
                
        except Exception as e:
            self.logger.error(f"Error adding message to tree: {e}")
    
    def update_config_display(self):
        """Update configuration display"""
        try:
            import json
            config_text = json.dumps(self.config, indent=2)
            self.config_text.delete(1.0, tk.END)
            self.config_text.insert(1.0, config_text)
        except Exception as e:
            self.logger.error(f"Error updating config display: {e}")
    
    def apply_config(self):
        """Apply saved configuration"""
        try:
            if 'connection' in self.config:
                conn_config = self.config['connection']
                if 'bitrate' in conn_config:
                    self.bitrate_var.set(str(conn_config['bitrate']))
                    
        except Exception as e:
            self.logger.error(f"Error applying config: {e}")
    
    def save_config(self):
        """Save current configuration"""
        try:
            self.config['connection'] = {
                'channel': self.channel_var.get(),
                'bitrate': int(self.bitrate_var.get())
            }
            self.config_manager.save_config(self.config)
            self.update_config_display()
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")
    
    def on_closing(self):
        """Handle application closing"""
        try:
            self.save_config()
            if self.connected:
                self.disconnect_can()
            self.root.destroy()
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            self.root.destroy()
    
    def run(self):
        """Start the GUI application"""
        try:
            self.logger.info("Starting GUI application")
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"GUI application error: {e}")
            raise

def main():
    """Main application entry point"""
    try:
        print("Starting Hitec CAN Servo Programming Tool (Desktop Version)")
        app = ServoControlGUI()
        app.run()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
    except Exception as e:
        print(f"Application failed to start: {e}")
        raise

if __name__ == "__main__":
    main()