# modules/validation/schemas.py - Pydantic v2 Input Validation Models
from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field, validator, field_validator
import re

# Order Validation Models
class OrderItemCreate(BaseModel):
    """Schema for creating order items with validation"""
    menu_item_id: int = Field(gt=0, description="Menu item ID must be positive")
    quantity: int = Field(gt=0, le=100, description="Quantity must be between 1 and 100")
    special_instructions: Optional[str] = Field(max_length=500, description="Special instructions")
    
    @field_validator('special_instructions')
    @classmethod
    def sanitize_instructions(cls, v):
        if v:
            # Remove any potential XSS content
            v = re.sub(r'<script.*?>.*?</script>', '', v, flags=re.IGNORECASE | re.DOTALL)
            v = re.sub(r'<.*?>', '', v)  # Remove HTML tags
            v = v.strip()
        return v

class OrderCreate(BaseModel):
    """Schema for creating orders with validation"""
    table_id: Optional[int] = Field(None, gt=0, description="Table ID must be positive")
    customer_id: Optional[int] = Field(None, gt=0, description="Customer ID must be positive")
    items: List[OrderItemCreate] = Field(min_items=1, description="At least one item required")
    
    @field_validator('items')
    @classmethod
    def validate_items(cls, v):
        if not v:
            raise ValueError('At least one item is required')
        
        # Check for duplicate menu items
        menu_item_ids = [item.menu_item_id for item in v]
        if len(menu_item_ids) != len(set(menu_item_ids)):
            raise ValueError('Duplicate menu items are not allowed')
        
        return v

class OrderUpdate(BaseModel):
    """Schema for updating orders"""
    status: Optional[str] = Field(None, description="Order status")
    customer_id: Optional[int] = Field(None, gt=0, description="Customer ID must be positive")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v:
            valid_statuses = ['new', 'preparing', 'ready', 'served', 'paid', 'cancelled']
            if v not in valid_statuses:
                raise ValueError(f'Invalid status. Must be one of: {valid_statuses}')
        return v

# Payment Validation Models
class PaymentCreate(BaseModel):
    """Schema for creating payments with validation"""
    order_id: int = Field(gt=0, description="Order ID must be positive")
    method: str = Field(description="Payment method")
    amount: Decimal = Field(gt=0, decimal_places=2, description="Amount must be positive")
    cashier_id: int = Field(gt=0, description="Cashier ID must be positive")
    discount_code: Optional[str] = Field(max_length=50, description="Discount code")
    
    @field_validator('method')
    @classmethod
    def validate_method(cls, v):
        valid_methods = ['cash', 'card', 'online', 'loyalty_points']
        if v not in valid_methods:
            raise ValueError(f'Invalid payment method. Must be one of: {valid_methods}')
        return v
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        if v > Decimal('999999.99'):
            raise ValueError('Amount exceeds maximum limit')
        return v

# Inventory Validation Models
class InventoryItemCreate(BaseModel):
    """Schema for creating inventory items"""
    name: str = Field(min_length=1, max_length=100, description="Item name required")
    quantity: Decimal = Field(ge=0, decimal_places=3, description="Quantity must be non-negative")
    unit: str = Field(min_length=1, max_length=20, description="Unit required")
    min_quantity: Decimal = Field(ge=0, decimal_places=3, description="Min quantity must be non-negative")
    supplier: Optional[str] = Field(max_length=100, description="Supplier name")
    
    @field_validator('name')
    @classmethod
    def sanitize_name(cls, v):
        # Remove any potential SQL injection or XSS content
        v = re.sub(r'[;\'"]', '', v)  # Remove SQL injection characters
        v = re.sub(r'<.*?>', '', v)   # Remove HTML tags
        v = v.strip()
        if not v:
            raise ValueError('Name cannot be empty')
        return v
    
    @field_validator('unit')
    @classmethod
    def validate_unit(cls, v):
        valid_units = ['kg', 'g', 'l', 'ml', 'pcs', 'bottle', 'package']
        if v.lower() not in valid_units:
            raise ValueError(f'Invalid unit. Must be one of: {valid_units}')
        return v.lower()

