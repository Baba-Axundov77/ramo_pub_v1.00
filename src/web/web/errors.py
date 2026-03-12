# web/errors.py - Global Exception Handling with Luxury UI
from __future__ import annotations
import logging
import traceback
from flask import jsonify, render_template, request, current_app
from functools import wraps
from typing import Dict, Any, Optional
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class ErrorHandler:
    """Luxury error handling with beautiful UI and JSON responses"""
    
    @staticmethod
    def handle_404(error):
        """Handle 404 Not Found errors"""
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'NOT_FOUND',
                'message': 'The requested resource was not found',
                'timestamp': datetime.utcnow().isoformat(),
                'path': request.path
            }), 404
        
        return render_template('errors/404.html', 
                             title='Page Not Found - Ramo Pub',
                             path=request.path), 404
    
    @staticmethod
    def handle_500(error):
        """Handle 500 Internal Server errors"""
        error_id = f"ERR_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Log full error details
        logger.error(f"Internal Server Error [{error_id}]: {str(error)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'INTERNAL_SERVER_ERROR',
                'message': 'An internal server error occurred',
                'error_id': error_id,
                'timestamp': datetime.utcnow().isoformat(),
                'path': request.path
            }), 500
        
        return render_template('errors/500.html',
                             title='Server Error - Ramo Pub',
                             error_id=error_id,
                             error_message=str(error) if current_app.debug else None), 500
    
    @staticmethod
    def handle_403(error):
        """Handle 403 Forbidden errors"""
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'FORBIDDEN',
                'message': 'You do not have permission to access this resource',
                'timestamp': datetime.utcnow().isoformat(),
                'path': request.path
            }), 403
        
        return render_template('errors/403.html',
                             title='Access Denied - Ramo Pub',
                             path=request.path), 403
    
    @staticmethod
    def handle_400(error):
        """Handle 400 Bad Request errors"""
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'BAD_REQUEST',
                'message': 'The request is invalid',
                'details': str(error),
                'timestamp': datetime.utcnow().isoformat(),
                'path': request.path
            }), 400
        
        return render_template('errors/400.html',
                             title='Bad Request - Ramo Pub',
                             error_message=str(error)), 400

def handle_exceptions(f):
    """Decorator to handle exceptions in routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            logger.warning(f"ValueError in {f.__name__}: {str(e)}")
            if request.path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'error': 'VALIDATION_ERROR',
                    'message': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }), 400
            else:
                return render_template('errors/validation.html',
                                     title='Validation Error - Ramo Pub',
                                     error_message=str(e)), 400
        
        except PermissionError as e:
            logger.warning(f"PermissionError in {f.__name__}: {str(e)}")
            return ErrorHandler.handle_403(e)
        
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return ErrorHandler.handle_500(e)
    
    return decorated_function

def register_error_handlers(app):
    """Register all error handlers with Flask app"""
    app.register_error_handler(404, ErrorHandler.handle_404)
    app.register_error_handler(500, ErrorHandler.handle_500)
    app.register_error_handler(403, ErrorHandler.handle_403)
    app.register_error_handler(400, ErrorHandler.handle_400)
    
    logger.info("Global error handlers registered successfully")

# Luxury Error Templates Data
ERROR_TEMPLATES = {
    '404': {
        'title': 'Page Not Found',
        'message': 'The page you are looking for seems to be missing.',
        'icon': '🔍',
        'action': 'Return to Dashboard',
        'action_url': '/admin/dashboard'
    },
    '500': {
        'title': 'Server Error',
        'message': 'Something went wrong on our end. Our team has been notified.',
        'icon': '⚠️',
        'action': 'Try Again',
        'action_url': 'javascript:history.back()'
    },
    '403': {
        'title': 'Access Denied',
        'message': 'You don\'t have permission to access this resource.',
        'icon': '🔒',
        'action': 'Request Access',
        'action_url': '/admin/contact'
    },
    '400': {
        'title': 'Bad Request',
        'message': 'The request you made is invalid.',
        'icon': '❌',
        'action': 'Try Again',
        'action_url': 'javascript:history.back()'
    }
}
