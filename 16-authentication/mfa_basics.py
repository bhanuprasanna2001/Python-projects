"""
Multi-Factor Authentication (MFA) Basics
========================================
TOTP (Time-based One-Time Password) implementation.
"""

from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, Dict
import pyotp
import qrcode
import qrcode.image.svg
from io import BytesIO
import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import secrets


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class MFAConfig:
    issuer: str = "MyApp"
    digits: int = 6
    interval: int = 30  # seconds
    valid_window: int = 1  # Allow 1 period before/after


config = MFAConfig()


# =============================================================================
# TOTP Service
# =============================================================================

class TOTPService:
    """
    Time-based One-Time Password service.
    Compatible with Google Authenticator, Authy, etc.
    """
    
    def __init__(self, config: MFAConfig = config):
        self.config = config
    
    def generate_secret(self) -> str:
        """Generate a new TOTP secret."""
        return pyotp.random_base32()
    
    def get_totp(self, secret: str) -> pyotp.TOTP:
        """Get TOTP instance for a secret."""
        return pyotp.TOTP(
            secret,
            digits=self.config.digits,
            interval=self.config.interval,
        )
    
    def generate_code(self, secret: str) -> str:
        """Generate current TOTP code."""
        totp = self.get_totp(secret)
        return totp.now()
    
    def verify_code(self, secret: str, code: str) -> bool:
        """
        Verify a TOTP code.
        Uses valid_window to allow for time drift.
        """
        totp = self.get_totp(secret)
        return totp.verify(code, valid_window=self.config.valid_window)
    
    def get_provisioning_uri(
        self,
        secret: str,
        email: str,
        issuer: Optional[str] = None
    ) -> str:
        """
        Get provisioning URI for authenticator apps.
        Format: otpauth://totp/ISSUER:EMAIL?secret=SECRET&issuer=ISSUER
        """
        totp = self.get_totp(secret)
        return totp.provisioning_uri(
            name=email,
            issuer_name=issuer or self.config.issuer,
        )
    
    def generate_qr_code(
        self,
        secret: str,
        email: str,
        issuer: Optional[str] = None,
        format: str = "png"
    ) -> bytes:
        """Generate QR code for authenticator setup."""
        uri = self.get_provisioning_uri(secret, email, issuer)
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        if format == "svg":
            img = qr.make_image(image_factory=qrcode.image.svg.SvgImage)
        else:
            img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()
    
    def generate_qr_code_base64(
        self,
        secret: str,
        email: str,
        issuer: Optional[str] = None
    ) -> str:
        """Generate QR code as base64 string for HTML embedding."""
        qr_bytes = self.generate_qr_code(secret, email, issuer, format="png")
        return base64.b64encode(qr_bytes).decode()
    
    def time_remaining(self) -> int:
        """Get seconds remaining until next code."""
        return self.config.interval - (int(datetime.now(timezone.utc).timestamp()) % self.config.interval)


totp_service = TOTPService()


# =============================================================================
# Backup Codes Service
# =============================================================================

class BackupCodesService:
    """
    Backup codes for account recovery when TOTP is unavailable.
    """
    
    @staticmethod
    def generate_codes(count: int = 10) -> list:
        """Generate a set of backup codes."""
        codes = []
        for _ in range(count):
            # Format: XXXX-XXXX (8 characters)
            code = secrets.token_hex(4).upper()
            formatted = f"{code[:4]}-{code[4:]}"
            codes.append(formatted)
        return codes
    
    @staticmethod
    def hash_code(code: str) -> str:
        """Hash a backup code for storage."""
        import hashlib
        # Remove formatting
        clean_code = code.replace("-", "").lower()
        return hashlib.sha256(clean_code.encode()).hexdigest()
    
    @staticmethod
    def verify_code(code: str, hashed_codes: list) -> tuple:
        """
        Verify a backup code.
        Returns (is_valid, matched_hash_to_remove).
        """
        code_hash = BackupCodesService.hash_code(code)
        if code_hash in hashed_codes:
            return True, code_hash
        return False, None


# =============================================================================
# Models
# =============================================================================

class MFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    qr_code_base64: str
    backup_codes: list


class MFAVerifyRequest(BaseModel):
    code: str


class MFAEnableRequest(BaseModel):
    code: str  # Verify code before enabling


# =============================================================================
# Fake User Database with MFA
# =============================================================================

fake_users_db = {
    "user1": {
        "id": "user1",
        "email": "user@example.com",
        "mfa_enabled": False,
        "mfa_secret": None,
        "backup_codes_hashed": [],
    },
}


def get_user(user_id: str) -> Optional[dict]:
    return fake_users_db.get(user_id)


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(title="MFA Authentication API")


# Simulated current user (in production, get from session/JWT)
def get_current_user_id() -> str:
    return "user1"


# =============================================================================
# MFA Endpoints
# =============================================================================

