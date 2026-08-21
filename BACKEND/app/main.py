from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.firebase import initialize_firebase
from app.database.database import Base, engine
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.rate_limit import limiter

# Import models so Base.metadata knows about them before create_all()
import app.models  # noqa: F401
from app.core.logger import logger
import time
from fastapi import Request

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("NYAAY AI Backend starting up", extra={"extra_info": {"environment": settings.ENVIRONMENT}})
    initialize_firebase()
    # Create all tables that do not yet exist (idempotent)
    Base.metadata.create_all(bind=engine)
    logger.info("Database schemas verified")
    
    # Pre-warm the embedding model so TTFT isn't 40s on first request
    from app.knowledge.embeddings import embedding_service
    embedding_service.warmup()
    logger.info("Embedding model warmed up and ready")
    
    yield
    # --- Shutdown --- (nothing to clean up yet)
    logger.info("NYAAY AI Backend shutting down")

app = FastAPI(
    title="NYAAY AI API",
    description="Backend API for NYAAY AI — Legal Assistant for the Indian Judiciary Ecosystem",
    version="1.0.0",
    lifespan=lifespan,
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        global_metrics.record_request()
        global_metrics.save()
        logger.info(
            "API Request completed",
            extra={"extra_info": {
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "process_time_ms": round(process_time * 1000, 2)
            }}
        )
        return response
    except Exception as exc:
        process_time = time.time() - start_time
        logger.error(
            "API Request failed",
            exc_info=True,
            extra={"extra_info": {
                "method": request.method,
                "url": str(request.url),
                "process_time_ms": round(process_time * 1000, 2)
            }}
        )
        raise exc

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Settings-driven CORS — no wildcard with allow_credentials=True
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.core.metrics import global_metrics
from app.routes import auth, kanoon, upload_chat, chat, drafting, reasoning, admin

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(kanoon.router, prefix="/api/kanoon", tags=["Know Your Kanoon"])
app.include_router(upload_chat.router, prefix="/api/upload-chat", tags=["Upload & Chat"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat History"])
app.include_router(drafting.router, prefix="/api/drafting", tags=["Drafting"])
app.include_router(reasoning.router, prefix="/api/reasoning", tags=["Reasoning"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


@app.get("/api/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Verifies that the API is running and configuration has loaded.
    """
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "database": "configured",
    }

@app.get("/api/ready", tags=["Health"])
async def readiness_check():
    """
    Readiness check endpoint.
    Used by load balancers and orchestrators to determine if traffic should be routed here.
    """
    return {
        "status": "ready"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.is_development,
    )
