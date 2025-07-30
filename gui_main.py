"""
Main GUI application for Hitec CAN Servo Programming Tool
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import time
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from can_interface import CANInterface, CANMessage
from servo_protocol import ServoProtocol, MessageType
from config_manager import ConfigManager
from utils import format_hex_bytes, parse_hex_input, validate_numeric_input

class ServoControlGUI:
    """Main GUI application class"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.can_interface = CANInterface()
        self.servo_protocol = ServoProtocol()
        self.config_manager = ConfigManager()
        
        # GUI state
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.message_count = 0
        
        # Load configuration
        self.config = self.config_manager.load_config()
        
        # Setup GUI
        self.setup_gui()
        self.setup_message_callback()
        
        # Apply saved configuration and refresh channels after GUI is ready
        self.apply_config()
        
        # Initial channel refresh after everything is set up
        self.root.after(100, self.refresh_channels)
        
    def setup_gui(self):
        """Setup the main GUI layout"""
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        
        # Create tabs
        self.create_connection_tab()
        self.create_servo_control_tab()
        self.create_message_monitor_tab()
        self.create_configuration_tab()
        
        # Status bar
        self.create_status_bar(main_frame)
        
    def create_connection_tab(self):
        """Create CAN connection configuration tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="Connection")
        
        # CAN Interface Settings
        settings_frame = ttk.LabelFrame(frame, text="CAN Interface Settings", padding="10")
        settings_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        # Channel selection
        ttk.Label(settings_frame, text="PCAN Channel:").grid(row=0, column=0, sticky="w", pady=2)
        self.channel_var = tk.StringVar(value=self.config.get('can_channel', ''))
        self.channel_combo = ttk.Combobox(settings_frame, textvariable=self.channel_var, width=20, state="readonly")
        self.channel_combo.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=2)
        
        # Add placeholder text when no channel is selected
        if not self.channel_var.get():
            self.channel_combo.set("Select CAN Interface...")
        
        # Refresh channels button
        ttk.Button(settings_frame, text="Refresh", 
                  command=self.refresh_channels).grid(row=0, column=2, padx=(10, 0), pady=2)
        
        # Bitrate selection
        ttk.Label(settings_frame, text="Bitrate (bps):").grid(row=1, column=0, sticky="w", pady=2)
        self.bitrate_var = tk.StringVar(value=str(self.config.get('can_bitrate', 500000)))
        bitrate_combo = ttk.Combobox(settings_frame, textvariable=self.bitrate_var, width=20)
        bitrate_combo['values'] = ('125000', '250000', '500000', '1000000')
        bitrate_combo.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=2)
        
        settings_frame.columnconfigure(1, weight=1)
        
        # Connection Controls
        controls_frame = ttk.Frame(frame)
        controls_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        self.connect_btn = ttk.Button(controls_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.connection_status_var = tk.StringVar(value="Disconnected")
        ttk.Label(controls_frame, textvariable=self.connection_status_var).pack(side=tk.LEFT)
        
        # Connection Info
        info_frame = ttk.LabelFrame(frame, text="Connection Info", padding="10")
        info_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        
        self.info_text = scrolledtext.ScrolledText(info_frame, height=8, width=60)
        self.info_text.pack(fill=tk.BOTH, expand=True)
        
        # Add initial helpful information
        initial_info = """Welcome to Hitec CAN Servo Programming Tool

Getting Started:
1. Click 'Refresh' to scan for available PCAN interfaces
2. Select your CAN interface from the dropdown
3. Choose appropriate bitrate (typically 500000 bps)
4. Click 'Connect' to establish connection
5. Use the 'Servo Control' tab to program your servos

