"""
Hitec CAN Servo Protocol Implementation
Handles servo-specific CAN message formatting and parsing
"""

import struct
import logging
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

class MessageType(Enum):
    """CAN message types for servo protocol"""
    WRITE_SINGLE = ord('w')      # 0x77 - Write single register
    WRITE_DUAL = ord('W')        # 0x57 - Write two registers
    WRITE_SINGLE_READ = ord('x') # 0x78 - Write single then read
    WRITE_DUAL_READ = ord('X')   # 0x58 - Write dual then read
    READ_SINGLE = ord('r')       # 0x72 - Read single register
    READ_DUAL = ord('R')         # 0x52 - Read two registers
    RESPONSE_SINGLE = ord('v')   # 0x76 - Single register response
    RESPONSE_DUAL = ord('V')     # 0x56 - Dual register response

@dataclass
class ServoRegister:
    """Servo register definition"""
    address: int
    name: str
    description: str
    size: int = 2  # bytes
    read_only: bool = False
    min_value: Optional[int] = None
    max_value: Optional[int] = None

class ServoProtocol:
    """Hitec CAN Servo Protocol Handler"""
    
    # Register definitions based on manual
    REGISTERS = {
        # Communication registers
        0x32: ServoRegister(0x32, "SERVO_ID", "Servo Receive ID", read_only=True),
        0x3C: ServoRegister(0x3C, "CAN_ID_HIGH", "CAN ID High Byte"),
        0x3E: ServoRegister(0x3E, "CAN_ID_LOW", "CAN ID Low Byte"),
        0x6A: ServoRegister(0x6A, "CAN_MODE", "CAN Mode Setting"),
        
        # Position and control
        0x0C: ServoRegister(0x0C, "POSITION_NEW", "New Position Command"),
        0x10: ServoRegister(0x10, "POSITION_EXT", "Extended Position"),
        0x60: ServoRegister(0x60, "BAUDRATE", "Baudrate Setting"),
        
        # System control
        0x70: ServoRegister(0x70, "SAVE_RESET", "Save and Reset Command"),
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_write_message(self, servo_id: int, address: int, value: int, 
                           is_extended: bool = False) -> Tuple[int, bytes]:
        """
        Create a write message for single register
        
        Args:
            servo_id: Target servo ID (0-255, 0 for broadcast)
            address: Register address
            value: Value to write (16-bit)
            is_extended: Use extended CAN ID format
            
        Returns:
            Tuple of (arbitration_id, message_data)
        """
        # Pack data: message_type, servo_id, address, value_low, value_high
        data = struct.pack('<BBBBB', 
                          MessageType.WRITE_SINGLE.value,
                          servo_id,
                          address,
                          value & 0xFF,
                          (value >> 8) & 0xFF)
        
        arbitration_id = 0x000 if not is_extended else 0x00000000
        return arbitration_id, data
    
    def create_write_dual_message(self, servo_id: int, address_a: int, value_a: int,
                                address_b: int, value_b: int, is_extended: bool = False) -> Tuple[int, bytes]:
        """
        Create a write message for two registers
        
        Args:
            servo_id: Target servo ID
            address_a: First register address
            value_a: First value to write
            address_b: Second register address  
            value_b: Second value to write
            is_extended: Use extended CAN ID format
            
        Returns:
            Tuple of (arbitration_id, message_data)
        """
        data = struct.pack('<BBBBBBB',
                          MessageType.WRITE_DUAL.value,
                          servo_id,
                          address_a,
                          value_a & 0xFF,
                          (value_a >> 8) & 0xFF,
                          address_b,
                          value_b & 0xFF,
                          (value_b >> 8) & 0xFF)
        
        arbitration_id = 0x000 if not is_extended else 0x00000000
        return arbitration_id, data
    
    def create_read_message(self, servo_id: int, address: int, 
                          is_extended: bool = False) -> Tuple[int, bytes]:
        """
        Create a read request message for single register
        
        Args:
            servo_id: Target servo ID
            address: Register address to read
            is_extended: Use extended CAN ID format
            
        Returns:
            Tuple of (arbitration_id, message_data)
        """
        data = struct.pack('<BBB',
                          MessageType.READ_SINGLE.value,
                          servo_id,
                          address)
        
        arbitration_id = 0x000 if not is_extended else 0x00000000
        return arbitration_id, data
    
    def create_read_dual_message(self, servo_id: int, address_a: int, address_b: int,
                               is_extended: bool = False) -> Tuple[int, bytes]:
        """
        Create a read request message for two registers
        
        Args:
            servo_id: Target servo ID
            address_a: First register address
            address_b: Second register address
            is_extended: Use extended CAN ID format
            
        Returns:
            Tuple of (arbitration_id, message_data)
        """
        data = struct.pack('<BBBB',
                          MessageType.READ_DUAL.value,
                          servo_id,
                          address_a,
                          address_b)
        
        arbitration_id = 0x000 if not is_extended else 0x00000000
        return arbitration_id, data
    
    def create_save_reset_message(self, servo_id: int, is_extended: bool = False) -> Tuple[int, bytes]:
        """
        Create save and reset command message
        
        Args:
            servo_id: Target servo ID
            is_extended: Use extended CAN ID format
            
        Returns:
            Tuple of (arbitration_id, message_data)
        """
        # Save and reset command: write 0xFFFF to register 0x70
        return self.create_write_message(servo_id, 0x70, 0xFFFF, is_extended)
    
    def create_set_can_id_message(self, servo_id: int, new_can_id: int, 
                                is_extended: bool = False) -> List[Tuple[int, bytes]]:
        """
        Create messages to set servo CAN ID
        
        Args:
            servo_id: Current servo ID
            new_can_id: New CAN ID to set
            is_extended: Use extended CAN ID format
            
        Returns:
            List of (arbitration_id, message_data) tuples
        """
        messages = []
        
        # Set CAN ID Low (address 0x3E)
        can_id_low = new_can_id & 0xFF
        msg_low = self.create_write_message(servo_id, 0x3E, can_id_low, is_extended)
        messages.append(msg_low)
        
        # Set CAN ID High (address 0x3C) if needed
        can_id_high = (new_can_id >> 8) & 0xFF
        if can_id_high > 0:
            msg_high = self.create_write_message(servo_id, 0x3C, can_id_high, is_extended)
            messages.append(msg_high)
        
        return messages
    
    def create_set_can_mode_message(self, servo_id: int, mode: int, 
                                  is_extended: bool = False) -> Tuple[int, bytes]:
        """
        Create message to set CAN mode
        
        Args:
            servo_id: Target servo ID
            mode: CAN mode value (0=Standard, 1=Extended)
            is_extended: Use extended CAN ID format
            
        Returns:
            Tuple of (arbitration_id, message_data)
        """
        return self.create_write_message(servo_id, 0x6A, mode, is_extended)
    
    def create_position_command(self, servo_id: int, position: int, 
                              is_extended: bool = False) -> Tuple[int, bytes]:
        """
        Create position command message
        
        Args:
            servo_id: Target servo ID
            position: Position value
            is_extended: Use extended CAN ID format
            
        Returns:
            Tuple of (arbitration_id, message_data)
        """
        return self.create_write_message(servo_id, 0x0C, position, is_extended)
    
    def parse_response_message(self, data: bytes) -> Optional[Dict]:
        """
        Parse a response message from servo
        
        Args:
            data: Message data bytes
            
        Returns:
            Dictionary with parsed data or None if invalid
        """
        try:
            if len(data) < 3:
                return None
            
            message_type = data[0]
            servo_id = data[1]
            
            if message_type == MessageType.RESPONSE_SINGLE.value:
                if len(data) < 5:
                    return None
                
                address = data[2]
                value = struct.unpack('<H', data[3:5])[0]
                
                return {
                    'type': 'single_response',
                    'servo_id': servo_id,
                    'address': address,
                    'value': value,
                    'register_name': self.REGISTERS.get(address, ServoRegister(address, f"ADDR_{address:02X}", "Unknown")).name
                }
            
            elif message_type == MessageType.RESPONSE_DUAL.value:
                if len(data) < 8:
                    return None
                
                address_a = data[2]
                value_a = struct.unpack('<H', data[3:5])[0]
                address_b = data[5]
                value_b = struct.unpack('<H', data[6:8])[0]
                
                return {
                    'type': 'dual_response',
                    'servo_id': servo_id,
                    'address_a': address_a,
                    'value_a': value_a,
                    'address_b': address_b,
                    'value_b': value_b,
                    'register_name_a': self.REGISTERS.get(address_a, ServoRegister(address_a, f"ADDR_{address_a:02X}", "Unknown")).name,
                    'register_name_b': self.REGISTERS.get(address_b, ServoRegister(address_b, f"ADDR_{address_b:02X}", "Unknown")).name
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error parsing response message: {e}")
            return None
    
    def create_old_format_write(self, servo_id: int, address: int, value: int) -> Tuple[int, bytes]:
        """
        Create write message using old packet format (for compatibility)
        
        Args:
            servo_id: Target servo ID
            address: Register address
            value: Value to write
            
        Returns:
            Tuple of (arbitration_id, message_data)
        """
        # Old format: Header(0x96), ID, Address, REG Length(0x02), Data Low, Data High, Checksum
        data_low = value & 0xFF
        data_high = (value >> 8) & 0xFF
        checksum = (servo_id + address + 0x02 + data_low + data_high) & 0xFF
        
        data = struct.pack('<BBBBBBB',
                          0x96,        # Write header
                          servo_id,    # Servo ID
                          address,     # Register address
                          0x02,        # REG length
                          data_low,    # Data low byte
                          data_high,   # Data high byte
                          checksum)    # Checksum
        
        return 0x000, data
    
    def create_old_format_read(self, servo_id: int, address: int) -> Tuple[int, bytes]:
        """
        Create read request using old packet format (for compatibility)
        
        Args:
            servo_id: Target servo ID
            address: Register address to read
            
        Returns:
            Tuple of (arbitration_id, message_data)
        """
        # Old format: Header(0x96), ID, Address, REG Length(0x00), Checksum
        checksum = (servo_id + address + 0x00) & 0xFF
        
        data = struct.pack('<BBBBB',
                          0x96,        # Read header
                          servo_id,    # Servo ID
                          address,     # Register address
                          0x00,        # REG length (0 for read)
                          checksum)    # Checksum
        
        return 0x000, data
    
    def get_register_info(self, address: int) -> ServoRegister:
        """Get register information by address"""
        return self.REGISTERS.get(address, 
                                ServoRegister(address, f"ADDR_{address:02X}", "Unknown Register"))
    
    def get_all_registers(self) -> Dict[int, ServoRegister]:
        """Get all defined registers"""
        return self.REGISTERS.copy()
    
    def validate_servo_id(self, servo_id: int) -> bool:
        """Validate servo ID range"""
        return 0 <= servo_id <= 255
    
    def validate_register_address(self, address: int) -> bool:
        """Validate register address (must be even)"""
        return 0 <= address <= 0xFF and address % 2 == 0
    
    def validate_register_value(self, address: int, value: int) -> bool:
        """Validate register value range"""
        if address in self.REGISTERS:
            reg = self.REGISTERS[address]
            if reg.min_value is not None and value < reg.min_value:
                return False
            if reg.max_value is not None and value > reg.max_value:
                return False
        
        return 0 <= value <= 0xFFFF
