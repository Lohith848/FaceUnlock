"""
Face Unlock Module
Monitors lock screen and unlocks Windows using face recognition.
"""

import cv2
import face_recognition
import mediapipe as mp
import pickle
import numpy as np
import time
import logging
import sys
from pathlib import Path

from config import config, PROFILE_PATH
from liveness import (
    eye_aspect_ratio, 
    BlinkDetector,
    LEFT_EYE_INDICES, 
    RIGHT_EYE_INDICES,
    EAR_THRESHOLD,
    CONSEC_FRAMES
)
from windows_bridge import is_screen_locked, unlock_windows
from security import get_password

# ── Setup Logging ──────────────────────────────────────────────────────
def setup_logging():
    """Configure logging for the unlock module."""
    log_level = getattr(logging, config.get('logging', 'level'), logging.INFO)
    
    # Create logger
    logger = logging.getLogger('FaceUnlock.Unlock')
    logger.setLevel(log_level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    if config.get('logging', 'console_logging'):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_format = logging.Formatter('[%(levelname)s] %(message)s')
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)
    
    # File handler
    if config.get('logging', 'file_logging'):
        from logging.handlers import RotatingFileHandler
        log_file = config.get('logging', 'max_log_size_mb', 10) * 1024 * 1024
        file_handler = RotatingFileHandler(
            'logs/faceunlock.log',
            maxBytes=log_file,
            backupCount=config.get('logging', 'backup_count', 5)
        )
        file_handler.setLevel(log_level)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger

logger = setup_logging()


