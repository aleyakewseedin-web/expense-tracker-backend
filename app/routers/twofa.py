from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import pyotp
import qrcode
import io
import base64
from app.database import get_db
from app.models.user import User
from app.dependencies import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/auth/2fa", tags=["2FA"])

class TOTPVerify(BaseModel):
    code: str

class TOTPLogin(BaseModel):
    email: str
    password: str
    code: str

@router.post("/setup")
def setup_2fa(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.is_2fa_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")

    # Generate secret
    secret = pyotp.random_base32()
    current_user.totp_secret = secret
    db.commit()

    # Generate QR code
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(
        name=current_user.email,
        issuer_name="ExpenseTracker"
    )

    qr = qrcode.make(uri)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return {
        "secret": secret,
        "qr_code": f"data:image/png;base64,{qr_base64}",
        "message": "Scan the QR code with Google Authenticator, then call POST /auth/2fa/verify to confirm"
    }


@router.post("/verify")
def verify_2fa(
    data: TOTPVerify,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA setup not started. Call POST /auth/2fa/setup first")

    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(data.code):
        raise HTTPException(status_code=400, detail="Invalid code. Please try again.")

    current_user.is_2fa_enabled = True
    db.commit()
    return {"message": "2FA enabled successfully"}


@router.post("/disable")
def disable_2fa(
    data: TOTPVerify,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_2fa_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")

    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(data.code):
        raise HTTPException(status_code=400, detail="Invalid code")

    current_user.is_2fa_enabled = False
    current_user.totp_secret = None
    db.commit()
    return {"message": "2FA disabled successfully"}