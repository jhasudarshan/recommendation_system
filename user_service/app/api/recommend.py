from fastapi import APIRouter, HTTPException
from services.recommend_service import recommend_service

router = APIRouter()

@router.get("/recommend")
async def get_recommendations(email: str, top_k: int = 30):
    recommendations = recommend_service.get_recommendations(email, top_k)
    if not recommendations["recommendations"]:
        raise HTTPException(status_code=404, detail="No recommendations found.")
    return recommendations