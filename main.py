import os
import random
import string
import httpx
from datetime import datetime, timedelta
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

SUPABASE_URL = "https://vlyuxgtwvfgbwaysbymv.supabase.co/rest/v1"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
SENDER_EMAIL  = "fuad.pennsl@gmail.com"
SENDER_NAME   = "PTPK Systems"

class SendOTPRequest(BaseModel):
    email: str
    target_role: Optional[str] = None

class VerifyOTPRequest(BaseModel):
    email: str
    code: str

class CheckSessionRequest(BaseModel):
    token: str

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def generate_token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=64))

def build_email_html(code: str) -> str:
    return f"""
    <html><body style="font-family: Arial, sans-serif; background: #f1f5f9; padding: 30px;">
    <div style="max-width: 420px; margin: auto; background: #ffffff; border-radius: 8px; padding: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
        <h2 style="color: #0f172a; margin-bottom: 10px;">PTPK Giriş Kodu</h2>
        <p style="color: #475569; font-size: 14px;">Sistemə daxil olmaq üçün birdəfəlik şifrəniz:</p>
        <div style="background: #f8fafc; padding: 15px; text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 5px; color: #0284c7; border: 1px solid #cbd5e1; border-radius: 6px; margin: 20px 0;">
            {code}
        </div>
        <p style="color: #94a3b8; font-size: 12px;">Bu kod 5 dəqiqə ərzində qüvvədədir. Əgər sorğunu siz etməmisinizsə, bu məktubu silə bilərsiniz.</p>
    </div>
    </body></html>
    """

@router.post("/api/auth/send-otp")
async def send_otp(req: SendOTPRequest):
    email = req.email.strip().lower()
    if not email:
        return {"status": "error", "message": "Email boş ola bilməz."}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(f"{SUPABASE_URL}/users?email=eq.{email}", headers=HEADERS)
        users = res.json()
        if not users:
            return {"status": "error", "message": "Bu email ünvanı sistemdə qeydiyyatda deyil."}
        
        user = users[0]
        if req.target_role == "komissiya" and user.get("role") != "komissiya":
            return {"status": "error", "message": "Bu səhifə yalnız Komissiya üzvləri üçündür."}
            
    except Exception as e:
        return {"status": "error", "message": "İstifadəçi təsdiqlənmə xətası."}

    otp = generate_otp()
    expires_at = (datetime.utcnow() + timedelta(minutes=5)).isoformat()

    otp_payload = {"email": email, "code": otp, "expires_at": expires_at}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{SUPABASE_URL}/otps",
                json=otp_payload,
                headers={**HEADERS, "Prefer": "resolution=merge-duplicates"}
            )
    except Exception:
        return {"status": "error", "message": "Kod sistem tərəfindən qeydə alına bilmədi."}

    email_payload = {
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "to": [{"email": email}],
        "subject": "PTPK Giriş Şifrəsi",
        "htmlContent": build_email_html(otp)
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            brevo_res = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                json=email_payload,
                headers={"api-key": BREVO_API_KEY, "Content-Type": "application/json"}
            )
        if brevo_res.status_code not in [200, 201, 202]:
            return {"status": "error", "message": "E-mail bildiriş xətası."}
    except Exception:
        return {"status": "error", "message": "E-mail provayderi ilə əlaqə qurulmadı."}

    return {"status": "success", "message": "OTP göndərildi."}

@router.post("/api/auth/verify-otp")
async def verify_otp(req: VerifyOTPRequest):
    email = req.email.strip().lower()
    code  = req.code.strip()
    now   = datetime.utcnow().isoformat()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{SUPABASE_URL}/otps?email=eq.{email}&code=eq.{code}&expires_at=gt.{now}",
                headers=HEADERS
            )
        otps = r.json()
        if not otps:
            return {"status": "error", "message": "Kod yanlışdır və ya vaxtı bitib."}

        async with httpx.AsyncClient(timeout=10.0) as client:
            ru = await client.get(f"{SUPABASE_URL}/users?email=eq.{email}", headers=HEADERS)
        users = ru.json()
        if not users:
            return {"status": "error", "message": "İstifadəçi tapılmadı."}

        user = users[0]
        role = user.get("role", "school")
        full_name = user.get("full_name", email)

        token = generate_token()
        session_expiry = (datetime.utcnow() + timedelta(hours=8)).isoformat()
        
        session_payload = {
            "token": token,
            "email": email,
            "role": role,
            "expires_at": session_expiry
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(f"{SUPABASE_URL}/sessions", json=session_payload, headers=HEADERS)

        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.delete(f"{SUPABASE_URL}/otps?email=eq.{email}", headers=HEADERS)

    except Exception as e:
        return {"status": "error", "message": "Doğrulama zamanı gözlənilməz xəta."}

    return {
        "status": "success",
        "token": token,
        "role": role,
        "full_name": full_name,
        "email": email
    }

@router.post("/api/auth/check-session")
async def check_session(req: CheckSessionRequest):
    token = req.token.strip()
    now   = datetime.utcnow().isoformat()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{SUPABASE_URL}/sessions?token=eq.{token}&expires_at=gt.{now}",
                headers=HEADERS
            )
        sessions = r.json()
        if not sessions:
            return {"status": "invalid"}
        return {"status": "valid", "email": sessions[0]["email"], "role": sessions[0]["role"]}
    except Exception:
        return {"status": "invalid"}

@router.post("/api/auth/logout")
async def logout(req: CheckSessionRequest):
    token = req.token.strip()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.delete(f"{SUPABASE_URL}/sessions?token=eq.{token}", headers=HEADERS)
    except Exception:
        pass
    return {"status": "success"}
