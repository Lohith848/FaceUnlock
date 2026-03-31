"""
Security Module for FaceUnlock
Provides secure password handling and encryption.
"""

import os
import base64
import hashlib
import logging
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger('FaceUnlock.Security')

# ── Constants ──────────────────────────────────────────────────────────
KEY_FILE = Path("data/.key")
SALT_FILE = Path("data/.salt")
ENCRYPTED_PASSWORD_FILE = Path("data/.password.enc")


def generate_key(password: str, salt: bytes = None) -> tuple:
    """
    Generate encryption key from password.
    
    Args:
        password: Password to derive key from
        salt: Salt for key derivation (generated if None)
    
    Returns:
        tuple: (key: bytes, salt: bytes)
    """
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt


def save_salt(salt: bytes):
    """Save salt to file."""
    try:
        SALT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SALT_FILE, 'wb') as f:
            f.write(salt)
        logger.debug("Salt saved")
    except Exception as e:
        logger.error(f"Failed to save salt: {e}")
        raise


def load_salt() -> bytes:
    """Load salt from file."""
    try:
        if not SALT_FILE.exists():
            raise FileNotFoundError("Salt file not found")
        
        with open(SALT_FILE, 'rb') as f:
            salt = f.read()
        return salt
    except Exception as e:
        logger.error(f"Failed to load salt: {e}")
        raise


def encrypt_password(password: str, master_password: str = None) -> bytes:
    """
    Encrypt password using master password.
    
    Args:
        password: Password to encrypt
        master_password: Master password for encryption (uses machine-specific if None)
    
    Returns:
        bytes: Encrypted password
    """
    try:
        if master_password is None:
            master_password = get_machine_key()
        
        # Generate key from master password
        key, salt = generate_key(master_password)
        
        # Save salt
        save_salt(salt)
        
        # Encrypt password
        fernet = Fernet(key)
        encrypted = fernet.encrypt(password.encode())
        
        logger.info("Password encrypted successfully")
        return encrypted
        
    except Exception as e:
        logger.error(f"Failed to encrypt password: {e}")
        raise


def decrypt_password(encrypted_password: bytes, master_password: str = None) -> str:
    """
    Decrypt password using master password.
    
    Args:
        encrypted_password: Encrypted password bytes
        master_password: Master password for decryption (uses machine-specific if None)
    
    Returns:
        str: Decrypted password
    """
    try:
        if master_password is None:
            master_password = get_machine_key()
        
        # Load salt
        salt = load_salt()
        
        # Generate key from master password
        key, _ = generate_key(master_password, salt)
        
        # Decrypt password
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted_password).decode()
        
        logger.info("Password decrypted successfully")
        return decrypted
        
    except Exception as e:
        logger.error(f"Failed to decrypt password: {e}")
        raise


def save_encrypted_password(password: str, master_password: str = None):
    """
    Save encrypted password to file.
    
    Args:
        password: Password to save
        master_password: Master password for encryption
    """
    try:
        encrypted = encrypt_password(password, master_password)
        
        ENCRYPTED_PASSWORD_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ENCRYPTED_PASSWORD_FILE, 'wb') as f:
            f.write(encrypted)
        
        logger.info("Encrypted password saved")
        
    except Exception as e:
        logger.error(f"Failed to save encrypted password: {e}")
        raise


def load_encrypted_password(master_password: str = None) -> str:
    """
    Load and decrypt password from file.
    
    Args:
        master_password: Master password for decryption
    
    Returns:
        str: Decrypted password
    """
    try:
        if not ENCRYPTED_PASSWORD_FILE.exists():
            raise FileNotFoundError("Encrypted password file not found")
        
        with open(ENCRYPTED_PASSWORD_FILE, 'rb') as f:
            encrypted = f.read()
        
        return decrypt_password(encrypted, master_password)
        
    except Exception as e:
        logger.error(f"Failed to load encrypted password: {e}")
        raise


