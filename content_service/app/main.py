from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
import uvicorn
from api.content import router as content_api
from event.kafka_service import content_kafka_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Content Service Starting...")
    yield
    logging.info("Content Service Shutting Down...")

app = FastAPI(title="Content Service", lifespan=lifespan)

app.include_router(content_api, prefix="/content", tags=["Content"])

if __name__ == "__main__":
    logging.info("Starting Content Service...")
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")