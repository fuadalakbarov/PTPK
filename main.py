import sqlite3
import os
import shutil
import time
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "ptpk.db"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY,
            fin TEXT, name TEXT, schoolText TEXT, schoolValue TEXT,
            type TEXT, year TEXT,
            docStatus TEXT DEFAULT "Tam Sənəd",
            decisionStatus TEXT DEFAULT "Gözləmədə",
            expiryDate TEXT DEFAULT "-",
            educationForm TEXT DEFAULT "-",
            notes TEXT DEFAULT "",
            hasManualFile INTEGER DEFAULT 0,
            manualFileName TEXT DEFAULT "",
            manualFileData TEXT DEFAULT "",
            coverLetter TEXT DEFAULT "",
            residenceCertificate TEXT DEFAULT "",
            xasiyyetname TEXT DEFAULT "",
            idCopies TEXT DEFAULT "",
            tabel TEXT DEFAULT "",
            forma027 TEXT DEFAULT ""
        )
    ''')
    try:
        cursor.execute("ALTER TABLE applications ADD COLUMN manualFileData TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    conn.commit()
    conn.close()

init_db()

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
    return FileResponse("index.html")

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

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO applications
        (id, fin, name, schoolText, schoolValue, type, year,
         docStatus, decisionStatus, expiryDate, educationForm, notes,
         hasManualFile, manualFileName, manualFileData,
         coverLetter, residenceCertificate, xasiyyetname, idCopies, tabel, forma027)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        app_id, finCode.upper(), studentName,
        schoolSelect, schoolSelect,
        applicationType + " Müraciət",
        academicYear,
        "Tam Sənəd", "Gözləmədə", "-", "-", "",
        0, "", "",
        f_cover, f_res, f_xas, f_id, f_tab, f_027
    ))
    conn.commit()
    conn.close()
    return {"status": "success", "id": app_id}

@app.get("/api/komissiya/get-applications")
async def get_applications():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications ORDER BY schoolText, name")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/komissiya/update-decision")
async def update_decision(data: DecisionUpdate):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if data.manualFileData:
        cursor.execute('''
            UPDATE applications
            SET decisionStatus = ?, educationForm = ?, notes = ?, expiryDate = ?,
                hasManualFile = 1, manualFileName = ?, manualFileData = ?
            WHERE id = ?
        ''', (data.decisionStatus, data.educationForm, data.notes, data.expiryDate,
              data.manualFileName or "", data.manualFileData, data.id))
    else:
        cursor.execute('''
            UPDATE applications
            SET decisionStatus = ?, educationForm = ?, notes = ?, expiryDate = ?
            WHERE id = ?
        ''', (data.decisionStatus, data.educationForm, data.notes, data.expiryDate, data.id))

    conn.commit()
    conn.close()
    return {"status": "success"}

@app.delete("/api/komissiya/delete-application")
async def delete_application(id: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM applications WHERE id = ?", (id,))
    conn.commit()
    conn.close()
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