def get_machine_key() -> str:
    """
    Generate a machine-specific key for encryption.
    Uses a combination of machine-specific identifiers.
    
    Returns:
        str: Machine-specific key
    """
    try:
        import platform
        import uuid
        
        # Combine machine-specific identifiers
        identifiers = [
            platform.node(),  # Computer name
            str(uuid.getnode()),  # MAC address
            platform.processor(),  # Processor
            platform.system(),  # OS
        ]
        
        # Create hash of identifiers
        combined = "".join(identifiers)
        key = hashlib.sha256(combined.encode()).hexdigest()
        
        return key
        
    except Exception as e:
        logger.error(f"Failed to generate machine key: {e}")
        # Fallback to a default key (less secure)
        return "FaceUnlock_Default_Key_2024"


def is_password_encrypted() -> bool:
    """Check if password is encrypted."""
    return ENCRYPTED_PASSWORD_FILE.exists()


def setup_encryption():
    """Setup encryption for the first time."""
    try:
        from config import config
        
        # Get current password
        password = config.get('security', 'password', '')
        
        if not password:
            logger.warning("No password configured")
            return False
        
        # Encrypt and save password
        save_encrypted_password(password)
        
        # Clear password from config
        config.set('security', 'password', value='')
        config.set('security', 'use_credential_manager', value=True)
        
        logger.info("Encryption setup completed")
        print("[✓] Password encrypted and saved securely")
        return True
        
    except Exception as e:
        logger.error(f"Encryption setup failed: {e}")
        print(f"[✗] Encryption setup failed: {e}")
        return False


def get_password() -> str:
    """
    Get password from encrypted storage or prompt user.
    
    Returns:
        str: Password
    """
    from config import config
    
    # Try to get from config first
    password = config.get('security', 'password', '')
    if password:
        return password
    
    # Try to decrypt from file
    if is_password_encrypted():
        try:
            return load_encrypted_password()
        except Exception as e:
            logger.error(f"Failed to decrypt password: {e}")
    
    # Prompt user
    import getpass
    password = getpass.getpass("[?] Enter Windows password: ")
    
    # Ask if user wants to save encrypted
    if password:
        save = input("[?] Save password encrypted? (y/n): ").strip().lower()
        if save == 'y':
            try:
                save_encrypted_password(password)
                print("[✓] Password saved encrypted")
            except Exception as e:
                print(f"[!] Could not save password: {e}")
    
    return password


def clear_credentials():
    """Clear all saved credentials."""
    try:
        files_to_remove = [
            ENCRYPTED_PASSWORD_FILE,
            SALT_FILE,
            KEY_FILE,
        ]
        
        for file_path in files_to_remove:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Removed {file_path}")
        
        # Clear password from config
        from config import config
        config.set('security', 'password', value='')
        
        print("[✓] All credentials cleared")
        return True
        
    except Exception as e:
        logger.error(f"Failed to clear credentials: {e}")
        print(f"[✗] Failed to clear credentials: {e}")
        return False


def check_security_status():
    """Check and display security status."""
    print("\n" + "="*60)
    print("Security Status")
    print("="*60)
    
    from config import config
    
    # Check password
    password = config.get('security', 'password', '')
    if password:
        print("[!] Password stored in plain text in config")
        print("    Consider encrypting it for better security")
    else:
        print("[✓] No plain text password in config")
    
    # Check encrypted password
    if is_password_encrypted():
        print("[✓] Encrypted password file exists")
    else:
        print("[!] No encrypted password file")
    
    # Check liveness detection
    liveness = config.get('liveness', 'enabled', True)
    if liveness:
        print("[✓] Liveness detection enabled")
    else:
        print("[!] Liveness detection disabled (less secure)")
    
    # Check lockout settings
    max_attempts = config.get('security', 'max_attempts', 3)
    lockout_duration = config.get('security', 'lockout_duration', 300)
    print(f"[✓] Lockout: {max_attempts} attempts, {lockout_duration}s duration")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    # Setup basic logging
    logging.basicConfig(level=logging.INFO)
    
    # Check security status
    check_security_status()
    
    # Offer to setup encryption
    from config import config
    password = config.get('security', 'password', '')
    
    if password and not is_password_encrypted():
        print("\n[!] You have a plain text password in config")
        response = input("    Would you like to encrypt it? (y/n): ").strip().lower()
        if response == 'y':
            setup_encryption()
