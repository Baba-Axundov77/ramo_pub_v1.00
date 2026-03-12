# modules/auth/jwt_decorators.py — JWT Authentication Decorators for API
from __future__ import annotations
from functools import wraps
from flask import request, jsonify, g
from src.core.modules.auth.token_manager import token_manager
import logging

logger = logging.getLogger(__name__)

def jwt_required(f):
    """JWT authentication decorator for API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            logger.warning("Missing Authorization header")
            return jsonify({
                'success': False,
                'message': 'Authorization header required',
                'error_code': 'MISSING_AUTH_HEADER'
            }), 401
        
        # Check Bearer format
        if not auth_header.startswith('Bearer '):
            logger.warning("Invalid Authorization header format")
            return jsonify({
                'success': False,
                'message': 'Authorization header must be in format: Bearer <token>',
                'error_code': 'INVALID_AUTH_FORMAT'
            }), 401
        
        # Extract and verify token
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        payload = token_manager.verify_token(token)
        
        if not payload:
            logger.warning("Invalid or expired token")
            return jsonify({
                'success': False,
                'message': 'Invalid or expired token',
                'error_code': 'INVALID_TOKEN'
            }), 401
        
        # Store user data in Flask's g object
        g.user = payload
        g.user_id = payload.get('user_id')
        g.username = payload.get('username')
        g.user_role = payload.get('role')
        
        return f(*args, **kwargs)
    
    return decorated_function


def role_required(*allowed_roles):
    """Role-based access control decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # First check JWT authentication
            if not hasattr(g, 'user_role'):
                return jsonify({
                    'success': False,
                    'message': 'Authentication required',
                    'error_code': 'AUTH_REQUIRED'
                }), 401
            
            # Check user role
            user_role = g.user_role
            if user_role not in allowed_roles:
                logger.warning(f"Access denied for role {user_role}. Required: {allowed_roles}")
                return jsonify({
                    'success': False,
                    'message': 'Insufficient permissions',
                    'error_code': 'INSUFFICIENT_PERMISSIONS',
                    'required_roles': list(allowed_roles),
                    'user_role': user_role
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def admin_required(f):
    """Admin-only access decorator"""
    return role_required('admin')(f)


def manager_required(f):
    """Manager or admin access decorator"""
    return role_required('admin', 'manager')(f)


def staff_required(f):
    """All staff roles access decorator"""
    return role_required('admin', 'manager', 'waiter', 'cashier', 'kitchen')(f)


def optional_jwt(f):
    """Optional JWT authentication - doesn't fail if token is missing"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]
            payload = token_manager.verify_token(token)
            
            if payload:
                g.user = payload
                g.user_id = payload.get('user_id')
                g.username = payload.get('username')
                g.user_role = payload.get('role')
        
        return f(*args, **kwargs)
    
    return decorated_function


def api_key_required(f):
    """API key authentication for external integrations"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for API key in header
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({
                'success': False,
                'message': 'API key required',
                'error_code': 'MISSING_API_KEY'
            }), 401
        
        # Here you would validate the API key against your database
        # For now, we'll use a simple environment variable check
        from os import getenv
        valid_api_key = getenv('API_KEY')
        
        if not valid_api_key or api_key != valid_api_key:
            logger.warning("Invalid API key provided")
            return jsonify({
                'success': False,
                'message': 'Invalid API key',
                'error_code': 'INVALID_API_KEY'
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated_function
