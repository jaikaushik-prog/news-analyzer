from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import contextlib

# Import routers
from routers.signals import router as signals_router
from routers.sectors import router as sectors_router
from routers.search import router as search_router
from scheduler import start_scheduler, shutdown_scheduler

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load ML models, start scheduler
    print("Starting up ML models and scheduler...")
    start_scheduler()
    yield
    # Shutdown
    print("Shutting down...")
    shutdown_scheduler()

app = FastAPI(title="News Alpha API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(signals_router)
app.include_router(sectors_router)
app.include_router(search_router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
