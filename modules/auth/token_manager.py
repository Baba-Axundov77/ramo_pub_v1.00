# modules/auth/token_manager.py — JWT Token Management for Enterprise System
from __future__ import annotations
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
import logging

logger = logging.getLogger(__name__)

class TokenManager:
    """Enterprise-grade JWT token management with security best practices"""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY")
        if not self.secret_key:
            raise ValueError("JWT_SECRET_KEY must be set in environment variables")
        
        self.algorithm = "HS256"
        self.token_expiry = timedelta(hours=24)  # 24 hours
        self.refresh_expiry = timedelta(days=7)   # 7 days for refresh tokens
        
    def generate_token(self, user_data: Dict[str, Any], expires_delta: timedelta = None) -> str:
        """Generate JWT access token"""
        if expires_delta is None:
            expires_delta = self.token_expiry
            
        payload = {
            "user_id": user_data.get("id"),
            "username": user_data.get("username"),
            "role": user_data.get("role"),
            "full_name": user_data.get("full_name"),
            "exp": datetime.utcnow() + expires_delta,
            "iat": datetime.utcnow(),
            "iss": "ramo_pub_enterprise",
            "aud": "ramo_pub_api"
        }
        
        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.info(f"Token generated for user: {user_data.get('username')}")
            return token
        except Exception as e:
            logger.error(f"Token generation failed: {str(e)}")
            raise
    
    def generate_refresh_token(self, user_data: Dict[str, Any]) -> str:
        """Generate refresh token for extended sessions"""
        return self.generate_token(user_data, self.refresh_expiry)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            # Remove Bearer prefix if present
            if token.startswith("Bearer "):
                token = token[7:]
            
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                audience="ramo_pub_api",
                issuer="ramo_pub_enterprise"
            )
            
            # Check if token is expired
            if datetime.utcnow() > datetime.fromtimestamp(payload["exp"]):
                logger.warning("Token expired")
                return None
                
            logger.info(f"Token verified for user: {payload.get('username')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            return None
    
    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired without full verification"""
        try:
            if token.startswith("Bearer "):
                token = token[7:]
                
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_exp": False}  # Skip expiration check temporarily
            )
            
            exp = payload.get("exp")
            if exp:
                return datetime.utcnow() > datetime.fromtimestamp(exp)
            return True
            
        except Exception:
            return True
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Generate new access token from refresh token"""
        payload = self.verify_token(refresh_token)
        if not payload:
            return None
            
        # Create new access token with shorter expiry
        user_data = {
            "id": payload.get("user_id"),
            "username": payload.get("username"),
            "role": payload.get("role"),
            "full_name": payload.get("full_name")
        }
        
        return self.generate_token(user_data)
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against bcrypt hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False

# Global token manager instance
token_manager = TokenManager()
