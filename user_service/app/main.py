from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
import uvicorn
from api.users import router as user_api
from api.recommend import router as recommend_api
from events.kafka_handler import user_service_kafka
import threading

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("User Service Starting...")
    listener_thread = threading.Thread(target=user_service_kafka.start_listeners, daemon=True)
    listener_thread.start()
    yield
    logging.info("User Service Shutting Down...")

app = FastAPI(title="User Service", lifespan=lifespan)

app.include_router(user_api, prefix="/users", tags=["Users"])
app.include_router(recommend_api, tags=["Recommend"])

if __name__ == "__main__":
    logging.info("Starting User Service...")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")