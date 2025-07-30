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
        
        # Servo settings
        settings_frame = ttk.LabelFrame(container, text="Servo Settings", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(settings_frame, text="Servo ID:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        servo_id_entry = ttk.Entry(settings_frame, textvariable=self.servo_id_var, width=10)
        servo_id_entry.grid(row=0, column=1, sticky="w", padx=(0, 20))
        
        ttk.Label(settings_frame, text="Register Address:").grid(row=0, column=2, sticky="w", padx=(0, 10))
        addr_entry = ttk.Entry(settings_frame, textvariable=self.register_addr_var, width=10)
        addr_entry.grid(row=0, column=3, sticky="w", padx=(0, 20))
        
        ttk.Label(settings_frame, text="Register Value:").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(10, 0))
        value_entry = ttk.Entry(settings_frame, textvariable=self.register_value_var, width=10)
        value_entry.grid(row=1, column=1, sticky="w", padx=(0, 20), pady=(10, 0))
        
        # Control buttons
        button_frame = ttk.Frame(settings_frame)
        button_frame.grid(row=2, column=0, columnspan=4, pady=(20, 0), sticky="w")
        
        ttk.Button(button_frame, text="Read Register", command=self.read_register).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Write Register", command=self.write_register).pack(side=tk.LEFT, padx=(0, 10))
        
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
            ("0x06", "CAN_ID", "CAN Bus ID", "1-127"),
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
        
        # Controls
        controls_frame = ttk.Frame(container)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(controls_frame, text="Clear Messages", command=self.clear_messages).pack(side=tk.LEFT, padx=(0, 10))
        
        self.auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls_frame, text="Auto Scroll", variable=self.auto_scroll_var).pack(side=tk.LEFT)
        
        # Message display
        msg_frame = ttk.LabelFrame(container, text="CAN Messages", padding="10")
        msg_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Create treeview for messages
        msg_columns = ("Time", "ID", "Data", "Length")
        self.msg_tree = ttk.Treeview(msg_frame, columns=msg_columns, show="headings", height=15)
        
        for col in msg_columns:
            self.msg_tree.heading(col, text=col)
        
        self.msg_tree.column("Time", width=100)
        self.msg_tree.column("ID", width=80)
        self.msg_tree.column("Data", width=200)
        self.msg_tree.column("Length", width=60)
        
        # Scrollbars for message tree
        msg_v_scrollbar = ttk.Scrollbar(msg_frame, orient=tk.VERTICAL, command=self.msg_tree.yview)
        msg_h_scrollbar = ttk.Scrollbar(msg_frame, orient=tk.HORIZONTAL, command=self.msg_tree.xview)
        self.msg_tree.configure(yscrollcommand=msg_v_scrollbar.set, xscrollcommand=msg_h_scrollbar.set)
        
        msg_v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        msg_h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.msg_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Custom message sending
        custom_frame = ttk.LabelFrame(container, text="Send Custom Message", padding="10")
        custom_frame.pack(fill=tk.X)
        
        ttk.Label(custom_frame, text="CAN ID:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Entry(custom_frame, textvariable=self.can_id_var, width=15).grid(row=0, column=1, sticky="w", padx=(0, 20))
        
        ttk.Label(custom_frame, text="Data (hex):").grid(row=0, column=2, sticky="w", padx=(0, 10))
        ttk.Entry(custom_frame, textvariable=self.can_data_var, width=30).grid(row=0, column=3, sticky="ew", padx=(0, 20))
        
        ttk.Button(custom_frame, text="Send", command=self.send_custom_message).grid(row=0, column=4)
        
        custom_frame.columnconfigure(3, weight=1)
        
    def create_config_tab(self):
        """Create configuration tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Configuration")
        
        container = ttk.Frame(frame)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Configuration display
        config_frame = ttk.LabelFrame(container, text="Application Configuration", padding="10")
        config_frame.pack(fill=tk.BOTH, expand=True)
        
        self.config_text = scrolledtext.ScrolledText(config_frame, height=20, wrap=tk.WORD)
        self.config_text.pack(fill=tk.BOTH, expand=True)
        
        # Load and display current config
        self.update_config_display()
        
    def create_status_bar(self):
        """Create status bar at bottom of window"""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
        
        self.status_label = ttk.Label(self.status_bar, text="Ready")
        self.status_label.pack(side=tk.LEFT)
        
    def setup_message_callback(self):
        """Setup callback for receiving CAN messages"""
        def message_callback(msg):
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            # Schedule GUI update in main thread
            self.root.after(0, lambda: self.add_message_to_display(
                timestamp, 
                f"0x{msg.arbitration_id:03X}",
                ' '.join([f"{b:02X}" for b in msg.data]),
                str(len(msg.data))
            ))
        
        self.can_interface.add_message_callback(message_callback)
    
    def setup_error_callback(self):
        """Setup callback for CAN bus errors"""
        def error_callback(error_message):
            # Schedule GUI update in main thread
            self.root.after(0, lambda: self.handle_bus_error(error_message))
        
        self.can_interface.add_error_callback(error_callback)
        
    def add_message_to_display(self, timestamp, msg_id, data, length):
        """Add message to display (called from main thread)"""
        try:
            self.msg_tree.insert("", 0, values=(timestamp, msg_id, data, length))
            
            # Limit number of displayed messages
            children = self.msg_tree.get_children()
            if len(children) > 1000:
                self.msg_tree.delete(children[-1])
            
            # Auto scroll to top if enabled
            if self.auto_scroll_var.get():
                self.msg_tree.selection_set(children[0])
                self.msg_tree.see(children[0])
                
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
            
            arbitration_id, message_data = self.servo_protocol.create_read_message(servo_id, addr)
            
            if self.can_interface.send_message(arbitration_id, message_data):
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
            
            arbitration_id, message_data = self.servo_protocol.create_write_message(servo_id, addr, value)
            
            if self.can_interface.send_message(arbitration_id, message_data):
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
            
            if self.can_interface.send_message(id_int, bytes(data_bytes)):
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
            for item in self.msg_tree.get_children():
                self.msg_tree.delete(item)
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