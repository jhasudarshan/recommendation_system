from fastapi import APIRouter, HTTPException
from services.user import user_service
from models.mongo_model import User

router = APIRouter()


@router.post("/log-interest")
def log_interest(request: User):
    user_service.log_interest(request.email, request.interests)
    return {"message": "User interest logged successfully"}

@router.get("/compute-embedding")
def compute_embedding(email: str):
    try:
        embedding = user_service.compute_user_embedding(email)
        return {"email": email, "embedding": embedding}
    except HTTPException as e:
        raise e