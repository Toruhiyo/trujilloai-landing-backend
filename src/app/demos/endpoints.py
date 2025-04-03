import logging
from fastapi import APIRouter

from src.app.demos.ai_bi.endpoints import router as aibi_router

# Create a demos router with a prefix
router = APIRouter(prefix="/demos", tags=["Demos"])

logger = logging.getLogger(__name__)
logger.info("Initializing demos router")

# Include the AI BI router
# The final endpoint will be /demos/aibi/... as the aibi_router already has the /aibi prefix
router.include_router(aibi_router)
