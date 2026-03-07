# modules/payments/payment_gateway_service.py - Enterprise Payment Processing
from __future__ import annotations
from typing import Dict, Optional, Tuple, List
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from dataclasses import dataclass
import requests
import json

from database.models import Payment, Order, PaymentMethod, PaymentStatus

@dataclass
class CardPaymentData:
    card_number: str
    expiry_month: str
    expiry_year: str
    cvv: str
    cardholder_name: str
    amount: Decimal

@dataclass
class PaymentResponse:
    success: bool
    transaction_id: Optional[str]
    error_message: Optional[str]
    auth_code: Optional[str]
    card_type: Optional[str]

class PaymentGatewayService:
    """Enterprise payment processing with multiple gateway support"""
    
    def __init__(self):
        self.gateway_config = self._load_gateway_config()
    
    def process_card_payment(self, db: Session, order_id: int, 
                           payment_data: CardPaymentData) -> Tuple[bool, PaymentResponse]:
        """Process card payment through payment gateway"""
        try:
            # Validate payment data
            validation_result = self._validate_card_data(payment_data)
            if not validation_result['valid']:
                return False, PaymentResponse(
                    success=False,
                    error_message=validation_result['error']
                )
            
            # Get order details
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                return False, PaymentResponse(
                    success=False,
                    error_message="Order tapılmadı"
                )
            
            # Prepare gateway request
            gateway_request = {
                'merchant_id': self.gateway_config['merchant_id'],
                'transaction_id': f"ORD-{order_id}-{datetime.utcnow().timestamp()}",
                'amount': float(payment_data.amount),
                'currency': 'AZN',
                'card_number': payment_data.card_number,
                'expiry_month': payment_data.expiry_month,
                'expiry_year': payment_data.expiry_year,
                'cvv': payment_data.cvv,
                'cardholder_name': payment_data.cardholder_name,
                'description': f"Ramo Pub Order #{order_id}"
            }
            
            # Call payment gateway
            gateway_response = self._call_payment_gateway(gateway_request)
            
            if gateway_response['success']:
                # Create payment record
                payment = Payment(
                    order_id=order_id,
                    method=PaymentMethod.card,
                    amount=payment_data.amount,
                    final_amount=payment_data.amount,
                    transaction_id=gateway_response['transaction_id'],
                    auth_code=gateway_response['auth_code'],
                    card_type=gateway_response['card_type'],
                    status=PaymentStatus.completed,
                    created_at=datetime.utcnow()
                )
                db.add(payment)
                
                # Update order status
                order.status = 'paid'
                order.paid_at = datetime.utcnow()
                
                db.commit()
                
                return True, PaymentResponse(
                    success=True,
                    transaction_id=gateway_response['transaction_id'],
                    auth_code=gateway_response['auth_code'],
                    card_type=gateway_response['card_type']
                )
            else:
                # Log failed payment
                failed_payment = Payment(
                    order_id=order_id,
                    method=PaymentMethod.card,
                    amount=payment_data.amount,
                    final_amount=Decimal('0.00'),
                    status=PaymentStatus.failed,
                    error_message=gateway_response['error_message'],
                    created_at=datetime.utcnow()
                )
                db.add(failed_payment)
                db.commit()
                
                return False, PaymentResponse(
                    success=False,
                    error_message=gateway_response['error_message']
                )
                
        except Exception as e:
            db.rollback()
            return False, PaymentResponse(
                success=False,
                error_message=f"Payment processing xətası: {str(e)}"
            )
    
    def process_refund(self, db: Session, payment_id: int, 
                     refund_amount: Decimal, reason: str) -> Tuple[bool, str]:
        """Process refund through payment gateway"""
        try:
            payment = db.query(Payment).filter(Payment.id == payment_id).first()
            if not payment:
                return False, "Payment tapılmadı"
            
            if payment.status != PaymentStatus.completed:
                return False, "Bu payment üçün refund mümkün deyil"
            
            if refund_amount > payment.final_amount:
                return False, "Refund məbləği payment məbləğindən çoxdur"
            
            # Prepare refund request
            refund_request = {
                'merchant_id': self.gateway_config['merchant_id'],
                'original_transaction_id': payment.transaction_id,
                'refund_amount': float(refund_amount),
                'reason': reason,
                'currency': 'AZN'
            }
            
            # Call gateway refund endpoint
            refund_response = self._call_refund_gateway(refund_request)
            
            if refund_response['success']:
                # Create refund record
                refund_payment = Payment(
                    order_id=payment.order_id,
                    method=PaymentMethod.card,
                    amount=-refund_amount,  # Negative for refund
                    final_amount=-refund_amount,
                    transaction_id=refund_response['refund_transaction_id'],
                    auth_code=refund_response['refund_auth_code'],
                    status=PaymentStatus.refunded,
                    parent_payment_id=payment_id,
                    reason=reason,
                    created_at=datetime.utcnow()
                )
                db.add(refund_payment)
                db.commit()
                
                return True, f"Refund uğurla: {refund_response['refund_transaction_id']}"
            else:
                return False, f"Refund xətası: {refund_response['error_message']}"
                
        except Exception as e:
            db.rollback()
            return False, f"Refund processing xətası: {str(e)}"
    
    def process_contactless_payment(self, db: Session, order_id: int, 
                                tap_data: Dict) -> Tuple[bool, PaymentResponse]:
        """Process NFC/contactless payment"""
        try:
            # Extract data from tap
            payment_data = {
                'merchant_id': self.gateway_config['merchant_id'],
                'transaction_id': f"TAP-{order_id}-{datetime.utcnow().timestamp()}",
                'amount': float(tap_data.get('amount', 0)),
                'currency': 'AZN',
                'tap_token': tap_data.get('tap_token'),
                'device_id': tap_data.get('device_id'),
                'description': f"Ramo Pub Contactless Order #{order_id}"
            }
            
            # Process through contactless endpoint
            response = self._call_contactless_gateway(payment_data)
            
            if response['success']:
                payment = Payment(
                    order_id=order_id,
                    method=PaymentMethod.card,  # Treat as card
                    amount=Decimal(str(tap_data['amount'])),
                    final_amount=Decimal(str(tap_data['amount'])),
                    transaction_id=response['transaction_id'],
                    auth_code=response['auth_code'],
                    card_type='CONTACTLESS',
                    status=PaymentStatus.completed,
                    created_at=datetime.utcnow()
                )
                db.add(payment)
                db.commit()
                
                return True, PaymentResponse(
                    success=True,
                    transaction_id=response['transaction_id']
                )
            else:
                return False, PaymentResponse(
                    success=False,
                    error_message=response['error_message']
                )
                
        except Exception as e:
            return False, PaymentResponse(
                success=False,
                error_message=f"Contactless payment xətası: {str(e)}"
            )
    
    def get_payment_status(self, db: Session, transaction_id: str) -> Dict:
        """Check payment status from gateway"""
        try:
            status_request = {
                'merchant_id': self.gateway_config['merchant_id'],
                'transaction_id': transaction_id
            }
            
            response = self._call_status_gateway(status_request)
            
            # Update local payment record
            payment = db.query(Payment).filter(
                Payment.transaction_id == transaction_id
            ).first()
            
            if payment and response['status_updated']:
                payment.status = response['status']
                if response['status'] == PaymentStatus.settled:
                    payment.settled_at = datetime.utcnow()
                db.commit()
            
            return {
                'local_status': payment.status if payment else None,
                'gateway_status': response['status'],
                'amount': response['amount'],
                'currency': response['currency']
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _validate_card_data(self, payment_data: CardPaymentData) -> Dict:
        """Validate card payment data"""
        errors = []
        
        # Basic card number validation (Luhn algorithm would be better)
        if not payment_data.card_number or len(payment_data.card_number) < 13:
            errors.append("Kart nömrəsi etibarsızdır")
        
        # Expiry validation
        current_year = datetime.now().year
        if not payment_data.expiry_year or int(payment_data.expiry_year) < current_year:
            errors.append("Kartın vaxtı keçib")
        
        if not payment_data.cvv or len(payment_data.cvv) < 3:
            errors.append("CVV etibarsızdır")
        
        if payment_data.amount <= 0:
            errors.append("Məbləğ etibarsızdır")
        
        return {
            'valid': len(errors) == 0,
            'error': '; '.join(errors) if errors else None
        }
    
    def _call_payment_gateway(self, request_data: Dict) -> Dict:
        """Call payment gateway API"""
        try:
            # Mock implementation - replace with actual gateway
            if self.gateway_config['test_mode']:
                # Test mode - always succeed
                return {
                    'success': True,
                    'transaction_id': f"TEST-{datetime.utcnow().timestamp()}",
                    'auth_code': 'AUTH123',
                    'card_type': 'VISA'
                }
            
            # Real implementation would call actual gateway
            response = requests.post(
                self.gateway_config['api_url'],
                json=request_data,
                headers=self.gateway_config['headers'],
                timeout=30
            )
            
            return response.json()
            
        except Exception as e:
            return {
                'success': False,
                'error_message': str(e)
            }
    
    def _load_gateway_config(self) -> Dict:
        """Load payment gateway configuration"""
        # This would typically come from environment variables or config
        return {
            'merchant_id': 'your_merchant_id',
            'api_url': 'https://api.payment-gateway.com/v1/charge',
            'refund_url': 'https://api.payment-gateway.com/v1/refund',
            'status_url': 'https://api.payment-gateway.com/v1/status',
            'test_mode': True,  # Set to False in production
            'headers': {
                'Authorization': 'Bearer your_api_key',
                'Content-Type': 'application/json'
            }
        }

payment_gateway_service = PaymentGatewayService()
