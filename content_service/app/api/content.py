from fastapi import APIRouter
from content_service.app.services.content_serve import content_service
from typing import Dict,List,Union

router = APIRouter()

@router.post("/process")
def process_content(content_data: Dict):
    response = content_service.process_content(content_data)
    return response
    
    response = content_service.process_batch_content(content_data)
    return response
