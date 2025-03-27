from fastapi import APIRouter, HTTPException
from app.services.feedback_service import feedback_log_service
from typing import Dict

router = APIRouter()

@router.post("/process_metadata_update")
def process_metadata_update(content_data: Dict):
    try:
        feedback_log_service.process_metadata_update(content_data)
        return {"message": "Metadata update processed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))