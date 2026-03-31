"""
FaceUnlock GUI
Provides a graphical user interface for face registration and unlock.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import cv2
import pickle
import numpy as np
from pathlib import Path
import logging

from config import config, PROFILE_PATH
from register import register_face
from unlock import FaceUnlock
from windows_bridge import is_screen_locked, check_dependencies

# ── Setup Logging ──────────────────────────────────────────────────────
logger = logging.getLogger('FaceUnlock.GUI')


class FaceUnlockGUI:
    """Graphical user interface for FaceUnlock."""
    
    def __init__(self, root):
        """
        Initialize the GUI.
        
        Args:
            root: Tkinter root window
        """
        self.root = root
        self.root.title("FaceUnlock")
        self.root.geometry("600x700")
        self.root.resizable(True, True)
        
        # State
        self.unlock_thread = None
        self.is_running = False
        self.face_unlock = None
        
        # Setup UI
        self._setup_styles()
        self._create_widgets()
        self._load_status()
    
    def _setup_styles(self):
        """Configure ttk styles."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        style.configure('Title.TLabel', font=('Helvetica', 16, 'bold'))
        style.configure('Status.TLabel', font=('Helvetica', 10))
        style.configure('Success.TLabel', foreground='green', font=('Helvetica', 10, 'bold'))
        style.configure('Error.TLabel', foreground='red', font=('Helvetica', 10, 'bold'))
        style.configure('Warning.TLabel', foreground='orange', font=('Helvetica', 10, 'bold'))
    
    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main container with scrollbar
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="FaceUnlock", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Status Section
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)
        
        # Profile status
        ttk.Label(status_frame, text="Face Profile:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.profile_status = ttk.Label(status_frame, text="Checking...", style='Status.TLabel')
        self.profile_status.grid(row=0, column=1, sticky=tk.W)
        
        # Camera status
        ttk.Label(status_frame, text="Camera:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.camera_status = ttk.Label(status_frame, text="Checking...", style='Status.TLabel')
        self.camera_status.grid(row=1, column=1, sticky=tk.W)
        
        # Lock screen status
        ttk.Label(status_frame, text="Lock Screen:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        self.lock_status = ttk.Label(status_frame, text="Checking...", style='Status.TLabel')
        self.lock_status.grid(row=2, column=1, sticky=tk.W)
        
        # Service status
        ttk.Label(status_frame, text="Service:").grid(row=3, column=0, sticky=tk.W, padx=(0, 10))
        self.service_status = ttk.Label(status_frame, text="Stopped", style='Status.TLabel')
        self.service_status.grid(row=3, column=1, sticky=tk.W)
        
        # Registration Section
        reg_frame = ttk.LabelFrame(main_frame, text="Face Registration", padding="10")
        reg_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        reg_frame.columnconfigure(1, weight=1)
        
        ttk.Label(reg_frame, text="Register your face to enable unlock.").grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        self.register_btn = ttk.Button(reg_frame, text="Register Face", command=self._start_registration)
        self.register_btn.grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        
        self.re_register_btn = ttk.Button(reg_frame, text="Re-register", command=self._start_registration)
        self.re_register_btn.grid(row=1, column=1, sticky=tk.W)
        
        # Unlock Service Section
        unlock_frame = ttk.LabelFrame(main_frame, text="Unlock Service", padding="10")
        unlock_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        unlock_frame.columnconfigure(1, weight=1)
        
        ttk.Label(unlock_frame, text="Start the unlock service to automatically unlock your laptop.").grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        self.start_btn = ttk.Button(unlock_frame, text="Start Service", command=self._start_service)
        self.start_btn.grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        
        self.stop_btn = ttk.Button(unlock_frame, text="Stop Service", command=self._stop_service, state=tk.DISABLED)
        self.stop_btn.grid(row=1, column=1, sticky=tk.W)
        
        # Settings Section
        settings_frame = ttk.LabelFrame(main_frame, text="Settings", padding="10")
        settings_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        settings_frame.columnconfigure(1, weight=1)
        
        # Tolerance
        ttk.Label(settings_frame, text="Recognition Tolerance:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.tolerance_var = tk.DoubleVar(value=config.get('face_recognition', 'tolerance', 0.50))
        tolerance_scale = ttk.Scale(settings_frame, from_=0.3, to=0.7, variable=self.tolerance_var, orient=tk.HORIZONTAL)
        tolerance_scale.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self.tolerance_label = ttk.Label(settings_frame, text=f"{self.tolerance_var.get():.2f}")
        self.tolerance_label.grid(row=0, column=2, padx=(10, 0))
        tolerance_scale.configure(command=self._update_tolerance_label)
        
        # Liveness detection
        self.liveness_var = tk.BooleanVar(value=config.get('liveness', 'enabled', True))
        liveness_check = ttk.Checkbutton(settings_frame, text="Enable Liveness Detection (Blink)", variable=self.liveness_var, command=self._update_liveness)
        liveness_check.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))
        
        # Timeout
        ttk.Label(settings_frame, text="Timeout (seconds):").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.timeout_var = tk.IntVar(value=config.get('unlock', 'timeout_seconds', 8))
        timeout_spin = ttk.Spinbox(settings_frame, from_=3, to=30, textvariable=self.timeout_var, width=10)
        timeout_spin.grid(row=2, column=1, sticky=tk.W, pady=(10, 0))
        
        # Save settings button
        save_btn = ttk.Button(settings_frame, text="Save Settings", command=self._save_settings)
        save_btn.grid(row=3, column=0, columnspan=3, pady=(10, 0))
        
        # Log Section
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # Log text widget with scrollbar
        self.log_text = tk.Text(log_frame, height=8, width=50, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Make log read-only
        self.log_text.configure(state=tk.DISABLED)
        
        # Bottom buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=3, pady=(10, 0))
        
        ttk.Button(button_frame, text="Refresh Status", command=self._load_status).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Open Config", command=self._open_config).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="About", command=self._show_about).pack(side=tk.LEFT)
    
    def _log(self, message, level="INFO"):
        """
        Add message to log display.
        
        Args:
            message: Message to log
            level: Log level (INFO, WARNING, ERROR, SUCCESS)
        """
        self.log_text.configure(state=tk.NORMAL)
        
        # Add timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color based on level
        if level == "ERROR":
            tag = "error"
            self.log_text.tag_configure("error", foreground="red")
        elif level == "WARNING":
            tag = "warning"
            self.log_text.tag_configure("warning", foreground="orange")
        elif level == "SUCCESS":
            tag = "success"
            self.log_text.tag_configure("success", foreground="green")
        else:
            tag = "info"
        
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)
    
    def _load_status(self):
        """Load and display current status."""
        # Check profile
        if PROFILE_PATH.exists():
            try:
                with open(PROFILE_PATH, 'rb') as f:
                    encoding = pickle.load(f)
                if encoding is not None and len(encoding) > 0:
                    self.profile_status.config(text="✓ Registered", style='Success.TLabel')
                else:
                    self.profile_status.config(text="✗ Invalid", style='Error.TLabel')
            except:
                self.profile_status.config(text="✗ Error", style='Error.TLabel')
        else:
            self.profile_status.config(text="✗ Not registered", style='Warning.TLabel')
        
        # Check camera
        try:
            cap = cv2.VideoCapture(config.get('camera', 'device_id', 0))
            if cap.isOpened():
                self.camera_status.config(text="✓ Available", style='Success.TLabel')
                cap.release()
            else:
                self.camera_status.config(text="✗ Not available", style='Error.TLabel')
        except:
            self.camera_status.config(text="✗ Error", style='Error.TLabel')
        
        # Check lock screen
        try:
            if is_screen_locked():
                self.lock_status.config(text="Locked", style='Warning.TLabel')
            else:
                self.lock_status.config(text="Unlocked", style='Success.TLabel')
        except:
            self.lock_status.config(text="Unknown", style='Status.TLabel')
        
        self._log("Status refreshed")
    
    def _update_tolerance_label(self, value):
        """Update tolerance label when slider changes."""
        self.tolerance_label.config(text=f"{float(value):.2f}")
    
    def _update_liveness(self):
        """Update liveness setting."""
        config.set('liveness', 'enabled', value=self.liveness_var.get())
        self._log(f"Liveness detection: {'Enabled' if self.liveness_var.get() else 'Disabled'}")
    
    def _save_settings(self):
        """Save current settings to config."""
        config.set('face_recognition', 'tolerance', value=self.tolerance_var.get())
        config.set('liveness', 'enabled', value=self.liveness_var.get())
        config.set('unlock', 'timeout_seconds', value=self.timeout_var.get())
        
        self._log("Settings saved", "SUCCESS")
        messagebox.showinfo("Settings", "Settings saved successfully!")
    
    def _start_registration(self):
        """Start face registration in a separate thread."""
        self.register_btn.config(state=tk.DISABLED)
        self.re_register_btn.config(state=tk.DISABLED)
        self._log("Starting face registration...")
        
        def run_registration():
            try:
                success = register_face(show_preview=True)
                if success:
                    self._log("Face registration completed successfully!", "SUCCESS")
                    self.root.after(0, lambda: messagebox.showinfo("Success", "Face registered successfully!"))
                else:
                    self._log("Face registration failed", "ERROR")
                    self.root.after(0, lambda: messagebox.showerror("Error", "Face registration failed. Please try again."))
            except Exception as e:
                self._log(f"Registration error: {e}", "ERROR")
                self.root.after(0, lambda: messagebox.showerror("Error", f"Registration error: {e}"))
            finally:
                self.root.after(0, lambda: self.register_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.re_register_btn.config(state=tk.NORMAL))
                self.root.after(0, self._load_status)
        
        thread = threading.Thread(target=run_registration, daemon=True)
        thread.start()
    
    def _start_service(self):
        """Start the unlock service."""
        if not PROFILE_PATH.exists():
            messagebox.showerror("Error", "Please register your face first!")
            return
        
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.service_status.config(text="Running", style='Success.TLabel')
        self._log("Unlock service started")
        
        def run_service():
            try:
                self.face_unlock = FaceUnlock()
                self.face_unlock.watch_for_lock_screen()
            except Exception as e:
                self._log(f"Service error: {e}", "ERROR")
                self.root.after(0, lambda: messagebox.showerror("Error", f"Service error: {e}"))
            finally:
                self.root.after(0, self._service_stopped)
        
        self.unlock_thread = threading.Thread(target=run_service, daemon=True)
        self.unlock_thread.start()
    
    def _stop_service(self):
        """Stop the unlock service."""
        self.is_running = False
        self._log("Stopping unlock service...")
        
        # The service will stop on next iteration
        self._service_stopped()
    
    def _service_stopped(self):
        """Update UI when service stops."""
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.service_status.config(text="Stopped", style='Status.TLabel')
        self._log("Unlock service stopped")
    
    def _open_config(self):
        """Open configuration file."""
        import os
        config_path = config.config_path
        if config_path.exists():
            os.startfile(str(config_path))
        else:
            messagebox.showinfo("Config", f"Config file not found at: {config_path}")
    
    def _show_about(self):
        """Show about dialog."""
        about_text = """FaceUnlock v1.0

A face recognition unlock system for Windows.

Features:
• Face recognition using face_recognition library
• Liveness detection (blink detection)
• Automatic lock screen detection
• Configurable settings

Created with Python, OpenCV, and MediaPipe.

Requirements:
• Python 3.7+
• Webcam
• Windows 10/11"""
        
        messagebox.showinfo("About FaceUnlock", about_text)


def main():
    """Main entry point for GUI."""
    root = tk.Tk()
    app = FaceUnlockGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
