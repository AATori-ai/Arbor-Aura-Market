import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from database import seed

seed()

app = FastAPI(title="ArborAura Market API", version="1.0.0", docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None)

ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:8000,http://localhost:8080,http://localhost:8090,http://127.0.0.1:3000,http://127.0.0.1:5500,http://127.0.0.1:8080,http://127.0.0.1:8090,http://localhost:5500,https://arboraura.com",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── Simple in-memory rate limiter ──
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "100"))  # requests per window
_rate_store: dict = defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Skip rate limiting for static files and health check
    path = request.url.path
    if path in ("/api/health",) or not path.startswith("/api/"):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW

    # Clean old entries and count recent
    _rate_store[client_ip] = [t for t in _rate_store[client_ip] if t > window_start]

    if len(_rate_store[client_ip]) >= RATE_LIMIT_MAX:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please slow down."},
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
        )

    _rate_store[client_ip].append(now)
    return await call_next(request)

from routes.auth import router as auth_router
from routes.listings import router as listings_router
from routes.favorites import router as favorites_router
from routes.admin import router as admin_router
from routes.stripe_api import router as stripe_router
from routes.contacts import router as contacts_router
from routes.reports import router as reports_router
from routes.views import router as views_router
from routes.users import router as users_router
from routes.uploads import router as uploads_router
from routes.chat import router as chat_router
from routes.notifications import router as notifications_router
from routes.gdpr import router as gdpr_router
from routes.reviews import router as reviews_router
from routes.ai import router as ai_router

# Serve uploaded files
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

app.include_router(auth_router)
app.include_router(listings_router)
app.include_router(favorites_router)
app.include_router(admin_router)
app.include_router(stripe_router)
app.include_router(contacts_router)
app.include_router(reports_router)
app.include_router(views_router)
app.include_router(users_router)
app.include_router(uploads_router)
app.include_router(chat_router)
app.include_router(notifications_router)
app.include_router(gdpr_router)
app.include_router(reviews_router)
app.include_router(ai_router, prefix="/api/ai", tags=["AI"])


@app.get("/api/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
