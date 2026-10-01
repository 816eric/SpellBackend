import os
import sys
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import users, words, study, rewards, tags, login, ai, settings, history, tts, levels, streaks, unlockables, challenges, lessons, minigames, bosses, achievements, moe_words
from src.db_session import init_db, migrate_plaintext_passwords, encrypt_pii
from src.routes import admin_routes
from src.routes.admin_routes import authenticate
from src.routes import leaderboard
import backup_to_drive
from src.security import AuthMiddleware, SecurityHeadersMiddleware
from config.settings import SERVER_HOST, SERVER_PORT, SERVER_RELOAD

# On Windows, stdout/stderr default to the system codepage (e.g. cp1252)
# whenever they aren't attached to a real console (piped to a file,
# launched by a service manager, etc). Debug print()s of Chinese lesson
# tags/words then raise UnicodeEncodeError and 500 the request. Force
# UTF-8 so logging never crashes a request regardless of how the process
# is launched.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# Interactive docs expose the full API surface; only enable them explicitly.
_docs = os.getenv("ENABLE_DOCS", "").lower() == "true"
app = FastAPI(
    title="Spell Practice API",
    docs_url="/docs" if _docs else None,
    redoc_url="/redoc" if _docs else None,
    openapi_url="/openapi.json" if _docs else None,
)

# Only the known frontends (plus local dev) may call the API from a browser.
# Auth uses bearer tokens, not cookies, so credentials mode stays off.
# Extra origins: CORS_ORIGINS="https://a.example,https://b.example"
_extra_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
_ORIGIN_REGEX = (
    r"^(https://([a-z0-9-]+\.)?(aispell|aispellgame)\.pages\.dev"
    r"|http://(localhost|127\.0\.0\.1)(:\d+)?)$"
)

# Middleware order: last added runs first (outermost). CORS must be outermost
# so 401/403/429 responses from AuthMiddleware still carry CORS headers.
app.add_middleware(AuthMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_extra_origins,
    allow_origin_regex=_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-User-Name"],
    max_age=600,
)

# Initialize DB
init_db()
migrate_plaintext_passwords()
encrypt_pii()

# Include Routers
app.include_router(users.router)
app.include_router(words.router)
app.include_router(study.router)
app.include_router(rewards.router)
app.include_router(tags.router)
app.include_router(admin_routes.router)
app.include_router(login.router)
app.include_router(ai.router)
app.include_router(leaderboard.router)
app.include_router(settings.router)
app.include_router(history.router)
app.include_router(tts.router)
app.include_router(levels.router)
app.include_router(streaks.router)
app.include_router(unlockables.router)
app.include_router(challenges.router)
app.include_router(lessons.router)
app.include_router(minigames.router)
app.include_router(bosses.router)
app.include_router(achievements.router)
app.include_router(moe_words.router)

# Backup is admin-only (HTTP Basic, same credentials as the /admin console).
@app.post("/admin/backup")
async def trigger_backup(creds=Depends(authenticate)):
    """Manually trigger a database backup to Google Drive."""
    success = backup_to_drive.backup_database()
    if success:
        return {"status": "success", "message": "Backup completed"}
    else:
        return {"status": "error", "message": "Backup failed"}


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=SERVER_HOST, port=SERVER_PORT, reload=SERVER_RELOAD)