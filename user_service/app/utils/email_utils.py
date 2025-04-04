import smtplib
import random
import string
import socket
import hashlib
from datetime import datetime,timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from app.config.config import (
    SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD,
    OTP_EXPIRY_SECONDS, OTP_REQUEST_LIMIT, OTP_RESEND_COOLDOWN
)
from app.config.logger_config import logger
from app.db.redis_cache import redis_cache
from app.utils.security_utils import security_utils
from app.db.mongo import mongo_db
from fastapi import Response


class EmailUtils:
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(EmailUtils, cls).__new__(cls)
            cls._instance.user_collection = mongo_db.get_collection("users")
            cls._instance.session_collection = mongo_db.get_collection("sessions")
        return cls._instance

    def _send_email(self, to_email: str, subject: str, body: str, is_html: bool = False):
        try:
            msg = MIMEMultipart()
            msg["From"] = SENDER_EMAIL
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "html" if is_html else "plain"))

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email} - Subject: {subject}")

        except smtplib.SMTPException as e:
            logger.error(f"SMTP error while sending email to {to_email}: {str(e)}")
            raise HTTPException(status_code=500, detail="SMTP server error.")
        except socket.gaierror:
            logger.error(f"Network error: Could not connect to SMTP server {SMTP_SERVER}")
            raise HTTPException(status_code=500, detail="Email service unavailable.")
        except Exception as e:
            logger.error(f"Unexpected error sending email to {to_email}: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to send email.")

    def _can_request_otp(self, email: str) -> bool:
        try:
            otp_request_count_key = f"otp_requests:{email}"
            last_request_key = f"otp_last_request:{email}"

            request_count = redis_cache.get_value(otp_request_count_key or {})
            if request_count and int(request_count) >= OTP_REQUEST_LIMIT:
                logger.warning(f"OTP request limit exceeded for {email}")
                return False

            last_request = redis_cache.get_value(last_request_key or {})
            if last_request:
                logger.warning(f"OTP cooldown active for {email}")
                return False

            return True
        except Exception as e:
            logger.error(f"Error checking OTP request eligibility for {email}: {e}")
            return False

    def _hash_otp(self, otp: str) -> str:
        try:
            return hashlib.sha256(otp.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Error hashing OTP: {e}")
            raise

    def generate_email_otp(self, email: str) -> str:
        try:
            if not self._can_request_otp(email):
                raise HTTPException(status_code=429, detail="Too many OTP requests. Try again later.")

            otp = ''.join(random.choices(string.digits, k=6))
            hashed_otp = self._hash_otp(otp)

            redis_cache.set_cache(f"email_otp:{email}", {"otp": hashed_otp}, OTP_EXPIRY_SECONDS)

            otp_request_count_key = f"otp_requests:{email}"
            redis_cache.set_value(otp_request_count_key, int(redis_cache.get_value(otp_request_count_key) or 0) + 1, 86400)

            last_request_key = f"otp_last_request:{email}"
            redis_cache.set_value(last_request_key, "1", OTP_RESEND_COOLDOWN)

            logger.info(f"Generated OTP for {email}: {otp} (valid for {OTP_EXPIRY_SECONDS // 60} mins)")
            return otp
        except Exception as e:
            logger.error(f"Error generating OTP for {email}: {e}")
            raise HTTPException(status_code=500, detail="Error generating OTP")

    def send_otp_email(self, email: str):
        try:
            otp = self.generate_email_otp(email)
            subject = "Verify Your Account on AI-NewsSphere" 

            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <h2 style="text-align: center;">Verify Your Account</h2>
                    <p>Dear User,</p>
                    <p>Your One-Time Password (OTP) for verifying your account on <strong>AI-NewsSphere</strong> is:</p> 
                    <p style="font-size: 20px; font-weight: bold; text-align: center;">{otp}</p>
                    <p>This OTP is valid for <strong>{OTP_EXPIRY_SECONDS // 60} minutes</strong>. Please do not share it with anyone.</p>
                    <p>If you did not request this, please ignore this email.</p>
            
                </body>
            </html>
            """
            self._send_email(email, subject, body, True)
        except Exception as e:
            logger.error(f"Error sending OTP email to {email}: {e}")
            raise HTTPException(status_code=500, detail="Error sending OTP email")

    def verify_email_otp(self, email: str, otp: str, response: Response) -> JSONResponse:
        try:
            stored_data = (redis_cache.get_cache(f"email_otp:{email}") or {}).get("data")
            logger.info(f"email: {email} and data: {stored_data}")
            
            if stored_data:
                stored_otp_hashed = stored_data.get("otp")
                logger.info(f"{otp}")
                
                if stored_otp_hashed and stored_otp_hashed == self._hash_otp(otp):
                    redis_cache.delete_key(f"email_otp:{email}")
                    logger.info(f"OTP verified successfully for {email}")
                    
                    self.user_collection.update_one({"email": email}, {"$set": {"verified": True}})
                    # session_id = str(uuid.uuid4())
                    # session_data = {
                    #     "session_id": session_id,
                    #     "last_login": datetime.now(timezone.utc),
                    #     "active": True,
                    # }

                    # self.session_collection.update_one(
                    #     {"email": email},
                    #     {"$push": {"sessions": session_data}},
                    #     upsert=True
                    # )
                    access_token = security_utils.create_access_token(data={"sub": email})
                    refresh_token = security_utils.create_refresh_token(data={"sub": email})
                    
                    response = JSONResponse(content={"message": "OTP verified successfully"}, status_code=200)
                    security_utils._set_auth_cookies(response, access_token, refresh_token)
                    return response
            
            logger.warning(f"Invalid OTP attempt for {email}")
            return JSONResponse(content={"message": "Invalid or expired OTP"}, status_code=400)
        except Exception as e:
            logger.error(f"Error verifying OTP for {email}: {e}")
            return JSONResponse(content={"message": "Error verifying OTP"}, status_code=500)


email_utils = EmailUtils()