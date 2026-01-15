# main.py (FastAPI app entrypoint)

import logging
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.api import plant_analysis_api, charts_api

# Load environment variables from .env file in root directory
try:
    from dotenv import load_dotenv
    # Load from root .env file
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        load_dotenv(env_file)
        logging.info(f"Loaded environment variables from {env_file}")
    else:
        # Fallback to default dotenv behavior
        load_dotenv()
        logging.info("Loaded environment variables from default .env location")
except ImportError:
    # If python-dotenv is not available, try to load manually
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        logging.info(f"Loaded environment variables manually from {env_file}")
except Exception as e:
    logging.warning(f"Could not load .env file: {e}")

# 🔧 New imports for DB setup
from backend.db.models import Base
from backend.db.database import engine

# Check if read-only mode is enabled
READ_ONLY_MODE = os.environ.get("READ_ONLY_MODE", "false").lower() == "true"

# Enable debug-level logging
logging.basicConfig(level=logging.DEBUG)

# Initialize app
app = FastAPI(title="Plant Analysis Backend")

# ✅ Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to ["http://localhost:8080"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔧 Create database tables
Base.metadata.create_all(bind=engine)

# Health and root endpoints for container healthcheck
@app.get("/health")
async def health():
    return {"status": "ok"}

# Register API routes
app.include_router(plant_analysis_api.router, prefix="/api")
app.include_router(charts_api.router, prefix="/api")

# Conditionally include upload API only if not in read-only mode
if not READ_ONLY_MODE:
    from backend.api import upload_api
    app.include_router(upload_api.router, prefix="/api")

# Serve static files from frontend/dist directory
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    # Mount static assets (css, js, img, favicon.ico) from dist root
    # Vue CLI with publicPath: './' creates files directly in dist/
    static_dirs = ["css", "js", "img"]
    for static_dir in static_dirs:
        static_path = FRONTEND_DIST / static_dir
        if static_path.exists():
            app.mount(f"/{static_dir}", StaticFiles(directory=str(static_path)), name=static_dir)
    
    # Serve favicon.ico if it exists
    favicon_path = FRONTEND_DIST / "favicon.ico"
    if favicon_path.exists():
        @app.get("/favicon.ico")
        async def serve_favicon():
            return FileResponse(str(favicon_path))
    
    # Serve index.html for root route
    @app.get("/")
    async def serve_index():
        index_path = FRONTEND_DIST / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {"error": "Frontend index.html not found"}
    
    # Serve index.html for all non-API routes (SPA fallback)
    # This must be last to catch all routes not matched above
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str, request: Request):
        # Don't interfere with API routes or static file routes
        path = request.url.path
        if path.startswith("/api") or path.startswith("/css") or path.startswith("/js") or path.startswith("/img") or path == "/favicon.ico":
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=404, content={"error": "Not found"})
        
        # Serve index.html for SPA routing
        index_path = FRONTEND_DIST / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {"error": "Frontend not built. Run: cd frontend && npm run build"}
else:
    # If frontend/dist doesn't exist, provide helpful message
    @app.get("/")
    async def root():
        return {
            "status": "ok",
            "message": "Frontend not built. Run: cd frontend && VUE_APP_API_BASE_URL=/api npm run build"
        }
