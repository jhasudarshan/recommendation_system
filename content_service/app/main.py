from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.config.logger_config import logger
import threading
from app.api.content import router as content_api
from app.event.kafka_service import content_kafka_service
from app.api.feedback import router as feedback_api
from app.services.new_scheduler import scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Content Service Starting...")
    scheduler_thread = threading.Thread(target=scheduler.start_scheduler, daemon=True)
    scheduler_thread.start()
    yield
    logger.info("Content Service Shutting Down...")

app = FastAPI(title="Content Service", lifespan=lifespan)

app.include_router(content_api, prefix="/content", tags=["Content"])
app.include_router(feedback_api, prefix="/feedback", tags=["Content"])