@app.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(user_id: str = Depends(get_current_user_id)):
    """
    Step 1: Initialize MFA setup.
    Returns secret, QR code, and backup codes.
    User must verify with a code before MFA is enabled.
    """
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user["mfa_enabled"]:
        raise HTTPException(status_code=400, detail="MFA already enabled")
    
    # Generate new secret
    secret = totp_service.generate_secret()
    
    # Generate QR code
    qr_code = totp_service.generate_qr_code_base64(secret, user["email"])
    
    # Generate provisioning URI
    uri = totp_service.get_provisioning_uri(secret, user["email"])
    
    # Generate backup codes
    backup_codes = BackupCodesService.generate_codes(10)
    
    # Store secret temporarily (not yet enabled)
    user["mfa_secret"] = secret
    user["backup_codes_hashed"] = [
        BackupCodesService.hash_code(code) for code in backup_codes
    ]
    
    return MFASetupResponse(
        secret=secret,
        provisioning_uri=uri,
        qr_code_base64=qr_code,
        backup_codes=backup_codes,
    )


@app.post("/mfa/enable")
async def enable_mfa(
    request: MFAEnableRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Step 2: Enable MFA after verifying setup.
    User must enter a valid code from their authenticator.
    """
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user["mfa_enabled"]:
        raise HTTPException(status_code=400, detail="MFA already enabled")
    
    if not user["mfa_secret"]:
        raise HTTPException(status_code=400, detail="MFA not set up. Call /mfa/setup first")
    
    # Verify the code
    if not totp_service.verify_code(user["mfa_secret"], request.code):
        raise HTTPException(status_code=400, detail="Invalid code")
    
    # Enable MFA
    user["mfa_enabled"] = True
    
    return {"message": "MFA enabled successfully"}


@app.post("/mfa/verify")
async def verify_mfa(
    request: MFAVerifyRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Verify MFA code during login.
    """
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user["mfa_enabled"]:
        raise HTTPException(status_code=400, detail="MFA not enabled")
    
    # Try TOTP code first
    if totp_service.verify_code(user["mfa_secret"], request.code):
        return {"message": "MFA verified", "method": "totp"}
    
    # Try backup code
    is_valid, code_hash = BackupCodesService.verify_code(
        request.code, user["backup_codes_hashed"]
    )
    
    if is_valid:
        # Remove used backup code
        user["backup_codes_hashed"].remove(code_hash)
        remaining = len(user["backup_codes_hashed"])
        
        return {
            "message": "MFA verified with backup code",
            "method": "backup",
            "backup_codes_remaining": remaining,
        }
    
    raise HTTPException(status_code=400, detail="Invalid code")


@app.delete("/mfa/disable")
async def disable_mfa(
    request: MFAVerifyRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Disable MFA (requires current code).
    """
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user["mfa_enabled"]:
        raise HTTPException(status_code=400, detail="MFA not enabled")
    
    # Verify code before disabling
    if not totp_service.verify_code(user["mfa_secret"], request.code):
        raise HTTPException(status_code=400, detail="Invalid code")
    
    # Disable MFA
    user["mfa_enabled"] = False
    user["mfa_secret"] = None
    user["backup_codes_hashed"] = []
    
    return {"message": "MFA disabled"}


@app.post("/mfa/regenerate-backup-codes")
async def regenerate_backup_codes(
    request: MFAVerifyRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Generate new backup codes (requires current MFA code).
    """
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user["mfa_enabled"]:
        raise HTTPException(status_code=400, detail="MFA not enabled")
    
    # Verify code
    if not totp_service.verify_code(user["mfa_secret"], request.code):
        raise HTTPException(status_code=400, detail="Invalid code")
    
    # Generate new backup codes
    new_codes = BackupCodesService.generate_codes(10)
    user["backup_codes_hashed"] = [
        BackupCodesService.hash_code(code) for code in new_codes
    ]
    
    return {
        "message": "Backup codes regenerated",
        "backup_codes": new_codes,
    }


@app.get("/mfa/status")
async def mfa_status(user_id: str = Depends(get_current_user_id)):
    """
    Get MFA status for current user.
    """
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "mfa_enabled": user["mfa_enabled"],
        "backup_codes_remaining": len(user["backup_codes_hashed"]) if user["mfa_enabled"] else 0,
    }


# =============================================================================
# Demo Endpoints
# =============================================================================

@app.get("/demo/generate-code")
async def demo_generate_code(user_id: str = Depends(get_current_user_id)):
    """
    Demo: Generate current TOTP code (for testing).
    In production, this would be on the user's device.
    """
    user = get_user(user_id)
    if not user or not user["mfa_secret"]:
        raise HTTPException(status_code=400, detail="MFA not set up")
    
    code = totp_service.generate_code(user["mfa_secret"])
    remaining = totp_service.time_remaining()
    
    return {
        "code": code,
        "valid_for_seconds": remaining,
    }


@app.get("/")
async def root():
    return {
        "message": "MFA API",
        "flow": [
            "1. POST /mfa/setup - Get secret and QR code",
            "2. POST /mfa/enable - Verify and enable MFA",
            "3. POST /mfa/verify - Verify MFA during login",
        ],
    }


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ================================================
    MFA Authentication API
    ================================================
    
    MFA Setup Flow:
    1. POST /mfa/setup - Get QR code and backup codes
    2. Scan QR code with Google Authenticator/Authy
    3. POST /mfa/enable with code from app
    
    Login Flow:
    1. Regular login (username/password)
    2. POST /mfa/verify with TOTP code
    
    OpenAPI docs: http://localhost:8000/docs
    ================================================
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
