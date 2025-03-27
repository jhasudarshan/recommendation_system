from fastapi import APIRouter
from app.services.content_serve import content_service
from typing import Dict

router = APIRouter()

@router.post("/process")
def process_content(content_data: Dict):
    response = content_service.process_content(content_data)
    return response