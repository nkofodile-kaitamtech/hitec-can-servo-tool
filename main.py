#!/usr/bin/env python3
"""
Main entry point for Hitec CAN Servo Programming Tool
"""

import tkinter as tk
from tkinter import messagebox
import sys
import os
import logging
from gui_main import ServoControlGUI

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('servo_control.log'),
            logging.StreamHandler()
        ]
    )

def main():
    """Main application entry point"""
    try:
        # Setup logging
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("Starting Hitec CAN Servo Programming Tool")
        
        # Create main application window
        root = tk.Tk()
        root.title("Hitec CAN Servo Programming Tool")
        root.geometry("1200x800")
        root.minsize(800, 600)
        
        # Set application icon (using built-in icon)
        try:
            root.iconbitmap(default='')
        except:
            pass  # Ignore if no icon available
        
        # Create main application
        app = ServoControlGUI(root)
        
        # Handle window closing
        def on_closing():
            if messagebox.askokcancel("Quit", "Do you want to quit?"):
                app.cleanup()
                root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Start the GUI
        logger.info("GUI initialized, starting main loop")
        root.mainloop()
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Application startup failed: {e}")
        messagebox.showerror("Startup Error", f"Failed to start application:\n{e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
