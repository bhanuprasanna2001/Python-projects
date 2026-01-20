"""
Password Hashing
================
Secure password hashing with bcrypt and argon2.
"""

import secrets
import hmac
import hashlib
from passlib.context import CryptContext
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from typing import Tuple
import time


# =============================================================================
# Passlib with bcrypt (Recommended approach)
# =============================================================================

class BCryptPasswordManager:
    """
    Password manager using bcrypt via passlib.
    
    Bcrypt is the most widely used algorithm and is battle-tested.
    Default work factor (rounds) is 12, which takes ~250ms.
    """
    
    def __init__(self, rounds: int = 12):
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=rounds,
        )
    
    def hash(self, password: str) -> str:
        """Hash a password."""
        return self.pwd_context.hash(password)
    
    def verify(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        return self.pwd_context.verify(password, hashed)
    
    def needs_rehash(self, hashed: str) -> bool:
        """Check if hash needs to be updated (e.g., rounds changed)."""
        return self.pwd_context.needs_update(hashed)
    
    def verify_and_update(self, password: str, hashed: str) -> Tuple[bool, str]:
        """
        Verify password and rehash if needed.
        Returns (is_valid, new_hash_or_empty).
        """
        is_valid, new_hash = self.pwd_context.verify_and_update(password, hashed)
        return is_valid, new_hash or ""


# =============================================================================
# Argon2 (Modern alternative, winner of PHC)
# =============================================================================

class Argon2PasswordManager:
    """
    Password manager using Argon2id.
    
    Argon2 won the Password Hashing Competition (PHC) in 2015.
    Argon2id is the recommended variant (combines resistance to
    both side-channel and GPU attacks).
    """
    
    def __init__(
        self,
        time_cost: int = 3,      # Number of iterations
        memory_cost: int = 65536, # Memory in KB (64 MB)
        parallelism: int = 4,     # Number of parallel threads
    ):
        self.hasher = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=32,
            salt_len=16,
            type=PasswordHasher.Type.ID,  # Argon2id
        )
    
    def hash(self, password: str) -> str:
        """Hash a password."""
        return self.hasher.hash(password)
    
    def verify(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        try:
            self.hasher.verify(hashed, password)
            return True
        except VerifyMismatchError:
            return False
    
    def needs_rehash(self, hashed: str) -> bool:
        """Check if hash needs to be updated."""
        return self.hasher.check_needs_rehash(hashed)


# =============================================================================
# Multi-scheme support (for migration)
# =============================================================================

class MigrationPasswordManager:
    """
    Password manager that supports multiple schemes.
    Useful when migrating from one hashing algorithm to another.
    """
    
    def __init__(self):
        self.pwd_context = CryptContext(
            schemes=["argon2", "bcrypt", "pbkdf2_sha256"],
            default="argon2",  # New passwords use argon2
            deprecated=["bcrypt", "pbkdf2_sha256"],  # Old schemes
            argon2__time_cost=3,
            argon2__memory_cost=65536,
            bcrypt__rounds=12,
        )
    
    def hash(self, password: str) -> str:
        """Hash a password using the default scheme."""
        return self.pwd_context.hash(password)
    
    def verify(self, password: str, hashed: str) -> bool:
        """Verify password (works with any supported scheme)."""
        return self.pwd_context.verify(password, hashed)
    
    def needs_rehash(self, hashed: str) -> bool:
        """Check if hash uses a deprecated scheme."""
        return self.pwd_context.needs_update(hashed)
    
    def verify_and_update(self, password: str, hashed: str) -> Tuple[bool, str]:
        """Verify and migrate to new scheme if needed."""
        is_valid, new_hash = self.pwd_context.verify_and_update(password, hashed)
        return is_valid, new_hash or ""


# =============================================================================
# Secure String Comparison
# =============================================================================

def constant_time_compare(a: str, b: str) -> bool:
    """
    Compare two strings in constant time.
    Prevents timing attacks.
    """
    return hmac.compare_digest(a.encode('utf-8'), b.encode('utf-8'))


def secure_random_string(length: int = 32) -> str:
    """Generate a cryptographically secure random string."""
    return secrets.token_urlsafe(length)


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for storage.
    API keys don't need slow hashing since they're random and long.
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, hashed: str) -> bool:
    """Verify an API key against its hash."""
    return constant_time_compare(hash_api_key(api_key), hashed)


# =============================================================================
# Password Validation
# =============================================================================

class PasswordValidator:
    """
    Validate password strength.
    """
    
    def __init__(
        self,
        min_length: int = 8,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = True,
    ):
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digit = require_digit
        self.require_special = require_special
    
    def validate(self, password: str) -> Tuple[bool, list]:
        """
        Validate password and return (is_valid, list_of_errors).
        """
        errors = []
        
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters")
        
        if self.require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if self.require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if self.require_digit and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        if self.require_special:
            special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
            if not any(c in special_chars for c in password):
                errors.append("Password must contain at least one special character")
        
        return len(errors) == 0, errors


# =============================================================================
# Demo
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Password Hashing Demo")
    print("=" * 60)
    
    password = "MySecurePassword123!"
    
    # BCrypt Demo
    print("\n=== BCrypt ===\n")
    bcrypt_manager = BCryptPasswordManager(rounds=12)
    
    start = time.time()
    bcrypt_hash = bcrypt_manager.hash(password)
    hash_time = time.time() - start
    
    print(f"Hash: {bcrypt_hash}")
    print(f"Hash time: {hash_time*1000:.2f}ms")
    print(f"Verify correct: {bcrypt_manager.verify(password, bcrypt_hash)}")
    print(f"Verify wrong: {bcrypt_manager.verify('wrong', bcrypt_hash)}")
    
    # Argon2 Demo
    print("\n=== Argon2id ===\n")
    argon2_manager = Argon2PasswordManager()
    
    start = time.time()
    argon2_hash = argon2_manager.hash(password)
    hash_time = time.time() - start
    
    print(f"Hash: {argon2_hash}")
    print(f"Hash time: {hash_time*1000:.2f}ms")
    print(f"Verify correct: {argon2_manager.verify(password, argon2_hash)}")
    print(f"Verify wrong: {argon2_manager.verify('wrong', argon2_hash)}")
    
    # Migration Demo
    print("\n=== Migration Support ===\n")
    migration_manager = MigrationPasswordManager()
    
    # Old bcrypt hash
    print(f"BCrypt needs rehash: {migration_manager.needs_rehash(bcrypt_hash)}")
    
    is_valid, new_hash = migration_manager.verify_and_update(password, bcrypt_hash)
    if new_hash:
        print(f"Migrated to: {new_hash[:50]}...")
    
    # Password Validation
    print("\n=== Password Validation ===\n")
    validator = PasswordValidator()
    
    test_passwords = [
        "weak",
        "WeakPassword",
        "weakpassword123",
        "StrongPassword123!",
    ]
    
    for pwd in test_passwords:
        is_valid, errors = validator.validate(pwd)
        status = "✓" if is_valid else "✗"
        print(f"{status} '{pwd}': {errors if errors else 'Valid'}")
    
    # Secure random
    print("\n=== Secure Random ===\n")
    print(f"Random token: {secure_random_string(32)}")
    print(f"API key: {secrets.token_urlsafe(32)}")
    
    print("\n" + "=" * 60)
