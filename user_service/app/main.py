from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.config.logger_config import logger
from app.api.users import router as user_api
from app.api.recommend import router as recommend_api
from app.events.kafka_handler import user_service_kafka
from app.api.auth import router as auth_api
import threading

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("User Service Starting...")
    listener_thread = threading.Thread(target=user_service_kafka.start_listeners, daemon=True)
    listener_thread.start()
    yield
    logger.info("User Service Shutting Down...")

app = FastAPI(title="User Service", lifespan=lifespan)

app.include_router(user_api, prefix="/users", tags=["Users"])
app.include_router(auth_api,prefix='/auth',tags=["Auth"])
app.include_router(recommend_api, tags=["Recommend"])