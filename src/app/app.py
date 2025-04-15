import logging
import traceback

from fastapi import APIRouter, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .chat import endpoints as chat
from .demos import endpoints as demos
from .entities.users import endpoints as users
from .landing_voicechat import endpoints as landing_voicechat

from .error_handling import set_app_exception_handlers
from src.utils.requests_toolbox import get_request_relevant_data

logger = logging.getLogger(__name__)

router = APIRouter()
router.include_router(chat.router, tags=["Chat"])
router.include_router(users.router, tags=["Users"])
router.include_router(landing_voicechat.router, tags=["LandingVoiceChat"])

# Include the demos router directly in the app, not in the main router
# This way the prefix can be properly handled
app = FastAPI(
    openapi_url="/documentation/openapi.json",
    docs_url="/documentation/swagger",
    redoc_url="/documentation/redoc",
)


# Add the catch-all exception middleware first
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        # Log the error with traceback
        logger.error(
            f"Unhandled exception in middleware: {str(e)}. "
            f"Traceback: {traceback.format_exc()}"
        )
        # Return a 500 response
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "An unexpected error occurred",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            },
        )


# Then add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "https://localhost:8080",
        "http://localhost:3000",  # Common React development port
        "https://localhost:3000",
        "https://dev.trujillo.ai",
        "https://www.trujillo.ai",
        "https://trujillo.ai",
        "https://trujilloai-landing.vercel.app",
        # Add any other frontend origins you need
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Expose headers to the frontend
    max_age=600,  # Cache preflight requests for 10 minutes
)

app.include_router(router)
# Include the demos router directly in the app since it already has its own prefix
app.include_router(demos.router)

set_app_exception_handlers(app)


@app.get("/")
def root(request: Request):
    return JSONResponse(
        status_code=200,
        content={
            "message": "Success",
            "status_code": 200,
            "data": get_request_relevant_data(request),
        },
    )


@app.get("/health")
def health(request: Request):
    return JSONResponse(
        status_code=200,
        content={
            "message": "Success. I'm in good health, thanks for asking.",
            "status_code": 200,
            "data": get_request_relevant_data(request),
        },
    )


@app.get("/admin/warmup")
def warmup():
    return JSONResponse(
        status_code=200,
        content={"message": "Success. I'm warmed up and ready to go."},
    )