class InventoryItemUpdate(BaseModel):
    """Schema for updating inventory items"""
    quantity: Optional[Decimal] = Field(None, ge=0, decimal_places=3)
    min_quantity: Optional[Decimal] = Field(None, ge=0, decimal_places=3)
    supplier: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    
    @field_validator('supplier')
    @classmethod
    def sanitize_supplier(cls, v):
        if v:
            v = re.sub(r'[;\'"]', '', v)
            v = re.sub(r'<.*?>', '', v)
            v = v.strip()
        return v

# User Validation Models
class UserCreate(BaseModel):
    """Schema for creating users"""
    username: str = Field(min_length=3, max_length=50, description="Username required")
    email: str = Field(description="Email required")
    password: str = Field(min_length=8, max_length=128, description="Password required")
    role: str = Field(description="User role required")
    full_name: Optional[str] = Field(max_length=100, description="Full name")
    phone: Optional[str] = Field(max_length=20, description="Phone number")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        # Username validation: alphanumeric + underscores only
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username can only contain letters, numbers, and underscores')
        return v.lower()
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        return v.lower()
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Check for at least one uppercase, one lowercase, and one digit
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        
        return v
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        valid_roles = ['admin', 'manager', 'waiter', 'cashier', 'kitchen']
        if v not in valid_roles:
            raise ValueError(f'Invalid role. Must be one of: {valid_roles}')
        return v

class UserLogin(BaseModel):
    """Schema for user login"""
    username: str = Field(min_length=1, description="Username required")
    password: str = Field(min_length=1, description="Password required")
    
    @field_validator('username')
    @classmethod
    def sanitize_username(cls, v):
        v = re.sub(r'[;\'"]', '', v)  # Remove SQL injection characters
        v = v.strip()
        if not v:
            raise ValueError('Username cannot be empty')
        return v

# API Response Models
class ApiResponse(BaseModel):
    """Standard API response model"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ValidationErrorResponse(BaseModel):
    """Validation error response"""
    success: bool = False
    error: str = "VALIDATION_ERROR"
    message: str
    details: Dict[str, List[str]]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Security Validation Functions
def sanitize_string(value: str, max_length: int = 100) -> str:
    """Sanitize string input to prevent XSS and SQL injection"""
    if not value:
        return ""
    
    # Remove SQL injection characters
    value = re.sub(r'[;\'"]', '', value)
    
    # Remove HTML tags (XSS prevention)
    value = re.sub(r'<script.*?>.*?</script>', '', value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r'<.*?>', '', value)
    
    # Remove dangerous characters
    value = re.sub(r'[<>&]', '', value)
    
    # Trim and limit length
    value = value.strip()[:max_length]
    
    return value

def validate_numeric_input(value: str, min_val: float = 0, max_val: float = 999999.99) -> Decimal:
    """Validate and convert numeric input"""
    try:
        num_value = Decimal(str(value))
        if num_value < min_val or num_value > max_val:
            raise ValueError(f'Value must be between {min_val} and {max_val}')
        return num_value
    except (ValueError, TypeError):
        raise ValueError('Invalid numeric input')

# Input Validation Decorator
def validate_input(schema_class: type[BaseModel]):
    """Decorator for input validation using Pydantic schemas"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            from flask import request, jsonify
            
            try:
                if request.is_json:
                    data = request.get_json()
                else:
                    data = request.form.to_dict()
                
                # Validate input
                validated_data = schema_class(**data)
                
                # Call the function with validated data
                return f(validated_data.dict(), *args, **kwargs)
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': 'VALIDATION_ERROR',
                    'message': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }), 400
        
        return wrapper
    return decorator
