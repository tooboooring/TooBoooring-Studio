from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="TooBoooring Studio API",
    description="Backend API for video processing and transcription",
    version="1.0.0"
)

# Allow CORS for the frontend (React/Vite default is port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Welcome to TooBoooring Studio API"}

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "TooBoooring Studio Backend"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
