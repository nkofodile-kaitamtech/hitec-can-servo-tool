# Hitec CAN Servo Programming Tool

## Overview

This is a Python-based GUI application for programming and controlling Hitec CAN servos. The application provides a user-friendly interface for sending CAN messages, reading servo registers, configuring servo parameters, and monitoring CAN bus traffic. It uses the PCAN interface for CAN communication and implements the Hitec-specific servo protocol.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes (July 28, 2025)

- Modified CAN interface selection to start empty and prompt user to select from available interfaces
- Added placeholder text "Select CAN Interface..." when no interface is chosen  
- Improved channel detection with helpful user guidance and error messages
- Added validation to prevent connection attempts without proper interface selection
- Enhanced connection info display with step-by-step getting started guide

## System Architecture

The application follows a modular architecture with clear separation of concerns:

- **GUI Layer**: Tkinter-based user interface (`gui_main.py`)
- **Protocol Layer**: Servo-specific CAN message handling (`servo_protocol.py`)
- **Communication Layer**: Low-level CAN interface abstraction (`can_interface.py`)
- **Configuration Layer**: Settings persistence and management (`config_manager.py`)
- **Utility Layer**: Helper functions for data formatting and validation (`utils.py`)

The architecture promotes maintainability by isolating hardware communication, protocol implementation, and user interface components.

## Key Components

### CAN Interface (`can_interface.py`)
- Wraps the python-can library for PCAN hardware communication
- Provides thread-safe message transmission and reception
- Implements callback-based message handling for real-time monitoring
- Uses a message queue system to buffer incoming CAN messages

### Servo Protocol (`servo_protocol.py`)
- Implements Hitec-specific CAN servo protocol
- Defines register mappings and message types
- Handles message encoding/decoding for servo commands
- Supports various operation modes (read, write, configuration)

### GUI Main (`gui_main.py`)
- Main application window built with Tkinter
- Provides controls for servo configuration and monitoring
- Implements real-time CAN message display
- Handles user interactions and validates input data

### Configuration Manager (`config_manager.py`)
- Persists application settings to JSON files
- Manages default configuration values
- Provides configuration validation and migration capabilities

### Utilities (`utils.py`)
- Helper functions for hex data formatting and parsing
- Input validation for numeric and hex values
- Common utility functions used across modules

## Data Flow

1. **User Input**: User interacts with GUI controls to configure servo parameters
2. **Protocol Encoding**: Servo protocol layer encodes user commands into CAN messages
3. **CAN Transmission**: CAN interface transmits messages to the servo via PCAN hardware
4. **Message Reception**: Incoming CAN messages are captured and queued
5. **Protocol Decoding**: Received messages are decoded by the servo protocol layer
6. **GUI Update**: Decoded data is displayed in the user interface

The application uses a callback-based architecture for handling incoming CAN messages, ensuring responsive real-time monitoring.

## External Dependencies

### Hardware Dependencies
- **PCAN Interface**: Requires PCAN USB adapter or similar hardware for CAN bus communication
- **CAN Bus**: Physical CAN network with connected Hitec servos

### Software Dependencies
- **python-can**: Core CAN communication library
- **tkinter**: Built-in Python GUI framework
- **threading**: For concurrent message handling and GUI responsiveness

### Protocol Dependencies
- **Hitec CAN Protocol**: Implements proprietary Hitec servo communication protocol
- **CAN 2.0**: Standard CAN bus protocol support

## Deployment Strategy

### Development Environment
- Python 3.x required with standard library support
- No external database requirements
- Configuration stored in local JSON files
- Logging to local files and console

### Hardware Requirements
- Windows/Linux system with USB support
- PCAN USB interface adapter
- CAN bus network with Hitec servos

### Installation Approach
- Standalone Python application
- Dependencies managed via pip/requirements
- No complex deployment infrastructure needed
- Portable configuration through JSON files

### Runtime Considerations
- Real-time CAN communication requires low-latency system
- Thread-safe implementation for concurrent operations
- Graceful handling of hardware disconnection
- Automatic configuration persistence between sessions

The application is designed as a desktop tool for servo technicians and engineers, prioritizing ease of use and reliable hardware communication over complex deployment scenarios.