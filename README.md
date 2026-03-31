<<<<<<< HEAD
# FaceLock
=======
# FaceUnlock

A face recognition unlock system for Windows laptops. Automatically unlocks your laptop when it detects your face, eliminating the need to type your password every time.

## Features

- **Face Recognition**: Uses the `face_recognition` library for accurate face detection and matching
- **Liveness Detection**: Blink detection prevents photo/video spoofing attacks
- **Automatic Lock Screen Detection**: Monitors for lock screen and triggers unlock automatically
- **GUI Interface**: Easy-to-use graphical interface for registration and settings
- **Configurable Settings**: Customize recognition tolerance, timeout, and more
- **Logging System**: Comprehensive logging for debugging and monitoring
- **Security Features**: Lockout after failed attempts, configurable security settings

## Requirements

### Software
- Python 3.7 or higher
- Windows 10/11
- Webcam (built-in or external)

### Python Packages
Install all dependencies using:
```bash
pip install -r requirements.txt
```

Required packages:
- `opencv-python` - Computer vision and camera handling
- `face-recognition` - Face detection and recognition
- `mediapipe` - Face mesh for liveness detection
- `numpy` - Numerical operations
- `pyautogui` - Keyboard simulation for unlocking
- `pywin32` - Windows API access (optional but recommended)

## Installation

1. **Clone or download this repository**
   ```bash
   cd FaceUnlock
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation**
   ```bash
   python config.py
   ```

## Quick Start

### Option 1: Using the GUI (Recommended)

1. **Launch the GUI**
   ```bash
   python gui.py
   ```

2. **Register your face**
   - Click "Register Face"
   - Position your face in the center of the frame
   - Move slightly to capture different angles
   - Wait for 60 captures (or press 'q' to finish early)

3. **Start the unlock service**
   - Click "Start Service"
   - The system will now monitor for lock screens and unlock automatically

### Option 2: Using Command Line

1. **Register your face**
   ```bash
   python register.py
   ```

2. **Start the unlock service**
   ```bash
   python unlock.py
   ```

3. **Lock your screen** (Win+L) to test the unlock

## Usage

### Face Registration

The registration process captures multiple face encodings to create a robust profile:

```bash
python register.py
```

**Tips for good registration:**
- Ensure good lighting on your face
- Look directly at the camera
- Move your head slightly to capture different angles
- Keep a neutral expression
- Avoid wearing glasses or hats if possible

The system will capture 60 frames by default (configurable in settings).

### Unlock Service

Start the unlock service to automatically unlock your laptop:

```bash
python unlock.py
```

The service will:
1. Monitor for Windows lock screen
2. When detected, activate the camera
3. Detect your face and verify identity
4. Unlock Windows automatically

**To stop the service:** Press `Ctrl+C` in the terminal

### GUI Interface

Launch the graphical interface for easier management:

```bash
python gui.py
```

The GUI provides:
- Status monitoring (profile, camera, lock screen)
- One-click face registration
- Service start/stop controls
- Settings adjustment
- Real-time logging

## Configuration

All settings are stored in `data/config.json`. You can modify them via:

1. **GUI**: Use the Settings section in the GUI
2. **Command line**: Edit `data/config.json` directly
3. **Python**: Use the config module

### Configuration Options

#### Face Recognition
- `tolerance`: Recognition strictness (0.3-0.7, lower = stricter)
- `model`: Detection model ("hog" for speed, "cnn" for accuracy)
- `num_jitters`: Re-sampling count for encoding

#### Liveness Detection
- `enabled`: Enable/disable blink detection
- `ear_threshold`: Eye aspect ratio threshold for blink detection
- `consecutive_frames`: Frames required to register a blink

#### Camera
- `device_id`: Camera device ID (0 = default webcam)
- `width`: Frame width
- `height`: Frame height

#### Unlock
- `timeout_seconds`: Time limit for unlock attempt
- `poll_interval`: Seconds between lock screen checks
- `lock_screen_delay`: Wait time after lock screen detected

#### Security
- `password`: Windows password (leave empty to prompt)
- `max_attempts`: Failed attempts before lockout
- `lockout_duration`: Lockout time in seconds

#### Logging
- `level`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `file_logging`: Enable logging to file
- `console_logging`: Enable logging to console

### View Current Configuration

```bash
python config.py
```

## File Structure

```
FaceUnlock/
├── register.py          # Face registration script
├── unlock.py            # Main unlock service
├── liveness.py          # Liveness detection (blink)
├── windows_bridge.py    # Windows lock screen interaction
├── config.py            # Configuration management
├── gui.py               # Graphical user interface
├── start.bat            # Windows batch file to start service
├── requirements.txt     # Python dependencies
├── README.md            # This file
├── data/
│   ├── profile.pkl      # Face encoding profile
│   └── config.json      # Configuration file
└── logs/
    └── faceunlock.log   # Log file
