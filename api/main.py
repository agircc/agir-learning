from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uvicorn

from agir_db.db.session import get_db
from api.routes import scenarios, episodes, steps, users, memories, chat, auth

app = FastAPI(title="AGIR API", description="API for AGIR Scenario Visualization")

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(scenarios.router, prefix="/api/scenarios", tags=["scenarios"])
app.include_router(episodes.router, prefix="/api/episodes", tags=["episodes"])
app.include_router(steps.router, prefix="/api/steps", tags=["steps"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(memories.router, prefix="/api/memories", tags=["memories"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

@app.get("/")
async def root():
    return {"message": "Welcome to AGIR API"}

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    # Check database connection
    try:
        # Execute a simple query
        db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 