import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.db.session import engine, Base
from app.routers import auth, chat, admin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events manager for database creation and teardown."""
    logger.info("Initializing database and tables on startup.")
    try:
        async with engine.begin() as conn:
            # Create all tables if they don't exist
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Critical error initializing database tables: {str(e)}")
        raise e
        
    yield
    
    logger.info("Application shutdown initiated.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
)

# Enable CORS for local cross-origin testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)

# Mount Static Files for Frontend
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
async def serve_index():
    """Serve the single-page HTML frontend at the root path."""
    return FileResponse("app/static/index.html")
