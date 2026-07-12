from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import users, words, study, rewards, tags, login, ai, settings, history, tts, levels, streaks, unlockables, challenges
from src.db_session import init_db
from src.routes import admin_routes
from src.routes import leaderboard
import backup_to_drive
from config.settings import SERVER_HOST, SERVER_PORT, SERVER_RELOAD

app = FastAPI(title="Spell Practice API")

# CORS middleware MUST be added before routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Initialize DB
init_db()

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

# SECURITY WARNING: Backup endpoint must be protected in production
# For production, implement proper authentication/authorization (e.g., API key, JWT)
@app.post("/admin/backup")
async def trigger_backup():
    """Manually trigger a database backup to Google Drive."""
    success = backup_to_drive.backup_database()
    if success:
        return {"status": "success", "message": "Backup completed"}
    else:
        return {"status": "error", "message": "Backup failed"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=SERVER_HOST, port=SERVER_PORT, reload=SERVER_RELOAD)