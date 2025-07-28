"""
CAN Interface module for PCAN communication
Handles low-level CAN bus operations using python-can library
"""

import can
import threading
import time
import logging
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass
from queue import Queue, Empty

@dataclass
class CANMessage:
    """CAN message data structure"""
    arbitration_id: int
    data: bytes
    is_extended_id: bool = False
    timestamp: float = 0.0
    is_error_frame: bool = False

class CANInterface:
    """PCAN interface wrapper using python-can library"""
    
    def __init__(self, channel: str = 'PCAN_USBBUS1', bitrate: int = 500000):
        """
        Initialize CAN interface
        
        Args:
            channel: PCAN channel (e.g., 'PCAN_USBBUS1')
            bitrate: CAN bus bitrate in bps
        """
        self.logger = logging.getLogger(__name__)
        self.channel = channel
        self.bitrate = bitrate
        self.bus: Optional[can.Bus] = None
        self.is_connected = False
        self.receive_thread: Optional[threading.Thread] = None
        self.stop_receive = threading.Event()
        self.message_callbacks: List[Callable[[CANMessage], None]] = []
        self.received_messages = Queue(maxsize=1000)
        self.lock = threading.Lock()
        
    def connect(self) -> bool:
        """
        Connect to PCAN interface
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Connecting to {self.channel} at {self.bitrate} bps")
            
            # Initialize CAN bus using python-can with PCAN interface
            self.bus = can.Bus(
                interface='pcan',
                channel=self.channel,
                bitrate=self.bitrate,
                receive_own_messages=False
            )
            
            self.is_connected = True
            self.logger.info("CAN interface connected successfully")
            
            # Start receive thread
            self.start_receive_thread()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to CAN interface: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Disconnect from CAN interface"""
        try:
            self.logger.info("Disconnecting CAN interface")
            
            # Stop receive thread
            self.stop_receive_thread()
            
            # Close bus connection
            if self.bus:
                self.bus.shutdown()
                self.bus = None
            
            self.is_connected = False
            self.logger.info("CAN interface disconnected")
            
        except Exception as e:
            self.logger.error(f"Error during disconnect: {e}")
    
    def start_receive_thread(self):
        """Start the message receive thread"""
        if self.receive_thread and self.receive_thread.is_alive():
            return
        
        self.stop_receive.clear()
        self.receive_thread = threading.Thread(target=self._receive_worker, daemon=True)
        self.receive_thread.start()
        self.logger.debug("Receive thread started")
    
    def stop_receive_thread(self):
        """Stop the message receive thread"""
        if self.receive_thread and self.receive_thread.is_alive():
            self.stop_receive.set()
            self.receive_thread.join(timeout=2.0)
            self.logger.debug("Receive thread stopped")
    
    def _receive_worker(self):
        """Worker thread for receiving CAN messages"""
        self.logger.debug("Receive worker started")
        
        while not self.stop_receive.is_set() and self.is_connected:
            try:
                if not self.bus:
                    break
                
                # Receive message with timeout
                msg = self.bus.recv(timeout=0.1)
                if msg is None:
                    continue
                
                # Convert to our message format
                can_msg = CANMessage(
                    arbitration_id=msg.arbitration_id,
                    data=msg.data,
                    is_extended_id=msg.is_extended_id,
                    timestamp=msg.timestamp,
                    is_error_frame=msg.is_error_frame
                )
                
                # Add to queue
                try:
                    self.received_messages.put_nowait(can_msg)
                except:
                    # Queue full, remove oldest message
                    try:
                        self.received_messages.get_nowait()
                        self.received_messages.put_nowait(can_msg)
                    except:
                        pass
                
                # Notify callbacks
                with self.lock:
                    for callback in self.message_callbacks:
                        try:
                            callback(can_msg)
                        except Exception as e:
                            self.logger.error(f"Error in message callback: {e}")
                
            except Exception as e:
                if self.is_connected:
                    self.logger.error(f"Error in receive worker: {e}")
                time.sleep(0.01)
        
        self.logger.debug("Receive worker stopped")
    
    def send_message(self, arbitration_id: int, data: bytes, is_extended_id: bool = False) -> bool:
        """
        Send a CAN message
        
        Args:
            arbitration_id: CAN message ID
            data: Message data bytes
            is_extended_id: True for 29-bit extended ID, False for 11-bit standard ID
            
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            if not self.is_connected or not self.bus:
                self.logger.error("CAN interface not connected")
                return False
            
            # Create CAN message
            msg = can.Message(
                arbitration_id=arbitration_id,
                data=data,
                is_extended_id=is_extended_id
            )
            
            # Send message
            self.bus.send(msg)
            self.logger.debug(f"Sent CAN message: ID=0x{arbitration_id:X}, Data={data.hex()}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send CAN message: {e}")
            return False
    
    def add_message_callback(self, callback: Callable[[CANMessage], None]):
        """Add a callback for received messages"""
        with self.lock:
            if callback not in self.message_callbacks:
                self.message_callbacks.append(callback)
    
    def remove_message_callback(self, callback: Callable[[CANMessage], None]):
        """Remove a message callback"""
        with self.lock:
            if callback in self.message_callbacks:
                self.message_callbacks.remove(callback)
    
    def get_received_messages(self, max_count: int = 100) -> List[CANMessage]:
        """Get received messages from queue"""
        messages = []
        count = 0
        
        while count < max_count:
            try:
                msg = self.received_messages.get_nowait()
                messages.append(msg)
                count += 1
            except Empty:
                break
        
        return messages
    
    def clear_received_messages(self):
        """Clear the received message queue"""
        while True:
            try:
                self.received_messages.get_nowait()
            except Empty:
                break
    
    def get_available_channels(self) -> List[str]:
        """Get list of available PCAN channels"""
        channels = []
        
        # Common PCAN channel names
        pcan_channels = [
            'PCAN_USBBUS1', 'PCAN_USBBUS2', 'PCAN_USBBUS3', 'PCAN_USBBUS4',
            'PCAN_USBBUS5', 'PCAN_USBBUS6', 'PCAN_USBBUS7', 'PCAN_USBBUS8',
            'PCAN_PCIBUS1', 'PCAN_PCIBUS2', 'PCAN_PCIBUS3', 'PCAN_PCIBUS4'
        ]
        
        for channel in pcan_channels:
            try:
                # Try to create bus instance to check availability
                test_bus = can.Bus(interface='pcan', channel=channel, bitrate=500000)
                test_bus.shutdown()
                channels.append(channel)
                self.logger.debug(f"Found available PCAN channel: {channel}")
            except Exception as e:
                self.logger.debug(f"Channel {channel} not available: {e}")
                continue
        
        self.logger.info(f"Detected {len(channels)} available PCAN channels")
        return channels  # Return empty list if no channels found
    
    def get_status(self) -> Dict[str, Any]:
        """Get interface status information"""
        return {
            'connected': self.is_connected,
            'channel': self.channel,
            'bitrate': self.bitrate,
            'messages_received': self.received_messages.qsize(),
            'receive_thread_active': self.receive_thread.is_alive() if self.receive_thread else False
        }
