# modules/kitchen/advanced_kitchen_service.py - Enterprise-level Kitchen Display System
from __future__ import annotations
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, and_, or_

from database.models import (
    Order, OrderItem, OrderStatus, MenuItem, 
    KitchenStation, ItemPreparationTime, KDSMessage
)

class AdvancedKitchenService:
    """Enterprise-level kitchen display system with bump screens and timers"""
    
    def __init__(self):
        pass
    
    def get_kds_queue(self, db: Session, station_id: Optional[int] = None) -> List[Dict]:
        """Get KDS queue with preparation times and priority"""
        try:
            query = db.query(Order).options(
                joinedload(Order.items).joinedload(OrderItem.menu_item),
                joinedload(Order.table),
                joinedload(Order.waiter)
            ).filter(
                Order.status.in_([OrderStatus.new, OrderStatus.preparing]),
                Order.created_at >= datetime.utcnow().date()
            )
            
            if station_id:
                # Filter by kitchen station
                query = query.join(MenuItem, OrderItem.menu_item_id == MenuItem.id).filter(
                    MenuItem.kitchen_station_id == station_id
                )
            
            orders = query.order_by(
                Order.priority.desc(),
                Order.created_at.asc()
            ).all()
            
            kds_data = []
            for order in orders:
                order_data = {
                    'id': order.id,
                    'table_number': order.table.number if order.table else None,
                    'customer_name': order.customer_name,
                    'priority': order.priority,
                    'created_at': order.created_at,
                    'estimated_completion': self._calculate_estimated_completion(order),
                    'items': []
                }
                
                for item in order.items:
                    if item.is_voided:
                        continue
                    
                    item_data = {
                        'id': item.id,
                        'name': item.menu_item.name if item.menu_item else 'Unknown',
                        'quantity': item.quantity,
                        'notes': item.notes,
                        'status': item.status,
                        'prep_time': self._get_prep_time(db, item.menu_item_id),
                        'started_at': item.started_at,
                        'completed_at': item.completed_at,
                        'station': item.menu_item.kitchen_station.name if item.menu_item.kitchen_station else None
                    }
                    order_data['items'].append(item_data)
                
                kds_data.append(order_data)
            
            return kds_data
            
        except Exception as e:
            print(f"KDS queue xətası: {str(e)}")
            return []
    
    def bump_screen(self, db: Session, station_id: int) -> Dict:
        """Get next order for bump screen"""
        try:
            next_order = db.query(Order).options(
                joinedload(Order.items).joinedload(OrderItem.menu_item),
                joinedload(Order.table)
            ).join(OrderItem, MenuItem).filter(
                Order.status == OrderStatus.new,
                MenuItem.kitchen_station_id == station_id
            ).order_by(
                Order.priority.desc(),
                Order.created_at.asc()
            ).first()
            
            if not next_order:
                return {'status': 'no_orders', 'order': None}
            
            return {
                'status': 'order_ready',
                'order': {
                    'id': next_order.id,
                    'table': next_order.table.number if next_order.table else None,
                    'items': [
                        {
                            'name': item.menu_item.name,
                            'quantity': item.quantity,
                            'notes': item.notes
                        } for item in next_order.items if not item.is_voided
                    ],
                    'total_time': self._calculate_estimated_completion(next_order)
                }
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def start_item_preparation(self, db: Session, item_id: int, 
                             staff_id: int) -> Tuple[bool, str]:
        """Start preparation timer for specific item"""
        try:
            item = db.query(OrderItem).filter(OrderItem.id == item_id).first()
            if not item:
                return False, "Item tapılmadı"
            
            item.status = OrderStatus.preparing
            item.started_at = datetime.utcnow()
            item.prepared_by = staff_id
            
            db.commit()
            return True, "Hazırlığa başlandı"
            
        except Exception as e:
            db.rollback()
            return False, f"Start preparation xətası: {str(e)}"
    
    def complete_item_preparation(self, db: Session, item_id: int, 
                               staff_id: int) -> Tuple[bool, str]:
        """Complete item preparation and track time"""
        try:
            item = db.query(OrderItem).filter(OrderItem.id == item_id).first()
            if not item:
                return False, "Item tapılmadı"
            
            item.status = OrderStatus.ready
            item.completed_at = datetime.utcnow()
            item.prepared_by = staff_id
            
            # Track preparation time for analytics
            if item.started_at:
                prep_time = (item.completed_at - item.started_at).total_seconds()
                self._track_preparation_time(db, item.menu_item_id, prep_time)
            
            # Check if all items in order are ready
            self._update_order_status(db, item.order_id)
            
            db.commit()
            return True, "Hazırlıq tamamlandı"
            
        except Exception as e:
            db.rollback()
            return False, f"Complete preparation xətası: {str(e)}"
    
    def send_kds_message(self, db: Session, station_id: int, 
                        message: str, message_type: str = 'info',
                        order_id: Optional[int] = None) -> Tuple[bool, str]:
        """Send message to KDS display"""
        try:
            kds_msg = KDSMessage(
                station_id=station_id,
                message=message,
                message_type=message_type,
                order_id=order_id,
                created_at=datetime.utcnow()
            )
            db.add(kds_msg)
            db.commit()
            return True, "Mesaj göndərildi"
            
        except Exception as e:
            db.rollback()
            return False, f"KDS message xətası: {str(e)}"
    
    def get_ingredient_shortages(self, db: Session) -> List[Dict]:
        """Check for ingredient shortages based on current orders"""
        try:
            # Get all pending order items
            pending_items = db.query(OrderItem).join(Order).filter(
                Order.status.in_([OrderStatus.new, OrderStatus.preparing]),
                OrderItem.is_voided == False
            ).all()
            
            # Calculate required ingredients
            required_ingredients = {}
            for item in pending_items:
                if item.menu_item:
                    ingredients = self._get_item_ingredients(db, item.menu_item_id)
                    for ing in ingredients:
                        required_ingredients[ing['id']] = required_ingredients.get(ing['id'], 0) + (ing['quantity'] * item.quantity)
            
            # Check current inventory
            shortages = []
            for ingredient_id, required_qty in required_ingredients.items():
                current_stock = self._get_current_stock(db, ingredient_id)
                if current_stock < required_qty:
                    shortages.append({
                        'ingredient_id': ingredient_id,
                        'ingredient_name': self._get_ingredient_name(db, ingredient_id),
                        'required': required_qty,
                        'available': current_stock,
                        'shortage': required_qty - current_stock
                    })
            
            return shortages
            
        except Exception as e:
            print(f"Ingredient shortage check xətası: {str(e)}")
            return []
    
    def _calculate_estimated_completion(self, order: Order) -> datetime:
        """Calculate estimated completion time based on items"""
        if not order.items:
            return datetime.utcnow() + timedelta(minutes=5)
        
        total_prep_time = 0
        for item in order.items:
            if not item.is_voided and item.menu_item:
                # Get average prep time for this item
                avg_time = self._get_avg_prep_time(item.menu_item_id)
                total_prep_time += avg_time * item.quantity
        
        return order.created_at + timedelta(minutes=total_prep_time)
    
    def _get_prep_time(self, db: Session, menu_item_id: int) -> int:
        """Get preparation time for menu item"""
        prep_time = db.query(ItemPreparationTime).filter(
            ItemPreparationTime.menu_item_id == menu_item_id
        ).first()
        return prep_time.prep_time_minutes if prep_time else 5
    
    def _track_preparation_time(self, db: Session, menu_item_id: int, actual_time: float):
        """Track actual preparation time for analytics"""
        # Update average preparation time
        existing = db.query(ItemPreparationTime).filter(
            ItemPreparationTime.menu_item_id == menu_item_id
        ).first()
        
        if existing:
            # Update running average
            existing.prep_count += 1
            existing.prep_time_minutes = (
                (existing.prep_time_minutes * (existing.prep_count - 1) + actual_time / 60) / existing.prep_count
            )
        else:
            # Create new record
            new_prep_time = ItemPreparationTime(
                menu_item_id=menu_item_id,
                prep_time_minutes=actual_time / 60,
                prep_count=1
            )
            db.add(new_prep_time)
    
    def _update_order_status(self, db: Session, order_id: int):
        """Update order status based on item completion"""
        items = db.query(OrderItem).filter(
            OrderItem.order_id == order_id,
            OrderItem.is_voided == False
        ).all()
        
        if all(item.status == OrderStatus.ready for item in items):
            order = db.query(Order).filter(Order.id == order_id).first()
            order.status = OrderStatus.ready
            db.commit()

advanced_kitchen_service = AdvancedKitchenService()
