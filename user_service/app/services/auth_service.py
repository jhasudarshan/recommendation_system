import uuid
from fastapi import HTTPException, status, Response, Request
from fastapi.responses import JSONResponse
from datetime import datetime,timezone
from app.db.mongo import mongo_db
from app.utils.security_utils import security_utils
from app.utils.email_utils import email_utils

class AuthService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AuthService, cls).__new__(cls)
            cls._instance.user_collection = mongo_db.get_collection("users")
            cls._instance.session_collection = mongo_db.get_collection("sessions")
        return cls._instance

    def signup(self, username: str, email: str, password: str) -> JSONResponse:
        if self.user_collection.find_one({"email": email}):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

        hashed_password = security_utils.hash_password(password)
        self.user_collection.insert_one({
            "username": username,
            "email": email,
            "hashed_password": hashed_password,
            "verified": False
        })

        email_utils.send_otp_email(email)

        return JSONResponse(content={"message": "User registered successfully. Please verify your email."},
                            status_code=status.HTTP_201_CREATED)

    def login(self, email: str, password: str, response: Response) -> JSONResponse:
        user = self.user_collection.find_one({"email": email})
        if not user or not security_utils.verify_password(password, user["hashed_password"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        if not user.get("verified", False):
            try:
                email_utils.send_otp_email(email)
                return JSONResponse(
                    content={"message": "User not verified. OTP sent to email for verification."},
                    status_code=status.HTTP_401_UNAUTHORIZED
                )
            except Exception:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send verification OTP")
        
        access_token = security_utils.create_access_token(data={"sub": user["email"]})
        refresh_token = security_utils.create_refresh_token(data={"sub": user["email"]})

        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "last_login": datetime.now(timezone.utc),
            "active": True,
        }

        self.session_collection.update_one(
            {"email": email},
            {"$push": {"sessions": session_data}},
            upsert=True
        )

        response = JSONResponse(content={"message": "Login successful"})
        security_utils._set_auth_cookies(response,access_token,refresh_token)
        return response


    def refresh_access_token(self, request: Request, response: Response):
        old_refresh_token = request.cookies.get("refresh_token")
        if not old_refresh_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")

        payload = security_utils.decode_refresh_token(old_refresh_token)
        if not payload:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        email = payload.get("sub")
        session = self.session_collection.find_one({"email": email}, {"refresh_token": 1, "rotated": 1})

        if not session or session["refresh_token"] != old_refresh_token or session["rotated"]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

        new_access_token = security_utils.create_access_token(data={"sub": email})
        new_refresh_token = security_utils.create_refresh_token(data={"sub": email})

        self.session_collection.update_one(
            {"email": email, "sessions.session_id": session.get("session_id")},
            {"$set": {"sessions.$.last_login": datetime.now(timezone.utc), "sessions.$.active": True}}
        )

        security_utils._set_auth_cookies(response, new_access_token, new_refresh_token)
        return response
    
    def get_current_user(self, request: Request, response: Response) -> JSONResponse:
        access_token = request.cookies.get("access_token")
        payload = security_utils.decode_access_token(access_token)

        if not payload:
            try:
                response = self.refresh_access_token(request, response)
                access_token = response.headers.get("set-cookie")
                if access_token:
                    access_token = access_token.split(";")[0].split("=")[1]
                    payload = security_utils.decode_access_token(access_token)
            except HTTPException:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not refresh access token")

        if not payload:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token")

        email = payload.get("sub")
        user = self.user_collection.find_one({"email": email}, {"_id": 0, "hashed_password": 0})

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        response = JSONResponse(content={"message": "User authenticated", "user": user})
        return response

    def logout(self, request: Request, response: Response) -> JSONResponse:
        refresh_token = request.cookies.get("refresh_token")

        if refresh_token:
            payload = security_utils.decode_refresh_token(refresh_token)
            if payload:
                email = payload.get("sub")
                session_id = self.session_collection.find_one({"email": email}, {"sessions.session_id": 1}).get("session_id")

                self.session_collection.update_one(
                    {"email": email, "sessions.session_id": session_id},
                    {"$set": {
                        "sessions.$.active": False,
                        "sessions.$.last_logout": datetime.now(timezone.utc),
                        "sessions.$.rotated": True
                    }}
                )

        response = JSONResponse(content={"message": "Logout successful"}, status_code=status.HTTP_200_OK)
        security_utils._clear_auth_cookies(response)
        return response

auth_service = AuthService()