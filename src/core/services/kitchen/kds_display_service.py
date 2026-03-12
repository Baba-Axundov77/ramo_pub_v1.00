# modules/kitchen/kds_display_service.py - Kitchen Display System
from __future__ import annotations
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_

from src.core.database.models import (
    Order, OrderItem, OrderStatus, MenuItem, 
    KitchenStation, ItemPreparationTime, KDSMessage
)

class KDSDisplayService:
    """Real-time kitchen display system with bump screens and timers"""
    
    def __init__(self):
        pass
    
    def get_kds_queue_by_station(self, db: Session, station_id: Optional[int] = None) -> Dict:
        """Get KDS queue filtered by kitchen station"""
        try:
            query = db.query(Order).options(
                joinedload(Order.items).joinedload(OrderItem.menu_item).joinedload(MenuItem.kitchen_station),
                joinedload(Order.table),
                joinedload(Order.waiter)
            ).filter(
                Order.status.in_([OrderStatus.new, OrderStatus.preparing]),
                Order.created_at >= datetime.utcnow().date()
            )
            
            if station_id:
                query = query.filter(MenuItem.kitchen_station_id == station_id)
            
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
                    'created_at': order.created_at.isoformat(),
                    'estimated_completion': self._calculate_estimated_completion(order).isoformat(),
                    'items': [],
                    'station': None
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
                        'prep_time_minutes': self._get_prep_time(db, item.menu_item_id),
                        'started_at': item.started_at.isoformat() if item.started_at else None,
                        'completed_at': item.completed_at.isoformat() if item.completed_at else None,
                        'time_remaining': self._calculate_time_remaining(item),
                        'station_id': item.menu_item.kitchen_station_id if item.menu_item else None,
                        'station_name': item.menu_item.kitchen_station.name if item.menu_item and item.menu_item.kitchen_station else None
                    }
                    order_data['items'].append(item_data)
                    
                    if item.menu_item and item.menu_item.kitchen_station:
                        order_data['station'] = item.menu_item.kitchen_station.name
                
                kds_data.append(order_data)
            
            return {
                'station_id': station_id,
                'orders': kds_data,
                'summary': {
                    'total_orders': len(kds_data),
                    'total_items': sum(len(o['items']) for o in kds_data),
                    'urgent_orders': len([o for o in kds_data if o['priority'] == 'high'])
                },
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def bump_next_order(self, db: Session, station_id: int) -> Dict:
        """Get next order for bump screen and mark as being prepared"""
        try:
            next_order = db.query(Order).options(
                joinedload(Order.items).joinedload(OrderItem.menu_item),
                joinedload(Order.table)
            ).join(OrderItem).join(MenuItem).filter(
                Order.status == OrderStatus.new,
                MenuItem.kitchen_station_id == station_id
            ).order_by(
                Order.priority.desc(),
                Order.created_at.asc()
            ).first()
            
            if not next_order:
                return {
                    'status': 'no_orders',
                    'message': 'Hazırda sifariş yoxdur',
                    'station_id': station_id
                }
            
            # Mark order as being prepared
            next_order.status = OrderStatus.preparing
            next_order.preparation_started_at = datetime.utcnow()
            
            # Mark all items as being prepared
            for item in next_order.items:
                if not item.is_voided:
                    item.status = OrderStatus.preparing
                    item.started_at = datetime.utcnow()
            
            db.commit()
            
            return {
                'status': 'order_bumped',
                'order': {
                    'id': next_order.id,
                    'table': next_order.table.number if next_order.table else None,
                    'customer_name': next_order.customer_name,
                    'items': [
                        {
                            'name': item.menu_item.name if item.menu_item else 'Unknown',
                            'quantity': item.quantity,
                            'notes': item.notes
                        } for item in next_order.items if not item.is_voided
                    ],
                    'total_time_estimate': self._calculate_estimated_completion(next_order).isoformat()
                },
                'station_id': station_id,
                'bumped_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            db.rollback()
            return {'error': str(e)}
    
    def complete_item_preparation(self, db: Session, item_id: int, 
                               staff_id: int) -> Dict:
        """Complete item preparation and track time"""
        try:
            item = db.query(OrderItem).options(
                joinedload(OrderItem.menu_item),
                joinedload(OrderItem.order)
            ).filter(OrderItem.id == item_id).first()
            
            if not item:
                return {'error': 'Order item tapılmadı'}
            
            if item.status == OrderStatus.ready:
                return {'warning': 'Item artıq hazır qeyd edilib'}
            
            # Mark item as ready
            item.status = OrderStatus.ready
            item.completed_at = datetime.utcnow()
            item.prepared_by = staff_id
            
            # Track preparation time
            prep_time_seconds = 0
            if item.started_at:
                prep_time_seconds = (item.completed_at - item.started_at).total_seconds()
                self._update_prep_time_tracking(db, item.menu_item_id, prep_time_seconds)
            
            # Check if all items in order are ready
            self._check_order_completion(db, item.order_id)
            
            db.commit()
            
            return {
                'success': True,
                'item_id': item_id,
                'item_name': item.menu_item.name if item.menu_item else 'Unknown',
                'prep_time_seconds': prep_time_seconds,
                'completed_at': item.completed_at.isoformat()
            }
            
        except Exception as e:
            db.rollback()
            return {'error': str(e)}
    
    def send_kds_message(self, db: Session, station_id: int, 
                        message: str, message_type: str = 'info',
                        order_id: Optional[int] = None) -> Dict:
        """Send message to KDS display"""
        try:
            kds_msg = KDSMessage(
                station_id=station_id,
                message=message,
                message_type=message_type,
                order_id=order_id,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            db.add(kds_msg)
            db.commit()
            
            return {
                'success': True,
                'message_id': kds_msg.id,
                'station_id': station_id,
                'message': message,
                'created_at': kds_msg.created_at.isoformat()
            }
            
        except Exception as e:
            db.rollback()
            return {'error': str(e)}
    
    def get_active_kds_messages(self, db: Session, station_id: int) -> List[Dict]:
        """Get active KDS messages for a station"""
        try:
            messages = db.query(KDSMessage).filter(
                KDSMessage.station_id == station_id,
                KDSMessage.expires_at > datetime.utcnow()
            ).order_by(KDSMessage.created_at.desc()).all()
            
            return [
                {
                    'id': msg.id,
                    'message': msg.message,
                    'message_type': msg.message_type,
                    'order_id': msg.order_id,
                    'created_at': msg.created_at.isoformat()
                } for msg in messages
            ]
            
        except Exception as e:
            return []
    
    def get_station_performance(self, db: Session, station_id: int, 
                               start_date: datetime, end_date: datetime) -> Dict:
        """Get performance metrics for a kitchen station"""
        try:
            # Get completed items for this station
            items = db.query(OrderItem).options(
                joinedload(OrderItem.menu_item)
            ).join(MenuItem).filter(
                MenuItem.kitchen_station_id == station_id,
                OrderItem.completed_at >= start_date,
                OrderItem.completed_at <= end_date,
                OrderItem.status == OrderStatus.ready
            ).all()
            
            if not items:
                return {
                    'station_id': station_id,
                    'period': {
                        'start': start_date.isoformat(),
                        'end': end_date.isoformat()
                    },
                    'metrics': {
                        'total_items': 0,
                        'avg_prep_time': 0,
                        'fastest_item': None,
                        'slowest_item': None
                    }
                }
            
            # Calculate metrics
            prep_times = []
            for item in items:
                if item.started_at and item.completed_at:
                    prep_time = (item.completed_at - item.started_at).total_seconds()
                    prep_times.append({
                        'item_name': item.menu_item.name if item.menu_item else 'Unknown',
                        'prep_time': prep_time,
                        'quantity': item.quantity
                    })
            
            avg_prep_time = sum(p['prep_time'] for p in prep_times) / len(prep_times) if prep_times else 0
            
            return {
                'station_id': station_id,
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'metrics': {
                    'total_items': len(items),
                    'avg_prep_time_seconds': round(avg_prep_time, 2),
                    'avg_prep_time_minutes': round(avg_prep_time / 60, 2) if avg_prep_time > 0 else 0,
                    'fastest_item': min(prep_times, key=lambda x: x['prep_time']) if prep_times else None,
                    'slowest_item': max(prep_times, key=lambda x: x['prep_time']) if prep_times else None,
                    'items_by_prep_time': prep_times
                }
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _calculate_estimated_completion(self, order: Order) -> datetime:
        """Calculate estimated completion time for an order"""
        if not order.items:
            return datetime.utcnow() + timedelta(minutes=5)
        
        total_prep_time = 0
        for item in order.items:
            if not item.is_voided and item.menu_item:
                prep_time = self._get_prep_time(None, item.menu_item_id)
                total_prep_time += prep_time * item.quantity
        
        return order.created_at + timedelta(minutes=total_prep_time)
    
    def _get_prep_time(self, db: Optional[Session], menu_item_id: int) -> int:
        """Get preparation time for menu item"""
        if db:
            prep_time = db.query(ItemPreparationTime).filter(
                ItemPreparationTime.menu_item_id == menu_item_id
            ).first()
            return prep_time.prep_time_minutes if prep_time else 5
        else:
            # Default times based on item type
            return 5  # 5 minutes default
    
    def _calculate_time_remaining(self, item: OrderItem) -> Optional[int]:
        """Calculate remaining time for item preparation"""
        if not item.started_at:
            return None
        
        if item.completed_at:
            return 0
        
        prep_time = self._get_prep_time(None, item.menu_item_id) * item.quantity
        elapsed = (datetime.utcnow() - item.started_at).total_seconds()
        remaining = prep_time - elapsed
        return max(0, int(remaining))
    
    def _update_prep_time_tracking(self, db: Session, menu_item_id: int, actual_time: float):
        """Update preparation time tracking"""
        if not db:
            return
        
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
    
    def _check_order_completion(self, db: Session, order_id: int):
        """Check if all items in order are ready and update order status"""
        items = db.query(OrderItem).filter(
            OrderItem.order_id == order_id,
            OrderItem.is_voided == False
        ).all()
        
        if all(item.status == OrderStatus.ready for item in items):
            order = db.query(Order).filter(Order.id == order_id).first()
            if order:
                order.status = OrderStatus.ready
                order.ready_at = datetime.utcnow()

kds_display_service = KDSDisplayService()
