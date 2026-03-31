"""
Face Registration Module
Captures face encodings and creates a profile for face unlock.
"""

import cv2
import face_recognition
import pickle
import numpy as np
import time
import logging
from pathlib import Path

from config import config, PROFILE_PATH

# ── Setup Logging ──────────────────────────────────────────────────────
def setup_logging():
    """Configure logging for the registration module."""
    log_level = getattr(logging, config.get('logging', 'level'), logging.INFO)
    
    # Create logger
    logger = logging.getLogger('FaceUnlock.Register')
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


def validate_camera(camera_id=0):
    """
    Validate that the camera is accessible.
    
    Args:
        camera_id: Camera device ID
    
    Returns:
        tuple: (success: bool, camera: cv2.VideoCapture or None)
    """
    logger.info(f"Initializing camera {camera_id}...")
    cam = cv2.VideoCapture(camera_id)
    
    if not cam.isOpened():
        logger.error(f"Cannot open camera {camera_id}")
        return False, None
    
    # Test reading a frame
    ret, frame = cam.read()
    if not ret or frame is None:
        logger.error("Cannot read from camera")
        cam.release()
        return False, None
    
    logger.info(f"Camera initialized successfully: {frame.shape[1]}x{frame.shape[0]}")
    return True, cam


def capture_face_encodings(camera, num_captures=None, show_preview=True):
    """
    Capture face encodings from the camera.
    
    Args:
        camera: OpenCV VideoCapture object
        num_captures: Number of captures to take (None = use config)
        show_preview: Whether to show camera preview
    
    Returns:
        list: List of face encodings, or empty list if failed
    """
    if num_captures is None:
        num_captures = config.get('registration', 'num_captures', 60)
    
    min_captures = config.get('registration', 'min_captures', 20)
    capture_delay = config.get('registration', 'capture_delay', 0.1)
    
    encodings = []
    count = 0
    consecutive_failures = 0
    max_consecutive_failures = 30
    
    logger.info(f"Starting face capture. Target: {num_captures} captures")
    print("\n[*] Face Registration Started")
    print("[*] Position your face in the center of the frame")
    print("[*] Move slightly to capture different angles")
    print("[*] Press 'q' to quit early\n")
    
    start_time = time.time()
    
    while count < num_captures:
        ret, frame = camera.read()
        if not ret:
            logger.warning("Failed to read frame from camera")
            consecutive_failures += 1
            if consecutive_failures >= max_consecutive_failures:
                logger.error("Too many consecutive frame read failures")
                break
            continue
        
        consecutive_failures = 0
        
        # Convert to RGB for face_recognition
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        boxes = face_recognition.face_locations(rgb, model=config.get('face_recognition', 'model', 'hog'))
        
        if len(boxes) == 0:
            # No face detected
            if show_preview:
                cv2.putText(frame, "No face detected", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                cv2.putText(frame, "Position face in center", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)
        elif len(boxes) > 1:
            # Multiple faces detected
            if show_preview:
                cv2.putText(frame, "Multiple faces detected", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
                cv2.putText(frame, "Only one person at a time", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 1)
        else:
            # Exactly one face detected - capture encoding
            encs = face_recognition.face_encodings(
                rgb, boxes,
                num_jitters=config.get('face_recognition', 'num_jitters', 1)
            )
            
            if encs:
                encodings.append(encs[0])
                count += 1
                logger.debug(f"Captured encoding {count}/{num_captures}")
                
                # Draw success indicator
                if show_preview:
                    top, right, bottom, left = boxes[0]
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                    cv2.putText(frame, f"Captured: {count}/{num_captures}", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    
                    # Progress bar
                    progress = count / num_captures
                    bar_width = 300
                    bar_height = 20
                    bar_x = 10
                    bar_y = 70
                    cv2.rectangle(frame, (bar_x, bar_y), 
                                (bar_x + bar_width, bar_y + bar_height), 
                                (100, 100, 100), 2)
                    cv2.rectangle(frame, (bar_x, bar_y),
                                (bar_x + int(bar_width * progress), bar_y + bar_height),
                                (0, 255, 0), -1)
            else:
                if show_preview:
                    cv2.putText(frame, "Could not encode face", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        if show_preview:
            # Show elapsed time
            elapsed = time.time() - start_time
            cv2.putText(frame, f"Time: {elapsed:.1f}s", (10, frame.shape[0] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            
            cv2.imshow("Face Registration - Press 'q' to quit", frame)
            
            key = cv2.waitKey(max(1, int(capture_delay * 1000))) & 0xFF
            if key == ord('q'):
                logger.info("User cancelled registration")
                print("\n[!] Registration cancelled by user")
                break
        else:
            time.sleep(capture_delay)
    
    return encodings


def save_profile(encodings, profile_path=None):
    """
    Save face encodings as a profile.
    
    Args:
        encodings: List of face encodings
        profile_path: Path to save profile (None = use config)
    
    Returns:
        bool: True if successful
    """
    if profile_path is None:
        profile_path = PROFILE_PATH
    
    if not encodings:
        logger.error("No encodings to save")
        print("[✗] Error: No face encodings captured")
        return False
    
    min_captures = config.get('registration', 'min_captures', 20)
    if len(encodings) < min_captures:
        logger.warning(f"Only {len(encodings)} captures (minimum: {min_captures})")
        print(f"[!] Warning: Only {len(encodings)} captures (minimum recommended: {min_captures})")
        response = input("    Continue anyway? (y/n): ").strip().lower()
        if response != 'y':
            print("[!] Registration cancelled")
            return False
    
    try:
        # Average all encodings into a single robust profile
        avg_encoding = np.mean(encodings, axis=0)
        
        # Ensure directory exists
        profile_path = Path(profile_path)
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(profile_path, "wb") as f:
            pickle.dump(avg_encoding, f)
        
        logger.info(f"Profile saved to {profile_path} ({len(encodings)} encodings)")
        print(f"\n[✓] Profile saved successfully!")
        print(f"    Location: {profile_path}")
        print(f"    Encodings: {len(encodings)}")
        print(f"    Quality: {'Good' if len(encodings) >= 40 else 'Acceptable' if len(encodings) >= 20 else 'Low'}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save profile: {e}")
        print(f"[✗] Error saving profile: {e}")
        return False


def register_face(show_preview=True):
    """
    Main face registration function.
    
    Args:
        show_preview: Whether to show camera preview
    
    Returns:
        bool: True if registration successful
    """
    print("\n" + "="*60)
    print("FaceUnlock - Face Registration")
    print("="*60)
    
    # Validate configuration
    is_valid, errors = config.validate()
    if not is_valid:
        logger.error("Configuration validation failed")
        print("\n[✗] Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    # Initialize camera
    camera_id = config.get('camera', 'device_id', 0)
    success, camera = validate_camera(camera_id)
    if not success:
        print("[✗] Error: Cannot access camera")
        print("    Please check:")
        print("    - Camera is connected")
        print("    - Camera is not in use by another application")
        print("    - Camera permissions are granted")
        return False
    
    try:
        # Capture face encodings
        encodings = capture_face_encodings(camera, show_preview=show_preview)
        
        if not encodings:
            print("\n[✗] Registration failed: No face encodings captured")
            return False
        
        # Save profile
        success = save_profile(encodings)
        
        return success
        
    except KeyboardInterrupt:
        logger.info("Registration interrupted by user")
        print("\n[!] Registration interrupted")
        return False
        
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        print(f"\n[✗] Registration error: {e}")
        return False
        
    finally:
        # Cleanup
        camera.release()
        cv2.destroyAllWindows()


def main():
    """Main entry point for face registration."""
    try:
        success = register_face()
        
        if success:
            print("\n[✓] Face registration completed successfully!")
            print("    You can now run unlock.py to test face unlock")
        else:
            print("\n[✗] Face registration failed")
            print("    Please try again")
        
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n[✗] Fatal error: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
