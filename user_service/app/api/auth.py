from fastapi import APIRouter, Request, Response
from app.services.auth_service import auth_service
from app.utils.email_utils import email_utils
from app.models.mongo_model import NewUser
router = APIRouter()

@router.post("/signup")
def signup(newUser : NewUser):
    return auth_service.signup(newUser.username, newUser.email, newUser.password)

@router.post("/login")
def login(email: str, password: str, response: Response):
    return auth_service.login(email, password, response)

@router.post("/logout")
def logout(request: Request, response: Response):
    return auth_service.logout(request, response)

@router.get("/me")
def protected_route(request: Request,response: Response):
    print("response: " ,response)
    user = auth_service.get_current_user(request,response)
    return {"message": "You are authorized", "user": user}

@router.post("/verify-otp")
def verify_otp(email: str, otp: str, response: Response):
    return email_utils.verify_email_otp(email, otp, response)