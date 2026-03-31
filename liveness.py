"""
Liveness Detection Module
Provides eye aspect ratio (EAR) calculation and blink detection
to prevent photo/video spoofing attacks.
"""

import numpy as np
from scipy.spatial import distance as dist

# ── Configuration Constants ──────────────────────────────────────────────
EAR_THRESHOLD = 0.21      # Eye aspect ratio threshold for blink detection
CONSEC_FRAMES = 3         # Number of consecutive frames below threshold to count as blink
BLINK_COOLDOWN = 0.5      # Minimum seconds between blinks to avoid double-counting


def eye_aspect_ratio(eye_landmarks):
    """
    Calculate the Eye Aspect Ratio (EAR) for blink detection.
    
    The EAR is the ratio of the vertical eye opening to the horizontal eye width.
    When eyes are open, EAR is relatively high (~0.25-0.35).
    When eyes close (blink), EAR drops significantly (~0.1-0.15).
    
    Formula:
        EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||)
    
    Args:
        eye_landmarks: numpy array of shape (6, 2) containing the 6 eye landmark
                      coordinates in order: [p1, p2, p3, p4, p5, p6]
                      where:
                          p1 = left corner
                          p2 = top-left
                          p3 = top-right
                          p4 = right corner
                          p5 = bottom-right
                          p6 = bottom-left
    
    Returns:
        float: The eye aspect ratio value
    """
    # Compute the euclidean distances between the two sets of
    # vertical eye landmarks (x, y)-coordinates
    A = dist.euclidean(eye_landmarks[1], eye_landmarks[5])
    B = dist.euclidean(eye_landmarks[2], eye_landmarks[4])
    
    # Compute the euclidean distance between the horizontal
    # eye landmark (x, y)-coordinates
    C = dist.euclidean(eye_landmarks[0], eye_landmarks[3])
    
    # Compute the eye aspect ratio
    ear = (A + B) / (2.0 * C)
    
    return ear


def calculate_ear_from_mediapipe(landmarks, eye_indices, frame_width, frame_height):
    """
    Calculate EAR from MediaPipe face mesh landmarks.
    
    Args:
        landmarks: MediaPipe face mesh landmarks
        eye_indices: List of 6 landmark indices for the eye
        frame_width: Width of the video frame
        frame_height: Height of the video frame
    
    Returns:
        float: The eye aspect ratio value
    """
    # Extract eye landmark coordinates and scale to frame dimensions
    eye_points = np.array([
        [landmarks[i].x * frame_width, landmarks[i].y * frame_height]
        for i in eye_indices
    ])
    
    return eye_aspect_ratio(eye_points)


class BlinkDetector:
    """
    Stateful blink detector that tracks blink state across frames.
    Prevents false positives and provides better blink detection accuracy.
    """
    
    def __init__(self, ear_threshold=EAR_THRESHOLD, consec_frames=CONSEC_FRAMES):
        """
        Initialize the blink detector.
        
        Args:
            ear_threshold: EAR value below which eye is considered closed
            consec_frames: Number of consecutive frames required to register a blink
        """
        self.ear_threshold = ear_threshold
        self.consec_frames = consec_frames
        self.blink_counter = 0
        self.total_blinks = 0
        self.blink_detected = False
        self.last_blink_time = 0
        
    def update(self, ear, current_time):
        """
        Update blink detection state with new EAR value.
        
        Args:
            ear: Current eye aspect ratio
            current_time: Current timestamp in seconds
        
        Returns:
            bool: True if a new blink was detected in this frame
        """
        if ear < self.ear_threshold:
            self.blink_counter += 1
        else:
            # Check if we had enough consecutive frames below threshold
            if self.blink_counter >= self.consec_frames:
                # Check cooldown to avoid double-counting
                if current_time - self.last_blink_time > BLINK_COOLDOWN:
                    self.total_blinks += 1
                    self.blink_detected = True
                    self.last_blink_time = current_time
                    self.blink_counter = 0
                    return True
            self.blink_counter = 0
            
        return False
    
    def reset(self):
        """Reset the blink detector state."""
        self.blink_counter = 0
        self.blink_detected = False
        self.total_blinks = 0
        self.last_blink_time = 0


def detect_blink_from_frame(frame, face_mesh, left_eye_indices, right_eye_indices):
    """
    Detect blinks in a single frame using MediaPipe face mesh.
    
    Args:
        frame: BGR image frame from OpenCV
        face_mesh: MediaPipe FaceMesh instance
        left_eye_indices: List of 6 landmark indices for left eye
        right_eye_indices: List of 6 landmark indices for right eye
    
    Returns:
        tuple: (blink_detected: bool, ear: float, frame_annotated: numpy.ndarray)
    """
    import cv2
    
    h, w = frame.shape[:2]
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    results = face_mesh.process(rgb)
    
    if not results.multi_face_landmarks:
        return False, 0.0, frame
    
    landmarks = results.multi_face_landmarks[0].landmark
    
    # Calculate EAR for both eyes
    left_ear = calculate_ear_from_mediapipe(landmarks, left_eye_indices, w, h)
    right_ear = calculate_ear_from_mediapipe(landmarks, right_eye_indices, w, h)
    
    # Average EAR of both eyes
    ear = (left_ear + right_ear) / 2.0
    
    # Draw eye landmarks on frame for visualization
    annotated_frame = frame.copy()
    for idx in left_eye_indices + right_eye_indices:
        x = int(landmarks[idx].x * w)
        y = int(landmarks[idx].y * h)
        cv2.circle(annotated_frame, (x, y), 2, (0, 255, 0), -1)
    
    # Display EAR value
    cv2.putText(annotated_frame, f"EAR: {ear:.3f}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    return ear < EAR_THRESHOLD, ear, annotated_frame


# ── MediaPipe Eye Landmark Indices ──────────────────────────────────────
# These are the standard MediaPipe face mesh indices for eyes
LEFT_EYE_INDICES = [362, 385, 387, 263, 373, 380]
RIGHT_EYE_INDICES = [33, 160, 158, 133, 153, 144]

# Alternative indices (more precise, using iris landmarks)
LEFT_EYE_INDICES_PRECISE = [362, 385, 387, 263, 373, 380, 388, 466, 390, 373]
RIGHT_EYE_INDICES_PRECISE = [33, 160, 158, 133, 153, 144, 145, 233, 153, 154]