class FaceUnlock:
    """Face unlock system for Windows."""
    
    def __init__(self):
        """Initialize the face unlock system."""
        self.known_encoding = None
        self.blink_detector = None
        self.face_mesh = None
        self.camera = None
        self.attempt_count = 0
        self.last_attempt_time = 0
        self.lockout_until = 0
        
        # Load configuration
        self.tolerance = config.get('face_recognition', 'tolerance', 0.50)
        self.blink_required = config.get('liveness', 'enabled', True)
        self.timeout = config.get('unlock', 'timeout_seconds', 8)
        self.poll_interval = config.get('unlock', 'poll_interval', 1.0)
        self.lock_screen_delay = config.get('unlock', 'lock_screen_delay', 1.5)
        self.max_attempts = config.get('security', 'max_attempts', 3)
        self.lockout_duration = config.get('security', 'lockout_duration', 300)
        
        # Initialize components
        self._load_profile()
        self._init_liveness()
    
    def _load_profile(self):
        """Load face profile from file."""
        try:
            if not PROFILE_PATH.exists():
                logger.error(f"Profile not found: {PROFILE_PATH}")
                print(f"[✗] Error: Face profile not found!")
                print(f"    Expected: {PROFILE_PATH}")
                print(f"    Please run register.py first to create a profile")
                sys.exit(1)
            
            with open(PROFILE_PATH, "rb") as f:
                self.known_encoding = pickle.load(f)
            
            logger.info(f"Face profile loaded from {PROFILE_PATH}")
            print(f"[✓] Face profile loaded")
            
        except Exception as e:
            logger.error(f"Failed to load profile: {e}")
            print(f"[✗] Error loading profile: {e}")
            sys.exit(1)
    
    def _init_liveness(self):
        """Initialize liveness detection components."""
        if self.blink_required:
            try:
                self.blink_detector = BlinkDetector(
                    ear_threshold=config.get('liveness', 'ear_threshold', EAR_THRESHOLD),
                    consec_frames=config.get('liveness', 'consecutive_frames', CONSEC_FRAMES)
                )
                self.face_mesh = mp.solutions.face_mesh.FaceMesh(
                    max_num_faces=1,
                    refine_landmarks=True,
                    min_detection_confidence=0.6,
                    min_tracking_confidence=0.6
                )
                logger.info("Liveness detection initialized")
            except Exception as e:
                logger.error(f"Failed to initialize liveness detection: {e}")
                print(f"[!] Warning: Liveness detection disabled: {e}")
                self.blink_required = False
    
    def _init_camera(self):
        """Initialize camera."""
        camera_id = config.get('camera', 'device_id', 0)
        width = config.get('camera', 'width', 640)
        height = config.get('camera', 'height', 480)
        
        self.camera = cv2.VideoCapture(camera_id)
        
        if not self.camera.isOpened():
            logger.error(f"Cannot open camera {camera_id}")
            return False
        
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        logger.info(f"Camera initialized: {width}x{height}")
        return True
    
    def _check_lockout(self):
        """Check if user is locked out due to too many failed attempts."""
        if time.time() < self.lockout_until:
            remaining = int(self.lockout_until - time.time())
            logger.warning(f"Account locked out. {remaining}s remaining")
            print(f"[!] Too many failed attempts. Try again in {remaining}s")
            return True
        return False
    
    def _record_failed_attempt(self):
        """Record a failed unlock attempt."""
        self.attempt_count += 1
        self.last_attempt_time = time.time()
        
        logger.warning(f"Failed unlock attempt {self.attempt_count}/{self.max_attempts}")
        
        if self.attempt_count >= self.max_attempts:
            self.lockout_until = time.time() + self.lockout_duration
            logger.warning(f"Account locked for {self.lockout_duration}s")
            print(f"[!] Too many failed attempts. Locked for {self.lockout_duration}s")
    
    def _reset_attempts(self):
        """Reset failed attempt counter."""
        self.attempt_count = 0
        self.lockout_until = 0
    
    def detect_blink(self, frame):
        """
        Detect blink in frame.
        
        Args:
            frame: BGR image frame
        
        Returns:
            tuple: (blink_detected: bool, ear: float, annotated_frame: numpy.ndarray)
        """
        if not self.blink_required or self.blink_detector is None:
            return True, 0.0, frame
        
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        results = self.face_mesh.process(rgb)
        
        if not results.multi_face_landmarks:
            return False, 0.0, frame
        
        landmarks = results.multi_face_landmarks[0].landmark
        
        # Calculate EAR for both eyes
        def get_eye(indices):
            return np.array([[landmarks[i].x * w, landmarks[i].y * h] for i in indices])
        
        left_ear = eye_aspect_ratio(get_eye(LEFT_EYE_INDICES))
        right_ear = eye_aspect_ratio(get_eye(RIGHT_EYE_INDICES))
        ear = (left_ear + right_ear) / 2.0
        
        # Update blink detector
        blink_detected = self.blink_detector.update(ear, time.time())
        
        # Annotate frame
        annotated_frame = frame.copy()
        
        if config.get('ui', 'show_landmarks', False):
            # Draw eye landmarks
            for idx in LEFT_EYE_INDICES + RIGHT_EYE_INDICES:
                x = int(landmarks[idx].x * w)
                y = int(landmarks[idx].y * h)
                cv2.circle(annotated_frame, (x, y), 2, (0, 255, 0), -1)
        
        if config.get('ui', 'show_ear', True):
            cv2.putText(annotated_frame, f"EAR: {ear:.3f}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        return blink_detected, ear, annotated_frame
    
    def recognize_face(self, frame):
        """
        Recognize face in frame.
        
        Args:
            frame: BGR image frame
        
        Returns:
            tuple: (match_found: bool, distance: float, boxes: list)
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        boxes = face_recognition.face_locations(
            rgb, 
            model=config.get('face_recognition', 'model', 'hog')
        )
        
        if not boxes:
            return False, 1.0, []
        
        # Get face encodings
        encs = face_recognition.face_encodings(
            rgb, 
            boxes,
            num_jitters=config.get('face_recognition', 'num_jitters', 1)
        )
        
        for enc in encs:
            dist = face_recognition.face_distance([self.known_encoding], enc)[0]
            if dist < self.tolerance:
                logger.info(f"Face match found! Distance: {dist:.3f}")
                return True, dist, boxes
        
        return False, min(face_recognition.face_distance([self.known_encoding], enc)[0] for enc in encs) if encs else 1.0, boxes
    
    def run_unlock(self):
        """
        Run the face unlock process.
        
        Returns:
            bool: True if unlock successful
        """
        # Check lockout
        if self._check_lockout():
            return False
        
        # Initialize camera
        if not self._init_camera():
            print("[✗] Error: Cannot access camera")
            return False
        
        logger.info("Starting face unlock process")
        print("\n[*] Face Unlock Started")
        print(f"[*] Timeout: {self.timeout}s")
        print(f"[*] Liveness detection: {'Enabled' if self.blink_required else 'Disabled'}")
        
        blink_detected = not self.blink_required  # Skip blink if not required
        start_time = time.time()
        show_preview = config.get('ui', 'show_preview', True)
        
        try:
            while True:
                elapsed = time.time() - start_time
                if elapsed > self.timeout:
                    logger.warning("Unlock timeout")
                    print("\n[-] Timeout — fallback to password")
                    self._record_failed_attempt()
                    break
                
                ret, frame = self.camera.read()
                if not ret:
                    logger.warning("Failed to read frame")
                    continue
                
                # Phase 1: Liveness detection (blink)
                if self.blink_required and not blink_detected:
                    blink_detected, ear, frame = self.detect_blink(frame)
                    
                    if show_preview:
                        cv2.putText(frame, "Blink to authenticate", (10, 30),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 0), 2)
                        cv2.putText(frame, f"Time left: {int(self.timeout - elapsed)}s", (10, 90),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1)
                        cv2.imshow(config.get('ui', 'window_name', 'FaceUnlock'), frame)
                        
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            logger.info("User cancelled unlock")
                            print("\n[!] Unlock cancelled")
                            break
                    continue
                
                # Phase 2: Face recognition
                match_found, distance, boxes = self.recognize_face(frame)
                
                if match_found:
                    logger.info(f"Unlock successful! Distance: {distance:.3f}")
                    print(f"\n[✓] Match! Distance: {distance:.3f}")
                    print("[*] Unlocking Windows...")
                    
                    # Get password
                    password = get_password()
                    
                    self.camera.release()
                    cv2.destroyAllWindows()
                    
                    # Unlock Windows
                    unlock_windows(password)
                    self._reset_attempts()
                    return True
                
                # Show status
                if show_preview:
                    # Draw face boxes
                    for (top, right, bottom, left) in boxes:
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                    
                    cv2.putText(frame, "Looking for you...", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
                    cv2.putText(frame, f"Distance: {distance:.3f} (need <{self.tolerance})", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1)
                    cv2.putText(frame, f"Time left: {int(self.timeout - elapsed)}s", (10, 90),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1)
                    
                    cv2.imshow(config.get('ui', 'window_name', 'FaceUnlock'), frame)
                    
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        logger.info("User cancelled unlock")
                        print("\n[!] Unlock cancelled")
                        break
            
            return False
            
        except Exception as e:
            logger.error(f"Unlock error: {e}", exc_info=True)
            print(f"\n[✗] Unlock error: {e}")
            return False
            
        finally:
            if self.camera and self.camera.isOpened():
                self.camera.release()
            cv2.destroyAllWindows()
    
    def watch_for_lock_screen(self):
        """Watch for lock screen and trigger unlock."""
        print("\n" + "="*60)
        print("FaceUnlock - Running")
        print("="*60)
        print(f"[*] Watching for lock screen...")
        print(f"[*] Poll interval: {self.poll_interval}s")
        print(f"[*] Press Ctrl+C to stop\n")
        
        was_locked = False
        
        try:
            while True:
                locked = is_screen_locked()
                
                if locked and not was_locked:
                    logger.info("Lock screen detected")
                    print(f"\n[*] Lock screen detected — starting camera in {self.lock_screen_delay}s...")
                    time.sleep(self.lock_screen_delay)
                    self.run_unlock()
                
                was_locked = locked
                time.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            logger.info("FaceUnlock stopped by user")
            print("\n\n[*] FaceUnlock stopped")
        
        except Exception as e:
            logger.error(f"Watch error: {e}", exc_info=True)
            print(f"\n[✗] Error: {e}")


def main():
    """Main entry point for face unlock."""
    try:
        # Validate configuration
        is_valid, errors = config.validate()
        if not is_valid:
            logger.error("Configuration validation failed")
            print("\n[✗] Configuration errors:")
            for error in errors:
                print(f"  - {error}")
            return 1
        
        # Create and run face unlock
        unlocker = FaceUnlock()
        unlocker.watch_for_lock_screen()
        
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n[✗] Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
