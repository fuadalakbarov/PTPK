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

# Auth router-i qoş
app.include_router(auth_router)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Supabase konfiqurasiyası
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

@app.get("/")
async def root():
    return FileResponse("login.html")

@app.get("/login")
async def login_page():
    return FileResponse("login.html")

@app.get("/image.png")
async def get_image():
    return FileResponse("image.png")

@app.get("/video.mp4")
async def get_video():
    return FileResponse("_İnklüziv təhsil_ - sosial çarx.mp4", media_type="video/mp4")

@app.post("/api/school/submit-student")
async def submit_student(
    finCode: str = Form(...),
    studentName: str = Form(...),
    schoolSelect: str = Form(...),
    applicationType: str = Form(...),
    academicYear: str = Form(...),
    coverLetter: UploadFile = File(...),
    residenceCertificate: UploadFile = File(...),
    xasiyyetname: UploadFile = File(...),
    idCopies: UploadFile = File(...),
    tabel: UploadFile = File(...),
    forma027: UploadFile = File(...),
):
    app_id = f"PTPK_{int(time.time() * 1000)}"

    def save_file(upload: UploadFile, prefix: str) -> str:
        if not upload.filename:
            return ""
        ext = os.path.splitext(upload.filename)[1]
        fname = f"{app_id}_{prefix}{ext}"
        fpath = os.path.join(UPLOAD_DIR, fname)
        with open(fpath, "wb") as f:
            shutil.copyfileobj(upload.file, f)
        return fname

    f_cover = save_file(coverLetter, "mushayiet")
    f_res   = save_file(residenceCertificate, "yasayis")
    f_xas   = save_file(xasiyyetname, "xasiyyetname")
    f_id    = save_file(idCopies, "sv_sureti")
    f_tab   = save_file(tabel, "tabel")
    f_027   = save_file(forma027, "forma027")

    payload = {
        "id": app_id,
        "fin": finCode.upper(),
        "name": studentName,
        "schoolText": schoolSelect,
        "schoolValue": schoolSelect,
        "type": applicationType + " Müraciət",
        "year": academicYear,
        "docStatus": "Tam Sənəd",
        "decisionStatus": "Gözləmədə",
        "expiryDate": "-",
        "educationForm": "-",
        "notes": "",
        "hasManualFile": 0,
        "manualFileName": "",
        "manualFileData": "",
        "coverLetter": f_cover,
        "residenceCertificate": f_res,
        "xasiyyetname": f_xas,
        "idCopies": f_id,
        "tabel": f_tab,
        "forma027": f_027
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(f"{SUPABASE_URL}/applications", json=payload, headers=HEADERS)

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

@app.get("/{page}.html")
async def get_html(page: str):
    file_path = f"{page}.html"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"detail": "Not Found"}
