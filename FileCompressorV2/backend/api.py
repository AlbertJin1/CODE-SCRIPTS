# backend/api.py
import os, shutil, tempfile, uuid, asyncio
from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from core.image_compressor import compress_image
from core.pdf_compressor import compress_pdf_to_target
from core.office_compressor import compress_office_to_target
from utils.helpers import get_compressed_name

app = FastAPI()
app.mount("/static", StaticFiles(directory="static", html=True), name="static")


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})


def json_stream(**kw):
    import json

    yield json.dumps(kw) + "\n"


async def progress_cb(pct: int, txt: str):
    yield json_stream(progress=pct, status=txt)


@app.post("/compress")
async def compress(
    file: UploadFile = File(...),
    mode: str = Form("percent"),
    percent: int = Form(75),
    target_mb: float = Form(2.0),
):
    # 1. Save upload
    suffix = os.path.splitext(file.filename)[1].lower()
    tmp_input = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    shutil.copyfileobj(file.file, tmp_input)
    tmp_input.close()

    # 2. Prepare output
    out_name = get_compressed_name(tmp_input.name)
    tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp_out.close()

    # 3. Choose target size
    orig_bytes = os.path.getsize(tmp_input.name)
    if mode == "percent" or orig_bytes < 1024 * 1024:
        target_bytes = orig_bytes * (100 - percent) / 100
    else:
        target_bytes = target_mb * 1024 * 1024

    # 4. Stream progress + final file
    async def stream():
        async for chunk in progress_cb(0, "Analyzing…"):
            yield chunk

        try:
            ext = suffix
            success = False
            final_path = ""

            if ext == ".pdf":
                success, size = await asyncio.to_thread(
                    compress_pdf_to_target,
                    tmp_input.name,
                    tmp_out.name,
                    int(target_bytes),
                    lambda p, t: asyncio.run(progress_cb(p, t)),
                )
                final_path = tmp_out.name if success else tmp_input.name
            elif ext in {".docx", ".xlsx"}:
                success, size = await asyncio.to_thread(
                    compress_office_to_target,
                    tmp_input.name,
                    tmp_out.name,
                    int(target_bytes),
                    lambda p, t: asyncio.run(progress_cb(p, t)),
                )
                final_path = tmp_out.name if success else tmp_input.name
            elif ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
                quality = percent
                success, size = await asyncio.to_thread(
                    compress_image, tmp_input.name, tmp_out.name, quality=quality
                )
                await progress_cb(100, "Done!")
                final_path = tmp_out.name if success else tmp_input.name
            else:
                await progress_cb(100, "Unsupported")
                yield json_stream(error="Unsupported file type")
                return

            # send download link (data URL)
            if success and os.path.getsize(final_path) < orig_bytes * 0.9:
                with open(final_path, "rb") as f:
                    data = f.read()
                import base64

                b64 = base64.b64encode(data).decode()
                await progress_cb(
                    download=f"data:application/octet-stream;base64,{b64}",
                    filename=os.path.basename(final_path),
                )
            else:
                await progress_cb(status="No further compression")
        finally:
            os.unlink(tmp_input.name)
            if os.path.exists(tmp_out.name):
                os.unlink(tmp_out.name)

    return StreamingResponse(stream(), media_type="text/event-stream")
