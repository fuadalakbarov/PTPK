import os
import time
import shutil
import httpx
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
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

app.include_router(auth_router)

UPLOAD_DIR       = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

SUPABASE_URL     = "https://vlyuxgtwvfgbwaysbymv.supabase.co/rest/v1"
SUPABASE_STORAGE = "https://vlyuxgtwvfgbwaysbymv.supabase.co/storage/v1"
SUPABASE_KEY     = os.environ.get("SUPABASE_KEY", "")
STORAGE_BUCKET   = "ptpk-files"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

CONTENT_TYPES = {
    "pdf":  "application/pdf",
    "jpg":  "image/jpeg",
    "jpeg": "image/jpeg",
    "png":  "image/png",
    "doc":  "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt":  "text/plain",
}

async def upload_to_storage(fname: str, data: bytes, ext: str) -> bool:
    """Faylı Supabase Storage-a yüklə. Uğursuz olsa lokal uploads/ qovluğuna saxla."""
    # Lokal qovluğa həmişə saxla (backup + fallback)
    local_path = os.path.join(UPLOAD_DIR, fname)
    with open(local_path, "wb") as f:
        f.write(data)

    # Supabase KEY yoxdursa, lokal saxlamaqla kifayətlən
    if not SUPABASE_KEY:
        return True

    ct = CONTENT_TYPES.get(ext.lower(), "application/octet-stream")
    url = f"{SUPABASE_STORAGE}/object/{STORAGE_BUCKET}/{fname}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": ct,
        "x-upsert": "true",
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, content=data, headers=headers)
        return r.status_code in (200, 201)
    except Exception:
        # Supabase uğursuz oldusa lokal fayl var, yenə də uğurlu sayırıq
        return True

def storage_public_url(fname: str) -> str:
    return f"{SUPABASE_STORAGE}/object/public/{STORAGE_BUCKET}/{fname}"


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

    async def save_file(upload: UploadFile, prefix: str) -> str:
        if not upload.filename or upload.filename in ("", "bos.txt"):
            return ""
        data = await upload.read()
        if len(data) == 0:
            return ""
        ext = os.path.splitext(upload.filename)[1].lstrip(".")
        fname = f"{app_id}_{prefix}.{ext}"
        ok = await upload_to_storage(fname, data, ext)
        return fname if ok else ""

    f_cover = await save_file(coverLetter, "mushayiet")
    f_res   = await save_file(residenceCertificate, "yasayis")
    f_xas   = await save_file(xasiyyetname, "xasiyyetname")
    f_id    = await save_file(idCopies, "sv_sureti")
    f_tab   = await save_file(tabel, "tabel")
    f_027   = await save_file(forma027, "forma027")

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


# Storage fayllarını proxy et (köhnə /files/ URL-ləri üçün geriyə uyğunluq)
@app.get("/files/{fname}")
async def proxy_file(fname: str):
    # Əvvəlcə lokal uploads/ qovluğunu yoxla
    local_path = os.path.join(UPLOAD_DIR, fname)
    if os.path.exists(local_path):
        ext = os.path.splitext(fname)[1].lstrip(".").lower()
        ct = CONTENT_TYPES.get(ext, "application/octet-stream")
        return FileResponse(local_path, media_type=ct,
                            headers={"Content-Disposition": f"inline; filename=\"{fname}\""})

    # Lokal yoxdursa Supabase Storage-dan cəhd et
    if SUPABASE_KEY:
        url = storage_public_url(fname)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url)
            if r.status_code == 200:
                ct = r.headers.get("content-type", "application/octet-stream")
                return __import__("fastapi").Response(content=r.content, media_type=ct)
        except Exception:
            pass

    return JSONResponse({"error": "Fayl tapılmadı"}, status_code=404)


@app.get("/{page}.html")
async def get_html(page: str):
    file_path = f"{page}.html"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return JSONResponse({"error": "not found"}, status_code=404)