Requirements:
• PCAN USB adapter connected
• PCAN drivers installed
• CAN bus with Hitec servos
"""
        self.info_text.insert(1.0, initial_info)
        
        frame.rowconfigure(2, weight=1)
        frame.columnconfigure(1, weight=1)
        
    def create_servo_control_tab(self):
        """Create servo control and programming tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="Servo Control")
        
        # Servo Settings Frame
        servo_frame = ttk.LabelFrame(frame, text="Servo Settings", padding="10")
        servo_frame.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        # Servo ID
        ttk.Label(servo_frame, text="Servo ID:").grid(row=0, column=0, sticky="w", pady=2)
        self.servo_id_var = tk.StringVar(value="0")
        servo_id_entry = ttk.Entry(servo_frame, textvariable=self.servo_id_var, width=10)
        servo_id_entry.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=2)
        
        # Extended ID checkbox
        self.extended_id_var = tk.BooleanVar()
        ttk.Checkbutton(servo_frame, text="Extended CAN ID (29-bit)", 
                       variable=self.extended_id_var).grid(row=1, column=0, columnspan=2, sticky="w", pady=2)
        
        # CAN ID Programming Frame
        can_id_frame = ttk.LabelFrame(frame, text="CAN ID Programming", padding="10")
        can_id_frame.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=10)
        
        ttk.Label(can_id_frame, text="New CAN ID LOW:").grid(row=0, column=0, sticky="w", pady=2)
        self.new_can_id_low_var = tk.StringVar(value="30")
        ttk.Entry(can_id_frame, textvariable=self.new_can_id_low_var, width=10).grid(row=0, column=1, sticky="w", padx=(10, 0), pady=2)
        
        ttk.Button(can_id_frame, text="Set CAN ID LOW", 
                  command=self.set_servo_can_id_low).grid(row=0, column=2, padx=(10, 0), pady=2)
        
        ttk.Label(can_id_frame, text="New CAN ID HIGH:").grid(row=1, column=0, sticky="w", pady=2)
        self.new_can_id_high_var = tk.StringVar(value="30")
        ttk.Entry(can_id_frame, textvariable=self.new_can_id_high_var, width=10).grid(row=1, column=1, sticky="w", padx=(10, 0), pady=2)
        
        ttk.Button(can_id_frame, text="Set CAN ID HIGH", 
                  command=self.set_servo_can_id_high).grid(row=1, column=2, padx=(10, 0), pady=2)
        
        ttk.Label(can_id_frame, text="CAN Mode:").grid(row=2, column=0, sticky="w", pady=2)
        self.can_mode_var = tk.StringVar(value="1")
        can_mode_combo = ttk.Combobox(can_id_frame, textvariable=self.can_mode_var, width=15)
        can_mode_combo['values'] = ('0 - Standard', '1 - Extended')
        can_mode_combo.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=2)
        
        ttk.Button(can_id_frame, text="Set CAN Mode", 
                  command=self.set_servo_can_mode).grid(row=2, column=2, padx=(10, 0), pady=2)
        
        ttk.Label(can_id_frame, text="SERVO NODE ID:").grid(row=3, column=0, sticky="w", pady=2)
        self.servoid_var = tk.StringVar(value="30")
        ttk.Entry(can_id_frame, textvariable=self.servoid_var, width=10).grid(row=3, column=1, sticky="w", padx=(10, 0), pady=2)
        
        ttk.Button(can_id_frame, text="Set SERVO NODE ID", 
                  command=self.set_servo_node_id).grid(row=3, column=2, padx=(10, 0), pady=2)
        
        # Position Control Frame
        position_frame = ttk.LabelFrame(frame, text="Position Control", padding="10")
        position_frame.grid(row=2, column=0, sticky="ew", padx=(0, 10), pady=10)
        
        ttk.Label(position_frame, text="Position:").grid(row=0, column=0, sticky="w", pady=2)
        self.position_var = tk.StringVar(value="1500")
        ttk.Entry(position_frame, textvariable=self.position_var, width=10).grid(row=0, column=1, sticky="w", padx=(10, 0), pady=2)
        
        ttk.Button(position_frame, text="Set Position", 
                  command=self.set_servo_position).grid(row=0, column=2, padx=(10, 0), pady=2)
        
        # Data Reading Frame
        read_frame = ttk.LabelFrame(frame, text="Data Reading", padding="10")
        read_frame.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=10)
        
        # Register reading
        ttk.Label(read_frame, text="Register Address:").grid(row=0, column=0, sticky="w", pady=2)
        self.read_address_var = tk.StringVar(value="0x32")
        ttk.Entry(read_frame, textvariable=self.read_address_var, width=10).grid(row=0, column=1, sticky="w", padx=(10, 0), pady=2)
        
        ttk.Button(read_frame, text="Read Register", 
                  command=self.read_servo_register).grid(row=0, column=2, padx=(10, 0), pady=2)
        
        # Common operations
        ttk.Button(read_frame, text="Read Servo ID", 
                  command=lambda: self.read_servo_register(0x32)).grid(row=1, column=0, columnspan=3, sticky="ew", pady=2)
        
        ttk.Button(read_frame, text="Read CAN Mode", 
                  command=lambda: self.read_servo_register(0x6A)).grid(row=2, column=0, columnspan=3, sticky="ew", pady=2)
        
        ttk.Button(read_frame, text="Read CAN ID", 
                  command=self.read_can_id_registers).grid(row=3, column=0, columnspan=3, sticky="ew", pady=2)
        
        ttk.Button(read_frame, text="Save & Reset", 
                  command=self.save_and_reset_servo).grid(row=4, column=0, columnspan=3, sticky="ew", pady=10)
        
        # Results area
        ttk.Label(read_frame, text="Results:").grid(row=5, column=0, sticky="w", pady=(10, 2))
        self.results_text = scrolledtext.ScrolledText(read_frame, height=15, width=40)
        self.results_text.grid(row=6, column=0, columnspan=3, sticky="nsew", pady=2)
        
        read_frame.columnconfigure(0, weight=1)
        read_frame.rowconfigure(6, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(2, weight=1)
        
    def create_message_monitor_tab(self):
        """Create CAN message monitoring tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="Message Monitor")
        
        # Controls frame
        controls_frame = ttk.Frame(frame)
        controls_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        self.monitor_btn = ttk.Button(controls_frame, text="Start Monitoring", 
                                     command=self.toggle_monitoring)
        self.monitor_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(controls_frame, text="Clear Messages", 
                  command=self.clear_messages).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(controls_frame, text="Save Log", 
                  command=self.save_message_log).pack(side=tk.LEFT, padx=(0, 10))
        
        # Message count
        self.message_count_var = tk.StringVar(value="Messages: 0")
        ttk.Label(controls_frame, textvariable=self.message_count_var).pack(side=tk.RIGHT)
        
        # Custom message frame
        custom_frame = ttk.LabelFrame(frame, text="Send Custom Message", padding="10")
        custom_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        ttk.Label(custom_frame, text="Message ID:").grid(row=0, column=0, sticky="w", pady=2)
        self.custom_id_var = tk.StringVar(value="0x000")
        ttk.Entry(custom_frame, textvariable=self.custom_id_var, width=10).grid(row=0, column=1, sticky="w", padx=(10, 0), pady=2)
        
        self.custom_extended_var = tk.BooleanVar()
        ttk.Checkbutton(custom_frame, text="Extended ID", 
                       variable=self.custom_extended_var).grid(row=0, column=2, padx=(10, 0), pady=2)
        
        ttk.Label(custom_frame, text="Data (hex):").grid(row=1, column=0, sticky="w", pady=2)
        self.custom_data_var = tk.StringVar(value="72 00 32")
        ttk.Entry(custom_frame, textvariable=self.custom_data_var, width=30).grid(row=1, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=2)
        
        ttk.Button(custom_frame, text="Send Message", 
                  command=self.send_custom_message).grid(row=2, column=0, columnspan=3, pady=10)
        
        custom_frame.columnconfigure(1, weight=1)
        
        # Message display
        self.message_tree = ttk.Treeview(frame, columns=('Time', 'ID', 'Data', 'Description'), show='headings', height=20)
        self.message_tree.grid(row=2, column=0, sticky="nsew")
        
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
        tree_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.message_tree.yview)
        tree_scroll.grid(row=2, column=1, sticky="ns")
        self.message_tree.configure(yscrollcommand=tree_scroll.set)
        
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)
        
    def create_configuration_tab(self):
        """Create configuration management tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="Configuration")
        
        # Configuration file management
        file_frame = ttk.LabelFrame(frame, text="Configuration Files", padding="10")
        file_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        ttk.Button(file_frame, text="Save Configuration", 
                  command=self.save_configuration).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(file_frame, text="Load Configuration", 
                  command=self.load_configuration).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(file_frame, text="Reset to Defaults", 
                  command=self.reset_configuration).pack(side=tk.LEFT, padx=(0, 10))
        
        # Current configuration display
        config_frame = ttk.LabelFrame(frame, text="Current Configuration", padding="10")
        config_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=10)
        
        self.config_text = scrolledtext.ScrolledText(config_frame, height=20, width=80)
        self.config_text.pack(fill=tk.BOTH, expand=True)
        
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)
        
        # Update configuration display
        self.update_config_display()
        
    def create_status_bar(self, parent):
        """Create status bar"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        
        # CAN status indicator
        self.can_status_var = tk.StringVar(value="CAN: Disconnected")
        ttk.Label(status_frame, textvariable=self.can_status_var).pack(side=tk.RIGHT)
        
    def setup_message_callback(self):
        """Setup CAN message callback"""
        self.can_interface.add_message_callback(self.on_can_message_received)
        
    def refresh_channels(self):
        """Refresh available PCAN channels"""
        try:
            self.status_var.set("Scanning for CAN interfaces...")
            channels = self.can_interface.get_available_channels()
            
            if channels:
                self.channel_combo['values'] = channels
                # If no channel selected or current selection not available, show prompt
                if not self.channel_var.get() or self.channel_var.get() not in channels:
                    if self.channel_var.get() == "Select CAN Interface...":
                        # Keep placeholder text
                        pass
                    else:
                        # Set to first available if we had a valid selection before
                        self.channel_var.set(channels[0])
                
                self.status_var.set(f"Found {len(channels)} CAN interface(s)")
                
                # Show message box on first startup to guide user
                if not hasattr(self, '_channels_scanned'):
                    self._channels_scanned = True
                    if len(channels) == 1:
                        result = messagebox.askyesno("CAN Interface Found", 
                                                   f"Found CAN interface: {channels[0]}\n\nWould you like to select it?")
                        if result:
                            self.channel_var.set(channels[0])
                    else:
                        messagebox.showinfo("CAN Interfaces Found", 
                                          f"Found {len(channels)} CAN interfaces.\nPlease select one from the dropdown to continue.")
            else:
                self.channel_combo['values'] = []
                self.channel_combo.set("No CAN interfaces found")
                self.status_var.set("No CAN interfaces detected")
                messagebox.showwarning("No CAN Interfaces", 
                                     "No PCAN interfaces were detected.\n\nPlease ensure:\n" +
                                     "• PCAN hardware is connected\n" +
                                     "• PCAN drivers are installed\n" +
                                     "• Interface is not in use by another application")
                
        except Exception as e:
            self.logger.error(f"Error refreshing channels: {e}")
            self.status_var.set("Error scanning CAN interfaces")
            messagebox.showerror("Error", f"Failed to scan CAN interfaces:\n{e}")
    
    def toggle_connection(self):
        """Toggle CAN connection"""
        if self.can_interface.is_connected:
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
            
            if self.can_interface.connect():
                self.connect_btn.config(text="Disconnect")
                self.connection_status_var.set("Connected")
                self.can_status_var.set(f"CAN: Connected ({channel})")
                self.status_var.set(f"Connected to {channel} at {bitrate} bps")
                
                # Update info display
                self.update_connection_info()
                
                self.logger.info(f"Connected to CAN interface: {channel}")
            else:
                messagebox.showerror("Connection Error", "Failed to connect to CAN interface")
                
        except ValueError:
            messagebox.showerror("Input Error", "Invalid bitrate value")
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            messagebox.showerror("Error", f"Connection failed:\n{e}")
    
    def disconnect_can(self):
        """Disconnect from CAN interface"""
        try:
            self.can_interface.disconnect()
            self.connect_btn.config(text="Connect")
            self.connection_status_var.set("Disconnected")
            self.can_status_var.set("CAN: Disconnected")
            self.status_var.set("Disconnected")
            
            # Stop monitoring if active
            if self.is_monitoring:
                self.toggle_monitoring()
            
            self.logger.info("Disconnected from CAN interface")
            
        except Exception as e:
            self.logger.error(f"Disconnect error: {e}")
    
    def update_connection_info(self):
        """Update connection information display"""
        try:
            status = self.can_interface.get_status()
            info_text = f"Connection Status: {'Connected' if status['connected'] else 'Disconnected'}\n"
            info_text += f"Channel: {status['channel']}\n"
            info_text += f"Bitrate: {status['bitrate']} bps\n"
            info_text += f"Messages Received: {status['messages_received']}\n"
            info_text += f"Receive Thread: {'Active' if status['receive_thread_active'] else 'Inactive'}\n"
            info_text += f"Last Updated: {datetime.now().strftime('%H:%M:%S')}\n"
            
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(1.0, info_text)
            
        except Exception as e:
            self.logger.error(f"Error updating connection info: {e}")
    
    def set_servo_can_id_low(self):
        """Set servo CAN ID LOW"""
        try:
            servo_id = int(self.servo_id_var.get())
            new_can_id = int(self.new_can_id_low_var.get())
            is_extended = self.extended_id_var.get()
            
            if not self.can_interface.is_connected:
                messagebox.showerror("Error", "CAN interface not connected")
                return
            
            if not self.servo_protocol.validate_servo_id(servo_id):
                messagebox.showerror("Error", "Invalid servo ID (0-255)")
                return
            
            # Create CAN ID programming messages
            messages = self.servo_protocol.create_set_can_id_low_message(servo_id, new_can_id, is_extended)
            
            # Send messages
            for arbitration_id, data in messages:
                if not self.can_interface.send_message(arbitration_id, data, is_extended):
                    messagebox.showerror("Error", "Failed to send CAN ID programming message")
                    return
                time.sleep(0.1)  # Small delay between messages
            
            self.status_var.set(f"CAN ID set to {new_can_id} for servo {servo_id}")
            self.add_result(f"Set CAN ID: Servo {servo_id} -> CAN ID {new_can_id}")
            
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric input")
        except Exception as e:
            self.logger.error(f"Error setting CAN ID: {e}")
            messagebox.showerror("Error", f"Failed to set CAN ID:\n{e}")


    def set_servo_can_id_high(self):
        """Set servo CAN ID HIGH"""
        try:
            servo_id = int(self.servo_id_var.get())
            new_can_id = int(self.new_can_id_high_var.get())
            is_extended = self.extended_id_var.get()
            
            if not self.can_interface.is_connected:
                messagebox.showerror("Error", "CAN interface not connected")
                return
            
            if not self.servo_protocol.validate_servo_id(servo_id):
                messagebox.showerror("Error", "Invalid servo ID (0-255)")
                return
            
            # Create CAN ID programming messages
            messages = self.servo_protocol.create_set_can_id_high_message(servo_id, new_can_id, is_extended)
            
            # Send messages
            for arbitration_id, data in messages:
                if not self.can_interface.send_message(arbitration_id, data, is_extended):
                    messagebox.showerror("Error", "Failed to send CAN ID programming message")
                    return
                time.sleep(0.1)  # Small delay between messages
            
            self.status_var.set(f"CAN ID set to {new_can_id} for servo {servo_id}")
            self.add_result(f"Set CAN ID: Servo {servo_id} -> CAN ID {new_can_id}")
            
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric input")
        except Exception as e:
            self.logger.error(f"Error setting CAN ID: {e}")
            messagebox.showerror("Error", f"Failed to set CAN ID:\n{e}")

    def set_servo_node_id(self):
        """Set servo NODE ID """
        try:
            servo_id = int(self.servo_id_var.get())
            new_servo_id = int(self.servoid_var.get())
            is_extended = self.extended_id_var.get()
            
            if not self.can_interface.is_connected:
                messagebox.showerror("Error", "CAN interface not connected")
                return
            
            if not self.servo_protocol.validate_servo_id(servo_id):
                messagebox.showerror("Error", "Invalid servo ID (0-255)")
                return
            
            # Create CAN ID programming messages
            messages = self.servo_protocol.create_set_servo_id_message(servo_id, new_servo_id, is_extended)
            
            # Send messages
            for arbitration_id, data in messages:
                if not self.can_interface.send_message(arbitration_id, data, is_extended):
                    messagebox.showerror("Error", "Failed to send CAN ID programming message")
                    return
                time.sleep(0.1)  # Small delay between messages
            
            self.status_var.set(f"SERVO ID set to {new_servo_id} for servo {servo_id}")
            self.add_result(f"Set SERVO ID: Servo {servo_id} -> CAN ID {new_servo_id}")
            
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric input")
        except Exception as e:
            self.logger.error(f"Error setting CAN ID: {e}")
            messagebox.showerror("Error", f"Failed to set CAN ID:\n{e}")

    def set_servo_can_mode(self):
        """Set servo CAN mode"""
        try:
            servo_id = int(self.servo_id_var.get())
            mode = int(self.can_mode_var.get().split()[0])
            is_extended = self.extended_id_var.get()
            
            if not self.can_interface.is_connected:
                messagebox.showerror("Error", "CAN interface not connected")
                return
            
            arbitration_id, data = self.servo_protocol.create_set_can_mode_message(servo_id, mode, is_extended)
            
            if self.can_interface.send_message(arbitration_id, data, is_extended):
                self.status_var.set(f"CAN mode set to {mode} for servo {servo_id}")
                self.add_result(f"Set CAN Mode: Servo {servo_id} -> Mode {mode}")
            else:
                messagebox.showerror("Error", "Failed to send CAN mode message")
                
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric input")
        except Exception as e:
            self.logger.error(f"Error setting CAN mode: {e}")
            messagebox.showerror("Error", f"Failed to set CAN mode:\n{e}")
    
    def set_servo_position(self):
        """Set servo position"""
        try:
            servo_id = int(self.servo_id_var.get())
            position = int(self.position_var.get())
            is_extended = self.extended_id_var.get()
            
            if not self.can_interface.is_connected:
                messagebox.showerror("Error", "CAN interface not connected")
                return
            
            arbitration_id, data = self.servo_protocol.create_position_command(servo_id, position, is_extended)
            
            if self.can_interface.send_message(arbitration_id, data, is_extended):
                self.status_var.set(f"Position {position} sent to servo {servo_id}")
                self.add_result(f"Set Position: Servo {servo_id} -> Position {position}")
            else:
                messagebox.showerror("Error", "Failed to send position command")
                
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric input")
        except Exception as e:
            self.logger.error(f"Error setting position: {e}")
            messagebox.showerror("Error", f"Failed to set position:\n{e}")
    
    def read_servo_register(self, address=None):
        """Read servo register"""
        try:
            servo_id = int(self.servo_id_var.get())
            is_extended = self.extended_id_var.get()
            
            if address is None:
                address_str = self.read_address_var.get()
                if address_str.startswith('0x'):
                    address = int(address_str, 16)
                else:
                    address = int(address_str)
            
            if not self.can_interface.is_connected:
                messagebox.showerror("Error", "CAN interface not connected")
                return
            
            arbitration_id, data = self.servo_protocol.create_read_message(servo_id, address, is_extended)
            
            if self.can_interface.send_message(arbitration_id, data, is_extended):
                reg_info = self.servo_protocol.get_register_info(address)
                self.status_var.set(f"Read request sent for register 0x{address:02X} ({reg_info.name})")
                self.add_result(f"Read Request: Servo {servo_id} -> Register 0x{address:02X} ({reg_info.name})")
            else:
                messagebox.showerror("Error", "Failed to send read request")
                
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric input")
        except Exception as e:
            self.logger.error(f"Error reading register: {e}")
            messagebox.showerror("Error", f"Failed to read register:\n{e}")
    
    def read_can_id_registers(self):
        """Read CAN ID high and low registers"""
        try:
            servo_id = int(self.servo_id_var.get())
            is_extended = self.extended_id_var.get()
            
            if not self.can_interface.is_connected:
                messagebox.showerror("Error", "CAN interface not connected")
                return
            
            # Read both CAN ID registers using dual read
            arbitration_id, data = self.servo_protocol.create_read_dual_message(servo_id, 0x3C, 0x3E, is_extended)
            
            if self.can_interface.send_message(arbitration_id, data, is_extended):
                self.status_var.set(f"CAN ID read request sent for servo {servo_id}")
                self.add_result(f"Read CAN ID: Servo {servo_id} -> Registers 0x3C, 0x3E")
            else:
                messagebox.showerror("Error", "Failed to send CAN ID read request")
                
        except ValueError:
            messagebox.showerror("Error", "Invalid servo ID")
        except Exception as e:
            self.logger.error(f"Error reading CAN ID: {e}")
            messagebox.showerror("Error", f"Failed to read CAN ID:\n{e}")
    
    def save_and_reset_servo(self):
        """Send save and reset command to servo"""
        try:
            servo_id = int(self.servo_id_var.get())
            is_extended = self.extended_id_var.get()
            
            if not self.can_interface.is_connected:
                messagebox.showerror("Error", "CAN interface not connected")
                return
            
            # Confirm action
            if not messagebox.askyesno("Confirm", f"Save and reset servo {servo_id}?"):
                return
            
            arbitration_id, data = self.servo_protocol.create_save_reset_message(servo_id, is_extended)
            
            if self.can_interface.send_message(arbitration_id, data, is_extended):
                self.status_var.set(f"Save and reset command sent to servo {servo_id}")
                self.add_result(f"Save & Reset: Servo {servo_id}")
            else:
                messagebox.showerror("Error", "Failed to send save and reset command")
                
        except ValueError:
            messagebox.showerror("Error", "Invalid servo ID")
        except Exception as e:
            self.logger.error(f"Error saving and resetting: {e}")
            messagebox.showerror("Error", f"Failed to save and reset:\n{e}")
    
    def toggle_monitoring(self):
        """Toggle CAN message monitoring"""
        if self.is_monitoring:
            self.stop_monitoring()
        else:
            self.start_monitoring()
    
    def start_monitoring(self):
        """Start CAN message monitoring"""
        if not self.can_interface.is_connected:
            messagebox.showerror("Error", "CAN interface not connected")
            return
        
        self.is_monitoring = True
        self.monitor_btn.config(text="Stop Monitoring")
        self.status_var.set("Monitoring CAN messages...")
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self.monitor_worker, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop CAN message monitoring"""
        self.is_monitoring = False
        self.monitor_btn.config(text="Start Monitoring")
        self.status_var.set("Monitoring stopped")
    
    def monitor_worker(self):
        """Worker thread for message monitoring"""
        while self.is_monitoring:
            try:
                messages = self.can_interface.get_received_messages(10)
                for msg in messages:
                    self.root.after(0, self.display_can_message, msg)
                time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Error in monitor worker: {e}")
                break
    
    def on_can_message_received(self, message: CANMessage):
        """Callback for received CAN messages"""
        # This runs in the CAN receive thread, so we need to use after()
        self.root.after(0, self.display_can_message, message)
    
    def display_can_message(self, message: CANMessage):
        """Display CAN message in the monitor"""
        try:
            self.message_count += 1
            self.message_count_var.set(f"Messages: {self.message_count}")
            
            # Format message data
            timestamp = datetime.fromtimestamp(message.timestamp).strftime('%H:%M:%S.%f')[:-3]
            can_id = f"0x{message.arbitration_id:X}"
            if message.is_extended_id:
                can_id += " (Ext)"
            
            data_hex = format_hex_bytes(message.data)
            
            # Try to parse servo protocol message
            description = "Unknown"
            parsed = self.servo_protocol.parse_response_message(message.data)
            if parsed:
                if parsed['type'] == 'single_response':
                    description = f"Response: {parsed['register_name']} = {parsed['value']} (Servo {parsed['servo_id']})"
                elif parsed['type'] == 'dual_response':
                    description = f"Response: {parsed['register_name_a']} = {parsed['value_a']}, {parsed['register_name_b']} = {parsed['value_b']} (Servo {parsed['servo_id']})"
            
            # Insert into tree
            self.message_tree.insert('', 0, values=(timestamp, can_id, data_hex, description))
            
            # Limit number of displayed messages
            children = self.message_tree.get_children()
            if len(children) > 1000:
                self.message_tree.delete(children[-100:])  # Remove oldest 100 messages
            
            # If this is a response to our read request, show in results
            if parsed:
                self.add_result(f"Received: {description}")

            if "Bus error" in str(message):
                self.logger.warning("CAN Bus Warning Detected")
                self.status_var.set("⚠️ CAN Bus Warning: Bus error threshold reached")
                messagebox.showwarning("CAN Bus Warning", "The CAN bus is in a warning/heavy state.\nTrying to reset connection...")
                self.reset_can_connection()
                return
    
        except Exception as e:
            self.logger.error(f"Error displaying message: {e}")
    
    def reset_can_connection(self):
        """Attempt to reset the CAN interface if it's in a heavy bus error state"""
        try:
            self.disconnect_can()
            time.sleep(1)
            self.connect_can()
            self.status_var.set("CAN bus reconnected after warning")
        except Exception as e:
            self.logger.error(f"Failed to reset CAN connection: {e}")
            messagebox.showerror("CAN Reset Failed", f"Could not recover CAN connection:\n{e}")


    def send_custom_message(self):
        """Send custom CAN message"""
        try:
            if not self.can_interface.is_connected:
                messagebox.showerror("Error", "CAN interface not connected")
                return
            
            # Parse message ID
            id_str = self.custom_id_var.get()
            if id_str.startswith('0x'):
                arbitration_id = int(id_str, 16)
            else:
                arbitration_id = int(id_str)
            
            # Parse data
            data_str = self.custom_data_var.get()
            data = parse_hex_input(data_str)
            
            is_extended = self.custom_extended_var.get()
            
            if self.can_interface.send_message(arbitration_id, data, is_extended):
                self.status_var.set(f"Custom message sent: ID=0x{arbitration_id:X}, Data={format_hex_bytes(data)}")
            else:
                messagebox.showerror("Error", "Failed to send custom message")
                
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
        except Exception as e:
            self.logger.error(f"Error sending custom message: {e}")
            messagebox.showerror("Error", f"Failed to send message:\n{e}")
    
    def clear_messages(self):
        """Clear message monitor"""
        self.message_tree.delete(*self.message_tree.get_children())
        self.message_count = 0
        self.message_count_var.set("Messages: 0")
        self.can_interface.clear_received_messages()
    
    def save_message_log(self):
        """Save message log to file"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            
            if filename:
                with open(filename, 'w') as f:
                    f.write("CAN Message Log\n")
                    f.write("=" * 50 + "\n")
                    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    
                    for child in reversed(self.message_tree.get_children()):
                        values = self.message_tree.item(child)['values']
                        f.write(f"{values[0]} | {values[1]} | {values[2]} | {values[3]}\n")
                
                self.status_var.set(f"Message log saved to {filename}")
                
        except Exception as e:
            self.logger.error(f"Error saving message log: {e}")
            messagebox.showerror("Error", f"Failed to save log:\n{e}")
    
    def add_result(self, text: str):
        """Add result to results display"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        result_line = f"[{timestamp}] {text}\n"
        
        self.results_text.insert(tk.END, result_line)
        self.results_text.see(tk.END)
    
    def save_configuration(self):
        """Save current configuration"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                config = self.get_current_config()
                self.config_manager.save_config_to_file(config, filename)
                self.status_var.set(f"Configuration saved to {filename}")
                
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            messagebox.showerror("Error", f"Failed to save configuration:\n{e}")
    
    def load_configuration(self):
        """Load configuration from file"""
        try:
            filename = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                config = self.config_manager.load_config_from_file(filename)
                self.apply_config(config)
                self.update_config_display()
                self.status_var.set(f"Configuration loaded from {filename}")
                
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            messagebox.showerror("Error", f"Failed to load configuration:\n{e}")
    
    def reset_configuration(self):
        """Reset configuration to defaults"""
        if messagebox.askyesno("Confirm", "Reset all settings to defaults?"):
            self.config = self.config_manager.get_default_config()
            self.apply_config()
            self.update_config_display()
            self.status_var.set("Configuration reset to defaults")
    
    def get_current_config(self) -> Dict[str, Any]:
        """Get current configuration from GUI"""
        return {
            'can_channel': self.channel_var.get(),
            'can_bitrate': int(self.bitrate_var.get()),
            'servo_id': self.servo_id_var.get(),
            'extended_id': self.extended_id_var.get(),
            'new_can_id_low': self.new_can_id_low_var.get(),
            'new_can_id_high': self.new_can_id_high_var.get(),
            'can_mode': self.can_mode_var.get(),
            'position': self.position_var.get(),
            'read_address': self.read_address_var.get(),
            'custom_id': self.custom_id_var.get(),
            'custom_data': self.custom_data_var.get(),
            'custom_extended': self.custom_extended_var.get()
        }
    
    def apply_config(self, config: Dict[str, Any] = None):
        """Apply configuration to GUI"""
        if config is None:
            config = self.config
        
        # Update GUI variables
        self.channel_var.set(config.get('can_channel', 'PCAN_USBBUS1'))
        self.bitrate_var.set(str(config.get('can_bitrate', 500000)))
        self.servo_id_var.set(str(config.get('servo_id', '0')))
        self.extended_id_var.set(config.get('extended_id', False))
        self.new_can_id_low_var.set(str(config.get('new_can_id_low', '30')))
        self.new_can_id_high_var.set(str(config.get('new_can_id_high', '1478')))
        self.can_mode_var.set(config.get('can_mode', '1'))
        self.position_var.set(str(config.get('position', '1500')))
        self.read_address_var.set(config.get('read_address', '0x32'))
        self.custom_id_var.set(config.get('custom_id', '0x000'))
        self.custom_data_var.set(config.get('custom_data', '72 00 32'))
        self.custom_extended_var.set(config.get('custom_extended', False))
    
    def update_config_display(self):
        """Update configuration display"""
        try:
            config = self.get_current_config()
            config_text = json.dumps(config, indent=2)
            
            self.config_text.delete(1.0, tk.END)
            self.config_text.insert(1.0, config_text)
            
        except Exception as e:
            self.logger.error(f"Error updating config display: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            # Stop monitoring
            if self.is_monitoring:
                self.stop_monitoring()
            
            # Disconnect CAN
            if self.can_interface.is_connected:
                self.disconnect_can()
            
            # Save current configuration
            config = self.get_current_config()
            self.config_manager.save_config(config)
            
            self.logger.info("Application cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
