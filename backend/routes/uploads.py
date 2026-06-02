import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

from routes.auth import get_current_user
from models import User

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


import io
from PIL import Image

@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")

    try:
        # Load and compress image using Pillow
        image = Image.open(io.BytesIO(content))
        
        # Normalize image modes for WebP
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA")
        else:
            if image.mode != "RGB":
                image = image.convert("RGB")
                
        # Downscale if image is excessively large
        max_size = 1200
        if image.width > max_size or image.height > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
        # Compress to WebP
        out_buf = io.BytesIO()
        image.save(out_buf, format="WEBP", quality=80)
        compressed_content = out_buf.getvalue()
        
        ext = ".webp"
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = UPLOAD_DIR / filename
        
        with open(filepath, "wb") as f:
            f.write(compressed_content)
    except Exception:
        # Fallback to saving original file if PIL processing fails
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = UPLOAD_DIR / filename
        with open(filepath, "wb") as f:
            f.write(content)

    return {"filename": filename, "url": f"/uploads/{filename}"}


@router.get("/{filename}")
def get_upload(filename: str):
    filepath = UPLOAD_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(filepath))