```

## How It Works

### Face Recognition
1. **Registration**: Captures 60 face encodings and averages them into a single profile
2. **Verification**: Compares detected face against stored profile using Euclidean distance
3. **Matching**: If distance < tolerance, face is recognized

### Liveness Detection
1. **MediaPipe Face Mesh**: Detects 468 facial landmarks
2. **Eye Aspect Ratio (EAR)**: Calculates eye openness ratio
3. **Blink Detection**: Monitors for rapid eye closure/opening
4. **Anti-Spoofing**: Prevents unlock with photos or videos

### Unlock Process
1. **Lock Screen Detection**: Monitors Windows foreground window
2. **Camera Activation**: Opens webcam when lock screen detected
3. **Liveness Check**: Waits for blink (if enabled)
4. **Face Recognition**: Matches face against stored profile
5. **Unlock**: Simulates keyboard input to enter password

## Troubleshooting

### Camera Not Working
- Check if camera is connected and not in use by another app
- Verify camera permissions in Windows Settings
- Try changing `camera.device_id` in config (0, 1, 2, etc.)

### Face Not Recognized
- Re-register with better lighting
- Adjust `face_recognition.tolerance` (increase for less strict)
- Ensure face is clearly visible (no glasses, hats, etc.)

### Unlock Not Triggering
- Check if profile exists (`data/profile.pkl`)
- Verify camera is working
- Check logs for errors (`logs/faceunlock.log`)
- Ensure `unlock.auto_start` is enabled

### Lock Screen Not Detected
- Install `pywin32`: `pip install pywin32`
- Check Windows version compatibility
- Test detection: `python windows_bridge.py`

### Performance Issues
- Use "hog" model instead of "cnn" (faster but less accurate)
- Reduce camera resolution in config
- Disable liveness detection if not needed

## Security Considerations

### Password Storage
- Password is stored in plain text in config file
- For better security, leave password empty to be prompted each time
- Consider using Windows Credential Manager (future feature)

### Lockout Protection
- System locks after 3 failed attempts (configurable)
- Lockout duration: 5 minutes (configurable)
- Prevents brute force attacks

### Liveness Detection
- Blink detection prevents photo/video attacks
- Can be disabled for faster unlock (less secure)
- Recommended to keep enabled

## Advanced Usage

### Custom Configuration

Create a custom config file:
```python
from config import Config

config = Config("my_config.json")
config.set('face_recognition', 'tolerance', value=0.45)
config.save_config()
```

### Testing Lock Screen Detection

```bash
python windows_bridge.py
```

### Running as Windows Service

To run FaceUnlock as a background service on startup:

1. Create a shortcut to `start.bat`
2. Place shortcut in `shell:startup` folder
3. Or use Task Scheduler to run at login

## Contributing

Contributions are welcome! Areas for improvement:
- Windows Credential Manager integration
- Multiple face profiles
- Face recognition model training
- Mobile app integration
- Linux/Mac support

## License

This project is open source and available under the MIT License.

## Acknowledgments

- [face_recognition](https://github.com/ageitgey/face_recognition) - Face recognition library
- [MediaPipe](https://google.github.io/mediapipe/) - Face mesh detection
- [OpenCV](https://opencv.org/) - Computer vision
- [pyautogui](https://pyautogui.readthedocs.io/) - GUI automation

## Support

For issues and questions:
1. Check the Troubleshooting section
2. Review logs in `logs/faceunlock.log`
3. Create an issue with detailed information

---

**Note**: This project is for personal use. Ensure you have permission to use face recognition on any system. Always follow local laws and regulations regarding biometric data.
>>>>>>> f5882f8 (Initial commit: FaceUnlock project)
