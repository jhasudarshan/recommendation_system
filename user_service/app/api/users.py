from fastapi import APIRouter, HTTPException
from app.services.user import user_service
from app.models.mongo_model import UserLogInterest

router = APIRouter()


@router.post("/log-interest")
def log_interest(request: UserLogInterest):
    user_service.log_interest(request.email, request.interests)
    return {"message": "User interest logged successfully"}