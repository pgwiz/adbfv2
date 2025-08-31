"""
Secure credential storage using OS keyring with encrypted fallback.
"""
import os
import json
import logging
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from .platform_paths import get_app_data_dir

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    logging.warning("keyring not available, using encrypted file fallback")


class SecureStore:
    """Secure storage for sensitive data like pairing codes and credentials."""
    
    def __init__(self, service_name: str = "ADBHelper"):
        self.logger = logging.getLogger(__name__)
        self.service_name = service_name
        self.encrypted_file = get_app_data_dir() / "secure_data.enc"
        self._encryption_key: Optional[bytes] = None
    
    def _get_keyring_key(self, key: str) -> Optional[str]:
        """Get value from OS keyring."""
        if not KEYRING_AVAILABLE:
            return None
        
        try:
            return keyring.get_password(self.service_name, key)
        except Exception as e:
            self.logger.error(f"Keyring access failed: {e}")
            return None
    
    def _set_keyring_key(self, key: str, value: str) -> bool:
        """Set value in OS keyring."""
        if not KEYRING_AVAILABLE:
            return False
        
        try:
            keyring.set_password(self.service_name, key, value)
            return True
        except Exception as e:
            self.logger.error(f"Keyring storage failed: {e}")
            return False
    
    def _delete_keyring_key(self, key: str) -> bool:
        """Delete value from OS keyring."""
        if not KEYRING_AVAILABLE:
            return False
        
        try:
            keyring.delete_password(self.service_name, key)
            return True
        except Exception as e:
            self.logger.error(f"Keyring deletion failed: {e}")
            return False
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def _load_encrypted_data(self, password: str) -> Optional[Dict[str, Any]]:
        """Load and decrypt data from encrypted file."""
        if not self.encrypted_file.exists():
            return {}
        
        try:
            with open(self.encrypted_file, 'rb') as f:
                encrypted_data = f.read()
            
            # Extract salt (first 16 bytes) and encrypted content
            salt = encrypted_data[:16]
            encrypted_content = encrypted_data[16:]
            
            # Derive key and decrypt
            key = self._derive_key(password, salt)
            fernet = Fernet(key)
            decrypted_data = fernet.decrypt(encrypted_content)
            
            return json.loads(decrypted_data.decode())
            
        except Exception as e:
            self.logger.error(f"Failed to decrypt data: {e}")
            return None
    
    def _save_encrypted_data(self, data: Dict[str, Any], password: str) -> bool:
        """Encrypt and save data to file."""
        try:
            # Generate salt and derive key
            import os
            salt = os.urandom(16)
            key = self._derive_key(password, salt)
            fernet = Fernet(key)
            
            # Encrypt data
            json_data = json.dumps(data).encode()
            encrypted_data = fernet.encrypt(json_data)
            
            # Save salt + encrypted data
            self.encrypted_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.encrypted_file, 'wb') as f:
                f.write(salt + encrypted_data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to encrypt data: {e}")
            return False
    
    def store_credential(self, key: str, value: str, use_keyring: bool = True) -> bool:
        """
        Store a credential securely.
        
        Args:
            key: Credential identifier
            value: Credential value
            use_keyring: Try OS keyring first (fallback to encrypted file)
        
        Returns:
            True if stored successfully
        """
        if use_keyring and self._set_keyring_key(key, value):
            self.logger.debug(f"Stored {key} in OS keyring")
            return True
        
        # Fallback to encrypted file storage
        self.logger.warning(f"Keyring unavailable, using encrypted file for {key}")
        return False  # Requires user password - handled by UI
    
    def get_credential(self, key: str, password: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a credential.
        
        Args:
            key: Credential identifier
            password: Password for encrypted file (if keyring fails)
        
        Returns:
            Credential value or None if not found
        """
        # Try keyring first
        value = self._get_keyring_key(key)
        if value is not None:
            return value
        
        # Try encrypted file
        if password:
            data = self._load_encrypted_data(password)
            if data is not None:
                return data.get(key)
        
        return None
    
    def delete_credential(self, key: str, password: Optional[str] = None) -> bool:
        """Delete a credential from all storage locations."""
        success = True
        
        # Delete from keyring
        if not self._delete_keyring_key(key):
            success = False
        
        # Delete from encrypted file
        if password:
            data = self._load_encrypted_data(password)
            if data is not None and key in data:
                del data[key]
                if not self._save_encrypted_data(data, password):
                    success = False
        
        return success
    
    def clear_all_data(self, password: Optional[str] = None, confirmation: str = "") -> bool:
        """
        Clear all stored credentials. Requires confirmation.
        
        Args:
            password: Password for encrypted file
            confirmation: Must be "DELETE" to proceed
        
        Returns:
            True if all data cleared successfully
        """
        if confirmation != "DELETE":
            self.logger.warning("Clear all data called without proper confirmation")
            return False
        
        success = True
        
        # Clear keyring entries (we need to track what we've stored)
        # This is a limitation - keyring doesn't provide list functionality
        common_keys = ["pairing_codes", "device_passwords", "wifi_credentials"]
        for key in common_keys:
            self._delete_keyring_key(key)
        
        # Delete encrypted file
        try:
            if self.encrypted_file.exists():
                self.encrypted_file.unlink()
                self.logger.info("Encrypted data file deleted")
        except Exception as e:
            self.logger.error(f"Failed to delete encrypted file: {e}")
            success = False
        
        return success
    
    def is_keyring_available(self) -> bool:
        """Check if OS keyring is available and working."""
        if not KEYRING_AVAILABLE:
            return False
        
        try:
            # Test keyring functionality
            test_key = f"{self.service_name}_test"
            keyring.set_password(self.service_name, test_key, "test")
            result = keyring.get_password(self.service_name, test_key)
            keyring.delete_password(self.service_name, test_key)
            return result == "test"
        except Exception:
            return False
