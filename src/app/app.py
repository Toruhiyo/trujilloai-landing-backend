import logging

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer

from .chat import endpoints as chat
from .entities.users import endpoints as users

from .error_handling import set_app_exception_handlers
from src.utils.requests_toolbox import get_request_relevant_data

logger = logging.getLogger(__name__)

router = APIRouter()
router.include_router(chat.router, tags=["Chat"])
router.include_router(users.router, tags=["Users"])

app = FastAPI(
    openapi_url="/documentation/openapi.json",
    docs_url="/documentation/swagger",
    redoc_url="/documentation/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "https://localhost:8080",
        "https://dev.trujillo.ai",
        "https://www.trujillo.ai",
        "https://trujillo.ai",
        "https://trujilloai-landing.vercel.app/*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

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
