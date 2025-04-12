from datetime import datetime, timedelta,timezone
from typing import Dict, Any
import jwt
from passlib.context import CryptContext
from app.config.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES,REFRESH_TOKEN_EXPIRE_DAYS
from fastapi import Response
from app.config.logger_config import logger

class SecurityUtils:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, data: Dict[str, Any]) -> str:
        try:
            to_encode = data.copy()
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            to_encode.update({"exp": expire})
            return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        except Exception as e:
            logger.error(f"Error creating access token: {e}")
            return 
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        try:
            to_encode = data.copy()
            expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
            to_encode.update({"exp": expire})
            return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        except Exception as e:
            logger.error(f"Error creating refresh token: {e}")
            return 
    
    def decode_access_token(self, token: str) -> Dict[str, Any] | None:
        try:
            return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except Exception as e:
            logger.error(f"Error decoding access token: {e}")
            return None
        
    def decode_refresh_token(self, token: str) -> Dict[str, Any] | None:
        try:
            return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except Exception as e:
            logger.error(f"Error decoding access token: {e}")
            return None
    
    def _set_auth_cookies(self, response: Response, access_token: str, refresh_token: str):
        try:
            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                secure=False,              
                samesite="Strict",
                path="/",
                max_age=3600, 
            )
            
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=False,               
                samesite="Strict",         
                path="/",             
                max_age=604800,
            )
            
            logger.info("Cookies Set: ", response.headers)
        except Exception as e:
            logger.error(f"Error setting auth cookies: {e}")
            return 
    
    def _clear_auth_cookies(self, response: Response):
        try:
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
        except Exception as e:
            logger.error(f"Error clearing auth cookies: {e}")
            return 
        
security_utils = SecurityUtils()