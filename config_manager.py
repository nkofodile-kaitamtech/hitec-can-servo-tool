"""
Configuration Manager for Hitec CAN Servo Programming Tool
Handles saving/loading application settings
"""

import json
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

class ConfigManager:
    """Configuration management class"""
    
    def __init__(self, config_file: str = "servo_config.json"):
        self.config_file = config_file
        self.logger = logging.getLogger(__name__)
        
        # Default configuration
        self.default_config = {
            'can_channel': 'PCAN_USBBUS1',
            'can_bitrate': 500000,
            'servo_id': '0',
            'extended_id': False,
            'new_can_id': '49',
            'can_mode': '1 - Extended',
            'position': '1500',
            'read_address': '0x32',
            'custom_id': '0x000',
            'custom_data': '72 00 32',
            'custom_extended': False,
            'window_geometry': '1200x800',
            'last_log_directory': '',
            'auto_connect': False,
            'message_display_limit': 1000,
            'log_level': 'INFO'
        }
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return self.default_config.copy()
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file
        
        Returns:
            Configuration dictionary
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                
                # Merge with defaults to ensure all keys exist
                merged_config = self.default_config.copy()
                merged_config.update(config)
                
                self.logger.info(f"Configuration loaded from {self.config_file}")
                return merged_config
            else:
                self.logger.info("No configuration file found, using defaults")
                return self.default_config.copy()
                
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            self.logger.info("Using default configuration")
            return self.default_config.copy()
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        Save configuration to file
        
        Args:
            config: Configuration dictionary to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create backup of existing config
            if os.path.exists(self.config_file):
                backup_file = f"{self.config_file}.backup"
                with open(self.config_file, 'r') as src, open(backup_file, 'w') as dst:
                    dst.write(src.read())
            
            # Save new configuration
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.logger.info(f"Configuration saved to {self.config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False
    
    def load_config_from_file(self, filename: str) -> Dict[str, Any]:
        """
        Load configuration from specific file
        
        Args:
            filename: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        try:
            with open(filename, 'r') as f:
                config = json.load(f)
            
            # Validate configuration
            validated_config = self.validate_config(config)
            
            self.logger.info(f"Configuration loaded from {filename}")
            return validated_config
            
        except Exception as e:
            self.logger.error(f"Error loading configuration from {filename}: {e}")
            raise
    
    def save_config_to_file(self, config: Dict[str, Any], filename: str) -> bool:
        """
        Save configuration to specific file
        
        Args:
            config: Configuration dictionary to save
            filename: Path to save configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate configuration before saving
            validated_config = self.validate_config(config)
            
            with open(filename, 'w') as f:
                json.dump(validated_config, f, indent=2)
            
            self.logger.info(f"Configuration saved to {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving configuration to {filename}: {e}")
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize configuration
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            Validated configuration dictionary
        """
        validated = self.default_config.copy()
        
        try:
            # Validate CAN settings
            if 'can_channel' in config and isinstance(config['can_channel'], str):
                validated['can_channel'] = config['can_channel']
            
            if 'can_bitrate' in config:
                bitrate = int(config['can_bitrate'])
                if bitrate in [125000, 250000, 500000, 1000000]:
                    validated['can_bitrate'] = bitrate
            
            # Validate servo settings
            if 'servo_id' in config:
                servo_id = str(config['servo_id'])
                validated['servo_id'] = servo_id
            
            if 'extended_id' in config and isinstance(config['extended_id'], bool):
                validated['extended_id'] = config['extended_id']
            
            if 'new_can_id' in config:
                validated['new_can_id'] = str(config['new_can_id'])
            
            if 'can_mode' in config and isinstance(config['can_mode'], str):
                validated['can_mode'] = config['can_mode']
            
            if 'position' in config:
                validated['position'] = str(config['position'])
            
            if 'read_address' in config:
                validated['read_address'] = str(config['read_address'])
            
            # Validate custom message settings
            if 'custom_id' in config:
                validated['custom_id'] = str(config['custom_id'])
            
            if 'custom_data' in config and isinstance(config['custom_data'], str):
                validated['custom_data'] = config['custom_data']
            
            if 'custom_extended' in config and isinstance(config['custom_extended'], bool):
                validated['custom_extended'] = config['custom_extended']
            
            # Validate UI settings
            if 'window_geometry' in config and isinstance(config['window_geometry'], str):
                validated['window_geometry'] = config['window_geometry']
            
            if 'last_log_directory' in config and isinstance(config['last_log_directory'], str):
                validated['last_log_directory'] = config['last_log_directory']
            
            if 'auto_connect' in config and isinstance(config['auto_connect'], bool):
                validated['auto_connect'] = config['auto_connect']
            
            if 'message_display_limit' in config:
                limit = int(config['message_display_limit'])
                if 100 <= limit <= 10000:
                    validated['message_display_limit'] = limit
            
            if 'log_level' in config and config['log_level'] in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
                validated['log_level'] = config['log_level']
            
        except Exception as e:
            self.logger.warning(f"Error validating configuration: {e}")
        
        return validated
    
    def export_config(self, config: Dict[str, Any], filename: str, include_metadata: bool = True) -> bool:
        """
        Export configuration with metadata
        
        Args:
            config: Configuration to export
            filename: Export filename
            include_metadata: Include metadata in export
            
        Returns:
            True if successful, False otherwise
        """
        try:
            export_data = {
                'configuration': config
            }
            
            if include_metadata:
                export_data['metadata'] = {
                    'exported_at': str(datetime.now()),
                    'application': 'Hitec CAN Servo Programming Tool',
                    'version': '1.0.0',
                    'config_version': '1.0'
                }
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            self.logger.info(f"Configuration exported to {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting configuration: {e}")
            return False
    
    def import_config(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Import configuration with metadata support
        
        Args:
            filename: Import filename
            
        Returns:
            Configuration dictionary or None if failed
        """
        try:
            with open(filename, 'r') as f:
                import_data = json.load(f)
            
            # Check if it's a metadata format or plain config
            if 'configuration' in import_data:
                config = import_data['configuration']
                
                # Log metadata if available
                if 'metadata' in import_data:
                    metadata = import_data['metadata']
                    self.logger.info(f"Importing config from {metadata.get('application', 'Unknown')} "
                                   f"v{metadata.get('version', 'Unknown')}")
            else:
                # Assume it's a plain configuration
                config = import_data
            
            validated_config = self.validate_config(config)
            self.logger.info(f"Configuration imported from {filename}")
            return validated_config
            
        except Exception as e:
            self.logger.error(f"Error importing configuration: {e}")
            return None
    
    def reset_to_defaults(self) -> Dict[str, Any]:
        """
        Reset configuration to defaults
        
        Returns:
            Default configuration dictionary
        """
        self.logger.info("Configuration reset to defaults")
        return self.default_config.copy()
    
    def create_profile(self, profile_name: str, config: Dict[str, Any]) -> bool:
        """
        Create a named configuration profile
        
        Args:
            profile_name: Name of the profile
            config: Configuration to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            profiles_dir = "profiles"
            if not os.path.exists(profiles_dir):
                os.makedirs(profiles_dir)
            
            profile_file = os.path.join(profiles_dir, f"{profile_name}.json")
            return self.save_config_to_file(config, profile_file)
            
        except Exception as e:
            self.logger.error(f"Error creating profile {profile_name}: {e}")
            return False
    
    def load_profile(self, profile_name: str) -> Optional[Dict[str, Any]]:
        """
        Load a named configuration profile
        
        Args:
            profile_name: Name of the profile to load
            
        Returns:
            Configuration dictionary or None if failed
        """
        try:
            profile_file = os.path.join("profiles", f"{profile_name}.json")
            return self.load_config_from_file(profile_file)
            
        except Exception as e:
            self.logger.error(f"Error loading profile {profile_name}: {e}")
            return None
    
    def get_available_profiles(self) -> List[str]:
        """
        Get list of available configuration profiles
        
        Returns:
            List of profile names
        """
        try:
            profiles_dir = "profiles"
            if not os.path.exists(profiles_dir):
                return []
            
            profiles = []
            for filename in os.listdir(profiles_dir):
                if filename.endswith('.json'):
                    profiles.append(filename[:-5])  # Remove .json extension
            
            return sorted(profiles)
            
        except Exception as e:
            self.logger.error(f"Error getting available profiles: {e}")
            return []
