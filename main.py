"""FHIR Validation Server - Main application entry point."""

import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.ui.api_endpoints import router
from src.ui.ig_endpoints import ig_router
from src.ui.web_endpoints import web_router
from src.constants.fhir_constants import (
    SERVER_NAME, SERVER_VERSION, SERVER_DESCRIPTION, DEFAULT_HOST, DEFAULT_PORT
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(f"Starting {SERVER_NAME} v{SERVER_VERSION}")
    logger.info("FHIR Validation Server is ready!")
    yield
    # Shutdown
    logger.info("Shutting down FHIR Validation Server")

# Create FastAPI application
app = FastAPI(
    title=SERVER_NAME,
    version=SERVER_VERSION,
    description=SERVER_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "FHIR Validation Server",
        "email": "support@fhirvalidation.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": f"http://localhost:{DEFAULT_PORT}",
            "description": "Development server"
        }
    ]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")

# Include PH-Core IG hosting routes (no prefix - served at root for FHIR canonical URLs)
app.include_router(ig_router)

# Include web frontend routes
app.include_router(web_router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/docs-api", include_in_schema=False)
async def api_docs():
    """Redirect to API documentation."""
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    # Development server configuration
    uvicorn.run(
        "main:app",
        host=DEFAULT_HOST,
        port=DEFAULT_PORT,
        reload=True,
        log_level="info"
    )
