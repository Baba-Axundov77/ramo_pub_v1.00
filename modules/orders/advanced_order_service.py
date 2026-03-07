# modules/orders/advanced_order_service.py - Enterprise-level Order Management
from __future__ import annotations
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, and_, or_

from database.models import (
    Order, OrderItem, Payment, OrderStatus, 
    PaymentMethod, OrderModification, TipDistribution,
    User, Customer, MenuItem, Table
)

class AdvancedOrderService:
    """Enterprise-level order management with split payments, modifications, and tips"""
    
    def __init__(self, db: Session = None):
        self.db = db
    
    def create_split_payment_order(self, db: Session, order_data: Dict[str, Any]) -> Tuple[bool, object]:
        """Create order with split payment capabilities"""
        try:
            # Create main order
            order = Order(
                table_id=order_data['table_id'],
                waiter_id=order_data['waiter_id'],
                customer_id=order_data.get('customer_id'),
                status='new',
                subtotal=0.0,
                total_amount=0.0,
                notes=order_data.get('notes', ''),
                created_at=datetime.now(),
                priority=order_data.get('priority', 'normal')
            )
            db.add(order)
            db.flush()
            
            # Add order items
            total_amount = 0.0
            for item_data in order_data['items']:
                menu_item = db.query(MenuItem).filter(MenuItem.id == item_data['menu_item_id']).first()
                if menu_item:
                    order_item = OrderItem(
                        order_id=order.id,
                        menu_item_id=item_data['menu_item_id'],
                        quantity=item_data['quantity'],
                        unit_price=menu_item.price,
                        subtotal=menu_item.price * item_data['quantity'],
                        notes=item_data.get('notes', ''),
                        status='pending'
                    )
                    db.add(order_item)
                    total_amount += order_item.subtotal
            
            # Update order totals
            order.subtotal = total_amount
            order.total_amount = total_amount
            
            # Mark as split payment order
            order.notes += " [SPLIT PAYMENT]"
            
            db.commit()
            
            return True, {
                'order_id': order.id,
                'total_amount': total_amount,
                'message': 'Split payment order created successfully'
            }
            
        except Exception as e:
            db.rollback()
            return False, f"Failed to create split payment order: {str(e)}"
    
    def process_split_payment(self, db: Session, order_id: int, 
                         cash_amount: Decimal = Decimal('0.00'),
                         card_amount: Decimal = Decimal('0.00'),
                         online_amount: Decimal = Decimal('0.00'),
                         tip_amount: Decimal = Decimal('0.00'),
                         processed_by: int = None) -> Tuple[bool, object]:
        """Process split payment across multiple tender types"""
        try:
            order = db.query(Order).options(
                joinedload(Order.items),
                joinedload(Order.table)
            ).filter(Order.id == order_id).first()
            
            if not order:
                return False, "Order tapılmadı"
            
            total_amount = cash_amount + card_amount + online_amount
            if total_amount != order.total:
                return False, f"Ödəniş məbləği uyğun deyil: {total_amount} vs {order.total}"
            
            # Create multiple payment records
            payments = []
            if cash_amount > 0:
                payment = Payment(
                    order_id=order_id,
                    method=PaymentMethod.cash,
                    amount=cash_amount,
                    final_amount=cash_amount,
                    processed_by=processed_by,
                    created_at=datetime.utcnow()
                )
                db.add(payment)
                payments.append(payment)
            
            if card_amount > 0:
                payment = Payment(
                    order_id=order_id,
                    method=PaymentMethod.card,
                    amount=card_amount,
                    final_amount=card_amount,
                    processed_by=processed_by,
                    created_at=datetime.utcnow()
                )
                db.add(payment)
                payments.append(payment)
            
            if online_amount > 0:
                payment = Payment(
                    order_id=order_id,
                    method=PaymentMethod.online,
                    amount=online_amount,
                    final_amount=online_amount,
                    processed_by=processed_by,
                    created_at=datetime.utcnow()
                )
                db.add(payment)
                payments.append(payment)
            
            # Update order status
            order.status = OrderStatus.paid
            order.paid_at = datetime.utcnow()
            
            # Update table status
            if order.table:
                order.table.status = 'available'
            
            db.commit()
            
            return True, {
                'order_id': order_id,
                'payments': [{'method': p.method.value, 'amount': float(p.amount)} for p in payments],
                'message': 'Split payment processed successfully'
            }
            
        except Exception as e:
            db.rollback()
            return False, f"Split payment failed: {str(e)}"
    
    def modify_order(self, db: Session, order_id: int, modifications: Dict[str, Any]) -> Tuple[bool, object]:
        """Modify existing order with tracking"""
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                return False, "Order not found"
            
            if order.status in ['paid', 'cancelled']:
                return False, "Cannot modify paid or cancelled order"
            
            # Create modification record
            modification = OrderModification(
                order_id=order_id,
                modified_by=modifications['modified_by'],
                modification_type=modifications['type'],  # 'add', 'remove', 'update'
                old_data=str({
                    'items': [{'id': item.id, 'quantity': item.quantity, 'price': item.unit_price} 
                            for item in order.items]
                }),
                new_data=str(modifications.get('items', [])),
                reason=modifications.get('reason', ''),
                created_at=datetime.now()
            )
            db.add(modification)
            
            # Process modifications based on type
            if modifications['type'] == 'add':
                for item_data in modifications['items']:
                    menu_item = db.query(MenuItem).filter(MenuItem.id == item_data['menu_item_id']).first()
                    if menu_item:
                        order_item = OrderItem(
                            order_id=order_id,
                            menu_item_id=item_data['menu_item_id'],
                            quantity=item_data['quantity'],
                            unit_price=menu_item.price,
                            subtotal=menu_item.price * item_data['quantity'],
                            notes=item_data.get('notes', ''),
                            status='pending'
                        )
                        db.add(order_item)
            
            elif modifications['type'] == 'remove':
                for item_id in modifications['item_ids']:
                    order_item = db.query(OrderItem).filter(
                        OrderItem.id == item_id,
                        OrderItem.order_id == order_id
                    ).first()
                    if order_item:
                        order_item.status = 'cancelled'
            
            elif modifications['type'] == 'update':
                for item_data in modifications['items']:
                    order_item = db.query(OrderItem).filter(
                        OrderItem.id == item_data['item_id'],
                        OrderItem.order_id == order_id
                    ).first()
                    if order_item:
                        order_item.quantity = item_data['quantity']
                        order_item.subtotal = order_item.unit_price * item_data['quantity']
                        order_item.notes = item_data.get('notes', order_item.notes)
            
            # Recalculate order totals
            active_items = db.query(OrderItem).filter(
                OrderItem.order_id == order_id,
                OrderItem.status != 'cancelled'
            ).all()
            
            order.subtotal = sum(item.subtotal for item in active_items)
            order.total_amount = order.subtotal
            order.updated_at = datetime.now()
            
            # Update order notes
            order.notes += f" [Modified: {modifications['type']} by {modifications['modified_by']}]"
            
            db.commit()
            
            return True, {
                'order_id': order_id,
                'modification_id': modification.id,
                'new_total': order.total_amount,
                'message': 'Order modified successfully'
            }
            
        except Exception as e:
            db.rollback()
            return False, f"Failed to modify order: {str(e)}"
    
    def get_order_history(self, db: Session, customer_id: Optional[int] = None, 
                         table_id: Optional[int] = None,
                         date_from: Optional[datetime] = None,
                         date_to: Optional[datetime] = None,
                         limit: int = 50) -> Tuple[bool, object]:
        """Get comprehensive order history with filters"""
        try:
            query = db.query(Order).options(
                joinedload(Order.table),
                joinedload(Order.waiter),
                joinedload(Order.customer),
                selectinload(Order.items).joinedload(OrderItem.menu_item),
                joinedload(Order.payment)
            )
            
            # Apply filters
            if customer_id:
                query = query.filter(Order.customer_id == customer_id)
            if table_id:
                query = query.filter(Order.table_id == table_id)
            if date_from:
                query = query.filter(Order.created_at >= date_from)
            if date_to:
                query = query.filter(Order.created_at <= date_to)
            
            orders = query.order_by(Order.created_at.desc()).limit(limit).all()
            
            # Format response
            order_history = []
            for order in orders:
                order_data = {
                    'id': order.id,
                    'table_number': order.table.number if order.table else None,
                    'waiter_name': order.waiter.full_name if order.waiter else None,
                    'customer_name': order.customer.full_name if order.customer else None,
                    'status': order.status.value,
                    'subtotal': float(order.subtotal),
                    'total_amount': float(order.total_amount),
                    'notes': order.notes,
                    'created_at': order.created_at.isoformat(),
                    'paid_at': order.paid_at.isoformat() if order.paid_at else None,
                    'items': [
                        {
                            'id': item.id,
                            'menu_item_name': item.menu_item.name,
                            'quantity': item.quantity,
                            'unit_price': float(item.unit_price),
                            'subtotal': float(item.subtotal),
                            'status': item.status,
                            'notes': item.notes
                        }
                        for item in order.items
                    ],
                    'payment': {
                        'method': order.payment.method.value,
                        'amount': float(order.payment.amount),
                        'status': order.payment.status
                    } if order.payment else None,
                    'modifications': [
                        {
                            'id': mod.id,
                            'type': mod.modification_type,
                            'reason': mod.reason,
                            'created_at': mod.created_at.isoformat()
                        }
                        for mod in order.modifications
                    ]
                }
                order_history.append(order_data)
            
            return True, {
                'orders': order_history,
                'total_count': len(order_history),
                'message': 'Order history retrieved successfully'
            }
            
        except Exception as e:
            return False, f"Failed to retrieve order history: {str(e)}"

# Create service instance
advanced_order_service = AdvancedOrderService()
