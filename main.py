import os
import time
import shutil
import httpx
import random
import smtplib
from email.message import EmailMessage
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional, List
import jwt

app = FastAPI()

# CORS Ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Konfiqurasiya və Mühit Dəyişənləri
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "fuad.pennsl@gmail.com")
SMTP_PASS = os.getenv("SMTP_PASS", "")  # Sizin aldığınız 16 simvollu kod
JWT_SECRET = os.getenv("JWT_SECRET", "ptpk_secret_key_2026")

# Müvəqqəti OTP Anbarı (Yaddaşda saxlamaq üçün)
otp_store = {}

# Sənədlərin müvəqqəti saxlanma qovluğu
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class LoginRequest(BaseModel):
    email: str

class VerifyRequest(BaseModel):
    email: str
    code: str

# Supabase ilə əlaqə funksiyası
async def check_allowed_email(email: str):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    url = f"{SUPABASE_URL}/rest/v1/allowed_emails?email=eq.{email}&select=*"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0]
        return None

# OTP Kodunu E-poçta Göndərmə Funksiyası
def send_otp_email(to_email: str, code: str):
    msg = EmailMessage()
    msg["Subject"] = "PTPK Portalı - Giriş Təsdiqləmə Kodu"
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #eee; max-width: 500px; margin: auto; border-radius: 8px;">
        <h2 style="color: #1a73e8; text-align: center;">PTPK Giriş Kodu</h2>
        <p>Salam,</p>
        <p>PTPK Sisteminə daxil olmaq üçün birdəfəlik təsdiqləmə kodunuz:</p>
        <div style="text-align: center; margin: 20px 0;">
            <span style="font-size: 24px; font-weight: bold; letter-spacing: 4px; background: #f1f3f4; padding: 10px 20px; border-radius: 4px; color: #202124;">{code}</span>
        </div>
        <p style="color: #5f6368; font-size: 12px;">Bu kod 5 dəqiqə ərzində etibarlıdır. Əgər bu sorğunu siz etməmisinizsə, bu məktubu diqqətə almaya bilərsiniz.</p>
    </div>
    """
    msg.set_content(f"Sizin PTPK giriş kodunuz: {code}")
    msg.add_alternative(html_content, subtype="html")
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"SMTP Xətası: {str(e)}")
        return False

# --- AUTH API ENDPOINT-LƏRİ ---

@app.post("/api/auth/login")
async def login_request(req: LoginRequest):
    email = req.email.strip().lower()
    user_data = await check_allowed_email(email)
    
    if not user_data:
        raise HTTPException(status_code=403, detail="Bu Gmail ünvanına giriş icazəsi yoxdur!")
        
    otp_code = str(random.randint(100000, 999999))
    otp_store[email] = {"code": otp_code, "expires": time.time() + 300}
    
    if send_otp_email(email, otp_code):
        return {"status": "success", "message": "OTP kod e-poçtunuza göndərildi."}
    else:
        raise HTTPException(status_code=500, detail="E-poçt göndərilərkən xəta baş verdi.")

@app.post("/api/auth/verify")
async def verify_request(req: VerifyRequest):
    email = req.email.strip().lower()
    code = req.code.strip()
    
    if email not in otp_store:
        raise HTTPException(status_code=400, detail="Aktiv giriş sorğusu tapılmadı.")
        
    data = otp_store[email]
    if time.time() > data["expires"]:
        del otp_store[email]
        raise HTTPException(status_code=400, detail="Kodun vaxtı bitib, yenidən cəhd edin.")
        
    if data["code"] != code:
        raise HTTPException(status_code=400, detail="Daxil etdiyiniz təsdiqləmə kodu yanlışdır.")
        
    # Uğurlu giriş - Rol məlumatını götürək
    user_data = await check_allowed_email(email)
    role = user_data.get("role", "user") if user_data else "user"
    
    # JWT Token Yaradılması
    token = jwt.encode({"email": email, "role": role, "exp": time.time() + 86400}, JWT_SECRET, algorithm="HS256")
    
    # Yaddaşı təmizlə
    del otp_store[email]
    
    return {"status": "success", "token": token, "role": role, "redirect": "/index.html"}

# --- STATİK VƏ ROOT MARŞRUTLAR (Render 404 Problem təmizləməsi) ---

@app.get("/")
async def root():
    return RedirectResponse(url="/login.html")

@app.get("/{filename}")
async def serve_static_html(filename: str):
    # Əgər uzantısı yoxdursa və mövcud fayldırsa .html əlavə et və ya birbaşa yoxla
    file_path = filename
    if not filename.endswith(".html") and not "." in filename:
        file_path = f"{filename}.html"
        
    if os.path.exists(file_path):
        return FileResponse(file_path)
        
    # Fayl diskdə yoxdursa login-ə yönləndir
    return RedirectResponse(url="/login.html")

# Hər hansı digər alt qovluq və ya fayl müraciətləri üçün universal tutucu
@app.get("/{full_path:path}")
async def catch_all_paths(full_path: str):
    if os.path.exists(full_path):
        return FileResponse(full_path)
    if os.path.exists(f"{full_path}.html"):
        return FileResponse(f"{full_path}.html")
    return RedirectResponse(url="/login.html")
