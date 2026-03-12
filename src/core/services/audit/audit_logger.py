# modules/audit/audit_logger.py - Enterprise Audit Logging
from __future__ import annotations
import structlog
from datetime import datetime
from typing import Optional, Dict, Any
from functools import wraps
import json
import os

# Configure structlog for luxury audit logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

audit_logger = structlog.get_logger("audit")

class AuditLogger:
    """Enterprise-grade audit logging for Ramo Pub ERP"""
    
    @staticmethod
    def log_action(
        user_id: Optional[int],
        action_type: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """Log an audit action with full context"""
        
        audit_data = {
            "user_id": user_id,
            "action_type": action_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": ip_address,
            "success": success,
            "error_message": error_message,
            "timestamp": datetime.utcnow().isoformat(),
            "environment": os.getenv("FLASK_ENV", "development")
        }
        
        if success:
            audit_logger.info("AUDIT_ACTION", **audit_data)
        else:
            audit_logger.error("AUDIT_ACTION_FAILED", **audit_data)
    
    @staticmethod
    def log_critical_operation(
        user_id: int,
        operation: str,
        module: str,
        details: Dict[str, Any],
        **kwargs
    ):
        """Log critical operations with enhanced security"""
        
        audit_data = {
            "user_id": user_id,
            "operation": operation,
            "module": module,
            "details": details,
            "critical": True,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        audit_logger.warning("CRITICAL_OPERATION", **audit_data)

def audit_action(
    action_type: str,
    resource_type: str,
    log_details: bool = True
):
    """Decorator for automatic audit logging"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request, g
            
            user_id = getattr(g, 'user_id', None)
            ip_address = request.remote_addr if request else None
            
            # Extract resource information
            resource_id = None
            details = {}
            
            if log_details:
                # Log function arguments (excluding sensitive data)
                for i, arg in enumerate(args):
                    if isinstance(arg, (int, str, float, bool)):
                        details[f"arg_{i}"] = arg
                
                # Log keyword arguments (excluding sensitive data)
                for key, value in kwargs.items():
                    if not any(sensitive in key.lower() for sensitive in ['password', 'secret', 'token']):
                        details[key] = value
            
            try:
                result = f(*args, **kwargs)
                
                # Log successful action
                AuditLogger.log_action(
                    user_id=user_id,
                    action_type=action_type,
                    resource_type=resource_type,
                    resource_id=str(resource_id) if resource_id else None,
                    details=details,
                    ip_address=ip_address,
                    success=True
                )
                
                return result
                
            except Exception as e:
                # Log failed action
                AuditLogger.log_action(
                    user_id=user_id,
                    action_type=action_type,
                    resource_type=resource_type,
                    resource_id=str(resource_id) if resource_id else None,
                    details=details,
                    ip_address=ip_address,
                    success=False,
                    error_message=str(e)
                )
                raise
        
        return decorated_function
    return decorator

# Specific audit decorators for common operations
@audit_action("CREATE", "order")
def create_order_audit(f):
    """Audit order creation"""
    return f

@audit_action("UPDATE", "order")
def update_order_audit(f):
    """Audit order updates"""
    return f

@audit_action("DELETE", "order")
def delete_order_audit(f):
    """Audit order deletion"""
    return f

@audit_action("PROCESS", "payment")
def process_payment_audit(f):
    """Audit payment processing"""
    return f

@audit_action("UPDATE", "inventory")
def update_inventory_audit(f):
    """Audit inventory updates"""
    return f

@audit_action("CREATE", "user")
def create_user_audit(f):
    """Audit user creation"""
    return f

@audit_action("LOGIN", "auth")
def login_audit(f):
    """Audit user login"""
    return f

@audit_action("LOGOUT", "auth")
def logout_audit(f):
    """Audit user logout"""
    return f

# Luxury Audit Log Examples
AUDIT_EXAMPLES = {
    "order_created": {
        "user_id": 123,
        "action_type": "CREATE",
        "resource_type": "order",
        "resource_id": "ORD-2024-001",
        "details": {
            "table_id": 5,
            "total_amount": 125.50,
            "items_count": 3,
            "payment_method": "card"
        },
        "ip_address": "192.168.1.100",
        "success": True
    },
    "payment_processed": {
        "user_id": 123,
        "action_type": "PROCESS",
        "resource_type": "payment",
        "resource_id": "PAY-2024-001",
        "details": {
            "order_id": "ORD-2024-001",
            "amount": 125.50,
            "payment_method": "card",
            "transaction_id": "txn_1234567890"
        },
        "ip_address": "192.168.1.100",
        "success": True
    },
    "inventory_updated": {
        "user_id": 456,
        "action_type": "UPDATE",
        "resource_type": "inventory",
        "resource_id": "INV-001",
        "details": {
            "item_name": "Coca Cola",
            "quantity_change": -5,
            "reason": "order_consumption",
            "order_id": "ORD-2024-001"
        },
        "ip_address": "192.168.1.101",
        "success": True
    }
}
