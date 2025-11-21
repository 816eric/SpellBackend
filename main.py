from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import users, words, study, rewards, tags, login, ai, settings, history
from src.db_session import init_db
from src.routes import admin_routes
from src.routes import leaderboard

app = FastAPI(title="Spell Practice API")

# Enable CORS for all origins, methods, and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)