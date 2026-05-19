import os
import time
import shutil
import httpx
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from auth_routes import router as auth_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Autentifikasiya API endpoint-lərini bura daxil edirik
app.include_router(auth_router)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

SUPABASE_URL = "https://vlyuxgtwvfgbwaysbymv.supabase.co/rest/v1"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

class DecisionUpdate(BaseModel):
    id: str
    decisionStatus: str
    educationForm: str
    notes: str
    expiryDate: str
    manualFileData: Optional[str] = None
    manualFileName: Optional[str] = None

# ==========================================
# SƏHİFƏLƏRİN MARŞRUTLARI (PAGE ROUTES)
# ==========================================

@app.get("/")
async def root():
    # Əsas ana səhifə məktəblərin giriş səhifəsi olur
    return FileResponse("login.html")

@app.get("/login")
async def login_page():
    # Məktəblər üçün ümumi giriş linki
    return FileResponse("login.html")

@app.get("/login/komissiya")
async def komissiya_login_page():
    # Komissiya üzvləri üçün tamamilə ayrıca giriş səhifəsi
    return FileResponse("login-komissiya.html")

@app.get("/komissiya")
async def komissiya_page():
    # Komissiyanın əsas idarəetmə paneli
    return FileResponse("komissiya (1).html")

@app.get("/index")
async def index_page():
    # Məktəblərin sənəd göndərmə paneli
    return FileResponse("index (1).html")


# ==========================================
# APPLİCATİON API ENDPOINT-LƏRİ
# ==========================================

@app.post("/api/school/submit-student")
async def submit_student(
    finCode: str = Form(...),
    studentName: str = Form(...),
    schoolSelect: str = Form(...),
    schoolText: str = Form(...),
    birthDate: str = Form(...),
    gender: str = Form(...),
    parentName: str = Form(...),
    parentPhone: str = Form(...),
    district: str = Form(...),
    year: str = Form(...),
    coverLetter: UploadFile = File(...),
    residenceCertificate: UploadFile = File(...),
    xasiyyetname: UploadFile = File(...),
    idCopies: UploadFile = File(...),
    tabel: UploadFile = File(...),
    forma027: UploadFile = File(...)
):
    app_id = f"app_{int(time.time())}"
    
    # Faylları yadda saxlayırıq
    files_dict = {
        "coverLetter": coverLetter,
        "residenceCertificate": residenceCertificate,
        "xasiyyetname": xasiyyetname,
        "idCopies": idCopies,
        "tabel": tabel,
        "forma027": forma027
    }

    saved_paths = {}
    for key, f in files_dict.items():
        ext = os.path.splitext(f.filename)[1]
        filename = f"{app_id}_{key}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(f.file, buffer)
        saved_paths[key] = f"/files/{filename}"

    payload = {
        "id": app_id,
        "fin": finCode,
        "name": studentName,
        "schoolSelect": schoolSelect,
        "schoolText": schoolText,
        "birthDate": birthDate,
        "gender": gender,
        "parentName": parentName,
        "parentPhone": parentPhone,
        "district": district,
        "year": year,
        "coverLetter": saved_paths["coverLetter"],
        "residenceCertificate": saved_paths["residenceCertificate"],
        "xasiyyetname": saved_paths["xasiyyetname"],
        "idCopies": saved_paths["idCopies"],
        "tabel": saved_paths["tabel"],
        "forma027": saved_paths["forma027"],
        "docStatus": "Yoxlanılıb",
        "decisionStatus": "Gözləmədə",
        "educationForm": "-",
        "notes": "-",
        "expiryDate": "-",
        "hasManualFile": 0,
        "manualFileData": "",
        "manualFileName": ""
    }

    async with httpx.AsyncClient() as client:
        await client.post(f"{SUPABASE_URL}/applications", json=payload, headers=HEADERS)

    return {"status": "success", "id": app_id}

@app.get("/api/komissiya/get-applications")
async def get_applications():
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{SUPABASE_URL}/applications?order=schoolText.asc,name.asc",
            headers=HEADERS
        )
    return r.json()

@app.post("/api/komissiya/update-decision")
async def update_decision(data: DecisionUpdate):
    payload = {
        "decisionStatus": data.decisionStatus,
        "educationForm": data.educationForm,
        "notes": data.notes,
        "expiryDate": data.expiryDate,
    }
    if data.manualFileData:
        payload["manualFileData"] = data.manualFileData
        payload["manualFileName"] = data.manualFileName or ""
        payload["hasManualFile"] = 1

    async with httpx.AsyncClient() as client:
        r = await client.patch(
            f"{SUPABASE_URL}/applications?id=eq.{data.id}",
            json=payload,
            headers=HEADERS
        )
    return {"status": "success"}

@app.delete("/api/komissiya/delete-application")
async def delete_application(id: str):
    async with httpx.AsyncClient() as client:
        await client.delete(
            f"{SUPABASE_URL}/applications?id=eq.{id}",
            headers=HEADERS
        )
    return {"status": "deleted"}

try:
    app.mount("/files", StaticFiles(directory=UPLOAD_DIR), name="files")
except Exception:
    pass
