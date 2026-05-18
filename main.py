# --- STATİK VƏ ROOT MARŞRUTLAR ---

@app.get("/")
async def root():
    if os.path.exists("login.html"):
        return FileResponse("login.html")
    return JSONResponse({"message": "PTPK API is running, but login.html not found"})

@app.get("/login.html")
async def serve_login():
    if os.path.exists("login.html"):
        return FileResponse("login.html")
    raise HTTPException(status_code=404, detail="login.html faylı serverdə tapılmadı!")

@app.get("/admin.html")
async def serve_admin():
    if os.path.exists("admin.html"):
        return FileResponse("admin.html")
    raise HTTPException(status_code=404, detail="admin.html faylı serverdə tapılmadı!")

@app.get("/index.html")
async def serve_index():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    raise HTTPException(status_code=404, detail="index.html faylı serverdə tapılmadı!")

@app.get("/komissiya.html")
async def serve_komissiya():
    if os.path.exists("komissiya.html"):
        return FileResponse("komissiya.html")
    raise HTTPException(status_code=404, detail="komissiya.html faylı serverdə tapılmadı!")
