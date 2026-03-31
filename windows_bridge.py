"""
Windows Bridge Module
Provides functions to interact with Windows lock screen and unlock.
"""

import ctypes
import pyautogui
import time
import logging
import sys

# ── Setup Logging ──────────────────────────────────────────────────────
logger = logging.getLogger('FaceUnlock.WindowsBridge')


def is_screen_locked():
    """
    Check if Windows lock screen is active.
    
    Returns:
        bool: True if screen is locked, False otherwise
    """
    try:
        user32 = ctypes.windll.User32
        
        # GetForegroundWindow returns 0 (None) on lock screen
        hwnd = user32.GetForegroundWindow()
        
        if hwnd == 0:
            logger.debug("Lock screen detected (no foreground window)")
            return True
        
        # Additional check for LockApp process (Win10/11 lock screen)
        try:
            import win32process
            import win32api
            import win32con
            
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            handle = win32api.OpenProcess(
                win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
                False,
                pid
            )
            
            if handle:
                try:
                    name = win32api.GetModuleFileNameEx(handle, 0)
                    is_locked = "LockApp" in name or "LogonUI" in name
                    
                    if is_locked:
                        logger.debug(f"Lock screen detected (process: {name})")
                    
                    return is_locked
                finally:
                    win32api.CloseHandle(handle)
                    
        except ImportError:
            # win32api not available, fall back to hwnd check
            logger.debug("win32api not available, using hwnd check only")
            return hwnd == 0
        except Exception as e:
            logger.debug(f"Error checking lock screen process: {e}")
            return hwnd == 0
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking lock screen status: {e}")
        return False


def unlock_windows(password, delay=0.5):
    """
    Unlock Windows by simulating keyboard input.
    
    Args:
        password: Windows password to type
        delay: Delay between actions (seconds)
    
    Returns:
        bool: True if unlock command sent successfully
    """
    try:
        logger.info("Attempting to unlock Windows...")
        
        # Small delay to ensure lock screen is ready
        time.sleep(delay)
        
        # Press Enter to dismiss lock screen overlay
        logger.debug("Pressing Enter to dismiss lock screen")
        pyautogui.press("enter")
        time.sleep(delay * 1.5)  # Wait for password field to appear
        
        # Type password
        logger.debug("Typing password")
        pyautogui.typewrite(password, interval=0.04)
        
        # Press Enter to submit
        logger.debug("Pressing Enter to submit password")
        pyautogui.press("enter")
        
        logger.info("Unlock command sent successfully")
        print("[+] Unlock command sent.")
        return True
        
    except Exception as e:
        logger.error(f"Error unlocking Windows: {e}")
        print(f"[✗] Error unlocking Windows: {e}")
        return False


def unlock_windows_secure(password=None):
    """
    Unlock Windows using more secure method.
    If password is not provided, prompts user for it.
    
    Args:
        password: Windows password (optional)
    
    Returns:
        bool: True if unlock successful
    """
    if password is None:
        import getpass
        password = getpass.getpass("[?] Enter Windows password: ")
    
    if not password:
        logger.error("No password provided")
        print("[✗] Error: No password provided")
        return False
    
    return unlock_windows(password)


def test_lock_screen_detection():
    """
    Test lock screen detection functionality.
    
    Returns:
        bool: True if test passed
    """
    print("\n" + "="*60)
    print("Lock Screen Detection Test")
    print("="*60)
    
    print("\n[*] Testing lock screen detection...")
    print("[*] Lock your screen (Win+L) to test detection")
    print("[*] Press Ctrl+C to stop\n")
    
    try:
        was_locked = False
        check_count = 0
        
        while True:
            check_count += 1
            locked = is_screen_locked()
            
            if locked and not was_locked:
                print(f"\n[✓] Lock screen detected! (check #{check_count})")
            elif not locked and was_locked:
                print(f"\n[✓] Lock screen dismissed! (check #{check_count})")
            
            was_locked = locked
            time.sleep(1)
            
    except KeyboardInterrupt:
        print(f"\n\n[*] Test completed. Total checks: {check_count}")
        return True
    
    except Exception as e:
        logger.error(f"Test error: {e}")
        print(f"\n[✗] Test error: {e}")
        return False


def check_dependencies():
    """
    Check if required dependencies are installed.
    
    Returns:
        tuple: (all_installed: bool, missing: list)
    """
    missing = []
    
    # Check pyautogui
    try:
        import pyautogui
    except ImportError:
        missing.append("pyautogui")
    
    # Check win32api (optional but recommended)
    try:
        import win32api
        import win32process
    except ImportError:
        logger.warning("pywin32 not installed. Lock screen detection may be less accurate.")
        print("[!] Warning: pywin32 not installed. Install with: pip install pywin32")
    
    return len(missing) == 0, missing


def main():
    """Main entry point for testing."""
    import sys
    
    # Setup basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(message)s'
    )
    
    # Check dependencies
    all_installed, missing = check_dependencies()
    if not all_installed:
        print(f"[✗] Missing dependencies: {', '.join(missing)}")
        print(f"    Install with: pip install {' '.join(missing)}")
        return 1
    
    # Run test
    success = test_lock_screen_detection()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
