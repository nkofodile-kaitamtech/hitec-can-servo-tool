"""
Utility functions for Hitec CAN Servo Programming Tool
"""

import re
import logging
from typing import List, Union, Optional

def format_hex_bytes(data: bytes) -> str:
    """
    Format bytes as hex string
    
    Args:
        data: Bytes to format
        
    Returns:
        Formatted hex string (e.g., "AB CD EF")
    """
    return ' '.join(f'{b:02X}' for b in data)

def parse_hex_input(hex_string: str) -> bytes:
    """
    Parse hex input string to bytes
    
    Args:
        hex_string: Hex string input (e.g., "AB CD EF" or "ABCDEF")
        
    Returns:
        Parsed bytes
        
    Raises:
        ValueError: If input is invalid
    """
    # Remove whitespace and normalize
    hex_string = re.sub(r'\s+', '', hex_string.strip())
    
    # Remove common prefixes
    if hex_string.startswith('0x'):
        hex_string = hex_string[2:]
    
    # Ensure even length
    if len(hex_string) % 2 != 0:
        hex_string = '0' + hex_string
    
    # Validate hex characters
    if not re.match(r'^[0-9A-Fa-f]*$', hex_string):
        raise ValueError("Invalid hex characters in input")
    
    # Convert to bytes
    try:
        return bytes.fromhex(hex_string)
    except ValueError as e:
        raise ValueError(f"Failed to parse hex string: {e}")

def validate_numeric_input(value: str, min_val: Optional[int] = None, max_val: Optional[int] = None, 
                          allow_hex: bool = True) -> int:
    """
    Validate and convert numeric input
    
    Args:
        value: Input string
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        allow_hex: Allow hex format (0x prefix)
        
    Returns:
        Converted integer value
        
    Raises:
        ValueError: If input is invalid
    """
    try:
        # Handle hex format
        if allow_hex and value.startswith('0x'):
            result = int(value, 16)
        else:
            result = int(value)
        
        # Validate range
        if min_val is not None and result < min_val:
            raise ValueError(f"Value {result} is below minimum {min_val}")
        
        if max_val is not None and result > max_val:
            raise ValueError(f"Value {result} is above maximum {max_val}")
        
        return result
        
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError(f"Invalid numeric format: {value}")
        raise

def format_can_id(can_id: int, is_extended: bool = False) -> str:
    """
    Format CAN ID for display
    
    Args:
        can_id: CAN ID value
        is_extended: True for extended (29-bit) ID
        
    Returns:
        Formatted CAN ID string
    """
    if is_extended:
        return f"0x{can_id:08X}"
    else:
        return f"0x{can_id:03X}"

def parse_can_id(id_string: str) -> tuple[int, bool]:
    """
    Parse CAN ID string and determine if extended
    
    Args:
        id_string: CAN ID string (e.g., "0x123" or "0x12345678")
        
    Returns:
        Tuple of (can_id, is_extended)
        
    Raises:
        ValueError: If input is invalid
    """
    try:
        # Remove whitespace
        id_string = id_string.strip()
        
        # Parse hex value
        if id_string.startswith('0x'):
            can_id = int(id_string, 16)
        else:
            can_id = int(id_string)
        
        # Determine if extended based on value
        if can_id > 0x7FF:  # Standard CAN ID max is 0x7FF (11 bits)
            is_extended = True
            if can_id > 0x1FFFFFFF:  # Extended CAN ID max is 0x1FFFFFFF (29 bits)
                raise ValueError(f"CAN ID 0x{can_id:X} exceeds maximum extended ID")
        else:
            is_extended = False
        
        return can_id, is_extended
        
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError(f"Invalid CAN ID format: {id_string}")
        raise

def calculate_checksum(data: List[int]) -> int:
    """
    Calculate checksum for old protocol format
    
    Args:
        data: List of byte values
        
    Returns:
        Checksum value (8-bit)
    """
    return sum(data) & 0xFF

