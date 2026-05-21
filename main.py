import os
import time
import shutil
import httpx
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
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

def HEADERS():
    _key = os.environ.get("SUPABASE_KEY", "")
    return {
        "apikey": _key,
        "Authorization": f"Bearer {_key}",
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
    """Faylı Supabase Storage-a yüklə."""
    if not SUPABASE_KEY:
        print(f"[XETA] SUPABASE_KEY muhit deyisheni teyinedilmeyib! Fayl saxlanilmadi: {fname}")
        return False

    ct = CONTENT_TYPES.get(ext.lower(), "application/octet-stream")
    url = f"{SUPABASE_STORAGE}/object/{STORAGE_BUCKET}/{fname}"
    headers = {
        "apikey": os.environ.get("SUPABASE_KEY",""),
        "Authorization": "Bearer " + os.environ.get("SUPABASE_KEY",""),
        "Content-Type": ct,
        "x-upsert": "true",
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, content=data, headers=headers)
        if r.status_code in (200, 201):
            print(f"[OK] Supabase Storage-a yuklendi: {fname}")
            return True
        else:
            print(f"[XETA] Supabase Storage cavabi {r.status_code}: {r.text[:300]}")
            return False
    except Exception as e:
        print(f"[XETA] Supabase Storage baglanti xetasi: {e}")
        return False

def storage_public_url(fname: str) -> str:
    return f"{SUPABASE_STORAGE}/object/public/{STORAGE_BUCKET}/{fname}"


class DecisionUpdate(BaseModel):
    id: str
    decisionStatus: str
    educationForm: str
    notes: str
    expiryDate: str
    docError: Optional[str] = None
    docErrorChecks: Optional[str] = None
    docErrorNote: Optional[str] = None
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
        r = await client.post(f"{SUPABASE_URL}/applications", json=payload, headers=HEADERS())

    return {"status": "success", "id": app_id}


@app.get("/api/komissiya/get-applications")
async def get_applications():
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{SUPABASE_URL}/applications?order=schoolText.asc,name.asc",
            headers=HEADERS()
        )
    data = r.json()
    if not isinstance(data, list):
        raise HTTPException(status_code=502, detail=f"Supabase xetasi: {str(data)[:200]}")
    for item in data:
        item.pop("manualFileData", None)
    return data


@app.get("/api/komissiya/get-file")
async def get_file(id: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{SUPABASE_URL}/applications?id=eq.{id}&select=id,manualFileData,manualFileName,hasManualFile",
            headers=HEADERS()
        )
    data = r.json()
    if not isinstance(data, list) or len(data) == 0:
        raise HTTPException(status_code=404, detail="Tapilmadi")
    return data[0]


@app.post("/api/komissiya/update-decision")
async def update_decision(data: DecisionUpdate):
    payload = {
        "decisionStatus": data.decisionStatus,
        "educationForm": data.educationForm,
        "notes": data.notes,
        "expiryDate": data.expiryDate,
        "docError": data.docError or "",
        "docErrorChecks": data.docErrorChecks or "",
        "docErrorNote": data.docErrorNote or "",
    }
    if data.manualFileData:
        payload["manualFileData"] = data.manualFileData
        payload["manualFileName"] = data.manualFileName or ""
        payload["hasManualFile"] = 1

    async with httpx.AsyncClient() as client:
        r = await client.patch(
            f"{SUPABASE_URL}/applications?id=eq.{data.id}",
            json=payload,
            headers=HEADERS()
        )
    if r.status_code not in (200, 204):
        raise HTTPException(status_code=500, detail=f"Supabase xetasi: {r.status_code}")
    updated = r.json()
    if isinstance(updated, list) and len(updated) == 0:
        raise HTTPException(status_code=404, detail=f"ID tapilmadi: {data.id}")
    return {"status": "success"}


@app.delete("/api/komissiya/delete-application")
async def delete_application(id: str):
    async with httpx.AsyncClient() as client:
        await client.delete(
            f"{SUPABASE_URL}/applications?id=eq.{id}",
            headers=HEADERS()
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




@app.get("/api/debug/storage-check")
async def debug_storage():
    """Supabase KEY ve Storage vəziyyətini yoxla"""
    key_set = bool(SUPABASE_KEY)
    key_preview = (SUPABASE_KEY[:8] + "...") if key_set else "YOX"
    
    # Bucket-e test sorgu
    bucket_ok = False
    bucket_msg = ""
    if key_set:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"{SUPABASE_STORAGE}/bucket/{STORAGE_BUCKET}",
                    headers={"apikey": os.environ.get("SUPABASE_KEY",""), "Authorization": "Bearer " + os.environ.get("SUPABASE_KEY","")}
                )
            bucket_ok = r.status_code == 200
            bucket_msg = f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as e:
            bucket_msg = str(e)
    
    return {
        "supabase_key_set": key_set,
        "supabase_key_preview": key_preview,
        "bucket": STORAGE_BUCKET,
        "bucket_accessible": bucket_ok,
        "bucket_response": bucket_msg,
        "supabase_url": SUPABASE_URL,
    }
@app.get("/{page}.html")
async def get_html(page: str):
    file_path = f"{page}.html"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return JSONResponse({"error": "not found"}, status_code=404)


# ── Məktəbin sənədi yenidən göndərməsi ──
@app.post("/api/school/resubmit-docs")
async def resubmit_docs(
    appId: str = Form(...),
    coverLetter: UploadFile = File(None),
    residenceCertificate: UploadFile = File(None),
    xasiyyetname: UploadFile = File(None),
    idCopies: UploadFile = File(None),
    tabel: UploadFile = File(None),
    forma027: UploadFile = File(None),
):
    field_map = {
        "coverLetter": (coverLetter, "mushayiet"),
        "residenceCertificate": (residenceCertificate, "yasayis"),
        "xasiyyetname": (xasiyyetname, "xasiyyetname"),
        "idCopies": (idCopies, "sv_sureti"),
        "tabel": (tabel, "tabel"),
        "forma027": (forma027, "forma027"),
    }

    payload = {}
    for key, (upload, prefix) in field_map.items():
        if upload and upload.filename and upload.filename not in ("", "bos.txt"):
            data = await upload.read()
            if len(data) > 0:
                ext = os.path.splitext(upload.filename)[1].lstrip(".")
                fname = f"{appId}_{prefix}.{ext}"
                ok = await upload_to_storage(fname, data, ext)
                if ok:
                    payload[key] = fname

    if not payload:
        return JSONResponse({"error": "Heç bir fayl göndərilmədi"}, status_code=400)

    # Sənəd yenidən göndərildikdə komissiyaya bildiriş üçün status yenilə
    payload["docError"] = ""
    payload["decisionStatus"] = "Yeni Sənəd ⚡"

    async with httpx.AsyncClient() as client:
        r = await client.patch(
            f"{SUPABASE_URL}/applications?id=eq.{appId}",
            json=payload,
            headers=HEADERS()
        )

    return {"status": "success", "updated": list(payload.keys())}
