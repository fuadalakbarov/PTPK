import os
import random
import string
import httpx
from datetime import datetime, timedelta
from fastapi import APIRouter
from pydantic import BaseModel

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
SENDER_NAME   = "PTPK"


class SendOTPRequest(BaseModel):
    email: str

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
    <div style="max-width: 420px; margin: auto; background: #ffffff; border-radius: 12px;
                border: 2px solid #0f172a; overflow: hidden;">
        <div style="background: #0f172a; padding: 20px 24px;">
            <h2 style="color: #ffffff; margin: 0; font-size: 18px;">PTPK Giriş Kodu</h2>
            <p style="color: #94a3b8; margin: 4px 0 0; font-size: 13px;">
                Psixoloji-Tibbi-Pedaqoji Komissiya</p>
        </div>
        <div style="padding: 28px 24px; text-align: center;">
            <p style="color: #475569; font-size: 14px; margin-bottom: 20px;">
                Sistemə giriş üçün aşağıdakı 6 rəqəmli kodu daxil edin:</p>
            <div style="background: #f0f9ff; border: 2px solid #0284c7; border-radius: 10px;
                        padding: 18px; display: inline-block;">
                <span style="font-size: 38px; font-weight: 900; letter-spacing: 10px;
                             color: #0f172a; font-family: monospace;">{code}</span>
            </div>
            <p style="color: #94a3b8; font-size: 12px; margin-top: 20px;">
                Bu kod 10 dəqiqə ərzində etibarlıdır.</p>
        </div>
        <div style="background: #f8fafc; padding: 14px 24px; border-top: 1px solid #e2e8f0;">
            <p style="color: #94a3b8; font-size: 11px; margin: 0; text-align: center;">
                © 2026 PTPK | by F.Alakbarov</p>
        </div>
    </div>
    </body></html>
    """


@router.post("/api/auth/send-otp")
async def send_otp(req: SendOTPRequest):
    email = req.email.strip().lower()

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            # 1. İstifadəçi mövcuddurmu?
            r = await client.get(
                f"{SUPABASE_URL}/allowed_emails?email=eq.{email}",
                headers=HEADERS
            )
            users = r.json()
            if not users or len(users) == 0:
                return {"status": "error", "message": "Bu e-poçt ünvanı sistemdə qeydiyyatlı deyil."}

            user = users[0]
            code = generate_otp()
            expires_at = (datetime.utcnow() + timedelta(minutes=10)).isoformat()

            # 2. Köhnə OTP-ni sil, yenisini yaz
            await client.delete(
                f"{SUPABASE_URL}/otp_codes?email=eq.{email}",
                headers=HEADERS
            )
            await client.post(
                f"{SUPABASE_URL}/otp_codes",
                json={"email": email, "code": code, "expires_at": expires_at, "used": False},
                headers=HEADERS
            )

            # 3. Brevo ilə email göndər
            r2 = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                json={
                    "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
                    "to": [{"email": email}],
                    "subject": f"PTPK Giriş Kodu: {code}",
                    "htmlContent": build_email_html(code)
                },
                headers={
                    "api-key": BREVO_API_KEY,
                    "Content-Type": "application/json"
                }
            )
            if r2.status_code >= 400:
                return {"status": "error", "message": f"Email göndərilmədi: {r2.text}"}

    except httpx.TimeoutException:
        return {"status": "error", "message": "Server cavab vermədi. Bir az sonra yenidən cəhd edin."}
    except Exception as e:
        return {"status": "error", "message": f"Xəta baş verdi: {str(e)}"}

    return {
        "status": "success",
        "message": "Kod göndərildi",
        "role": user.get("role", "user"),
        "full_name": user.get("name", "")
    }


@router.post("/api/auth/verify-otp")
async def verify_otp(req: VerifyOTPRequest):
    email = req.email.strip().lower()
    code  = req.code.strip()
    now   = datetime.utcnow().isoformat()

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            # 1. OTP yoxla
            r = await client.get(
                f"{SUPABASE_URL}/otp_codes?email=eq.{email}&code=eq.{code}&used=eq.false&expires_at=gt.{now}",
                headers=HEADERS
            )
            records = r.json()
            if not records or len(records) == 0:
                return {"status": "error", "message": "Kod yanlışdır və ya müddəti bitib."}

            otp_id = records[0]["id"]

            # 2. OTP-ni istifadə edilmiş işarələ + istifadəçini al
            await client.patch(
                f"{SUPABASE_URL}/otp_codes?id=eq.{otp_id}",
                json={"used": True},
                headers=HEADERS
            )
            r2 = await client.get(
                f"{SUPABASE_URL}/allowed_emails?email=eq.{email}",
                headers=HEADERS
            )
            users = r2.json()
            if not users:
                return {"status": "error", "message": "İstifadəçi tapılmadı."}

            user      = users[0]
            role      = user.get("role", "user")
            full_name = user.get("name", "")
            token     = generate_token()
            expires_at = (datetime.utcnow() + timedelta(hours=8)).isoformat()

            # 3. Session yaz
            await client.post(
                f"{SUPABASE_URL}/sessions",
                json={"token": token, "email": email, "role": role, "expires_at": expires_at},
                headers=HEADERS
            )

    except httpx.TimeoutException:
        return {"status": "error", "message": "Server cavab vermədi. Bir az sonra yenidən cəhd edin."}
    except Exception as e:
        return {"status": "error", "message": f"Xəta baş verdi: {str(e)}"}

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
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{SUPABASE_URL}/sessions?token=eq.{token}&expires_at=gt.{now}",
                headers=HEADERS
            )
        sessions = r.json()
        if not sessions or len(sessions) == 0:
            return {"status": "invalid"}

        s = sessions[0]
        return {
            "status": "valid",
            "email": s["email"],
            "role":  s["role"]
        }

    except Exception:
        return {"status": "invalid"}


@router.post("/api/auth/logout")
async def logout(req: CheckSessionRequest):
    token = req.token.strip()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.delete(
                f"{SUPABASE_URL}/sessions?token=eq.{token}",
                headers=HEADERS
            )
    except Exception:
        pass
    return {"status": "ok"}