def validate_servo_id(servo_id: int) -> bool:
    """
    Validate servo ID range
    
    Args:
        servo_id: Servo ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    return 0 <= servo_id <= 255

def validate_register_address(address: int) -> bool:
    """
    Validate register address (must be even)
    
    Args:
        address: Register address to validate
        
    Returns:
        True if valid, False otherwise
    """
    return 0 <= address <= 0xFF and address % 2 == 0

def format_register_value(value: int, reg_name: str = "") -> str:
    """
    Format register value for display
    
    Args:
        value: Register value
        reg_name: Register name for context
        
    Returns:
        Formatted value string
    """
    # Special formatting for known registers
    if reg_name in ["CAN_ID_HIGH", "CAN_ID_LOW"]:
        return f"0x{value:02X} ({value})"
    elif reg_name == "CAN_MODE":
        mode_names = {0: "Standard", 1: "Extended"}
        return f"{value} ({mode_names.get(value, 'Unknown')})"
    elif reg_name in ["POSITION_NEW", "POSITION_EXT"]:
        return f"{value} μs"
    else:
        return f"0x{value:04X} ({value})"

def create_message_description(msg_type: int, data: bytes) -> str:
    """
    Create human-readable description of CAN message
    
    Args:
        msg_type: Message type byte
        data: Message data bytes
        
    Returns:
        Description string
    """
    descriptions = {
        0x77: "Write Single Register",
        0x57: "Write Dual Register", 
        0x78: "Write Single + Read",
        0x58: "Write Dual + Read",
        0x72: "Read Single Register",
        0x52: "Read Dual Register",
        0x76: "Single Register Response",
        0x56: "Dual Register Response",
        0x96: "Old Format Message"
    }
    
    base_desc = descriptions.get(msg_type, "Unknown Message")
    
    # Add additional context if possible
    if len(data) >= 3:
        servo_id = data[1]
        address = data[2]
        return f"{base_desc} (Servo {servo_id}, Addr 0x{address:02X})"
    
    return base_desc

def log_can_message(logger: logging.Logger, direction: str, can_id: int, 
                   data: bytes, is_extended: bool = False):
    """
    Log CAN message with formatted output
    
    Args:
        logger: Logger instance
        direction: "TX" or "RX"
        can_id: CAN message ID
        data: Message data
        is_extended: Extended ID flag
    """
    id_str = format_can_id(can_id, is_extended)
    data_str = format_hex_bytes(data)
    
    # Try to decode message type
    description = ""
    if len(data) > 0:
        description = f" - {create_message_description(data[0], data)}"
    
    logger.debug(f"{direction}: {id_str} [{len(data)}] {data_str}{description}")

def convert_position_to_microseconds(position: int, min_us: int = 500, max_us: int = 2500) -> int:
    """
    Convert position value to microseconds
    
    Args:
        position: Position value (typically 0-4095 or similar)
        min_us: Minimum pulse width in microseconds
        max_us: Maximum pulse width in microseconds
        
    Returns:
        Position in microseconds
    """
    # Assume position is in standard servo range (500-2500 μs)
    # This is a placeholder - actual conversion depends on servo specs
    if 500 <= position <= 2500:
        return position  # Already in microseconds
    else:
        # Scale from 0-4095 to min_us-max_us range
        return int(min_us + (position / 4095.0) * (max_us - min_us))

def convert_microseconds_to_position(microseconds: int, min_us: int = 500, max_us: int = 2500) -> int:
    """
    Convert microseconds to position value
    
    Args:
        microseconds: Position in microseconds
        min_us: Minimum pulse width in microseconds
        max_us: Maximum pulse width in microseconds
        
    Returns:
        Position value
    """
    if min_us <= microseconds <= max_us:
        # Convert to 0-4095 range
        return int((microseconds - min_us) / (max_us - min_us) * 4095)
    else:
        return microseconds  # Assume already in correct format

def create_can_frame_summary(can_id: int, data: bytes, is_extended: bool = False) -> str:
    """
    Create a summary string for a CAN frame
    
    Args:
        can_id: CAN ID
        data: Frame data
        is_extended: Extended ID flag
        
    Returns:
        Summary string
    """
    id_str = format_can_id(can_id, is_extended)
    data_str = format_hex_bytes(data)
    ext_str = " (Ext)" if is_extended else ""
    
    return f"ID: {id_str}{ext_str}, Data: [{data_str}], Length: {len(data)}"

def validate_can_bitrate(bitrate: int) -> bool:
    """
    Validate CAN bitrate
    
    Args:
        bitrate: Bitrate in bps
        
    Returns:
        True if valid, False otherwise
    """
    valid_bitrates = [125000, 250000, 500000, 1000000]
    return bitrate in valid_bitrates

def format_timestamp(timestamp: float) -> str:
    """
    Format timestamp for display
    
    Args:
        timestamp: Unix timestamp
        
    Returns:
        Formatted timestamp string
    """
    from datetime import datetime
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime('%H:%M:%S.%f')[:-3]  # Include milliseconds

def safe_int_conversion(value: str, default: int = 0) -> int:
    """
    Safely convert string to integer with default
    
    Args:
        value: String value to convert
        default: Default value if conversion fails
        
    Returns:
        Converted integer or default
    """
    try:
        if value.startswith('0x'):
            return int(value, 16)
        return int(value)
    except (ValueError, AttributeError):
        return default
