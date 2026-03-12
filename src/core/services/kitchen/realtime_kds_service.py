# Real-time Kitchen Display System (KDS)
# Advanced KDS with bump screens and real-time updates

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, and_, or_
from src.core.database.models import (
    Order, OrderItem, OrderStatus, KitchenStation, User, MenuItem
)
import json
from collections import defaultdict

class RealTimeKDSService:
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_kitchen_queue(self, station_id: Optional[int] = None) -> Dict[str, Any]:
        """Get real-time kitchen queue with priority sorting"""
        try:
            query = self.db.query(Order).options(
                joinedload(Order.table),
                joinedload(Order.waiter),
                selectinload(Order.items).joinedload(OrderItem.menu_item)
            ).filter(
                Order.status.in_(['new', 'preparing']),
                Order.created_at >= datetime.now() - timedelta(hours=2)  # Last 2 hours
            )
            
            if station_id:
                # Filter by station if specified
                station = self.db.query(KitchenStation).filter(KitchenStation.id == station_id).first()
                if station and station.station_type != 'all':
                    query = query.join(OrderItem).join(MenuItem).filter(
                        MenuItem.category_id == station.station_type
                    )
            
            orders = query.order_by(
                Order.priority.desc(),  # High priority first
                Order.created_at.asc()   # Then by time
            ).all()
            
            # Format for KDS display
            kitchen_queue = []
            for order in orders:
                order_data = {
                    'id': order.id,
                    'table_number': order.table.number if order.table else None,
                    'waiter_name': order.waiter.full_name if order.waiter else None,
                    'priority': order.priority,
                    'created_at': order.created_at.isoformat(),
                    'estimated_completion': order.estimated_completion.isoformat() if order.estimated_completion else None,
                    'notes': order.notes,
                    'items': []
                }
                
                for item in order.items:
                    if item.status in ['pending', 'preparing']:
                        item_data = {
                            'id': item.id,
                            'menu_item_name': item.menu_item.name,
                            'quantity': item.quantity,
                            'notes': item.notes,
                            'status': item.status,
                            'prep_time': item.menu_item.prep_time_min,
                            'station': self._get_item_station(item.menu_item),
                            'started_at': item.started_at.isoformat() if item.started_at else None,
                            'ready_at': item.ready_at.isoformat() if item.ready_at else None
                        }
                        order_data['items'].append(item_data)
                
                if order_data['items']:
                    kitchen_queue.append(order_data)
            
            return {
                'success': True,
                'queue': kitchen_queue,
                'station_id': station_id,
                'timestamp': datetime.now().isoformat(),
                'total_orders': len(kitchen_queue)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to get kitchen queue'
            }
    
    def bump_item(self, item_id: int, station_id: int, staff_id: int) -> Dict[str, Any]:
        """Mark item as completed (bump from screen)"""
        try:
            item = self.db.query(OrderItem).filter(OrderItem.id == item_id).first()
            if not item:
                return {'success': False, 'message': 'Order item not found'}
            
            if item.status == 'completed':
                return {'success': False, 'message': 'Item already completed'}
            
            # Update item status
            item.status = 'completed'
            item.ready_at = datetime.now()
            item.prepared_by = staff_id
            
            # Update station performance
            self._update_station_performance(station_id, staff_id, item)
            
            # Check if all items in order are completed
            order = self.db.query(Order).filter(Order.id == item.order_id).first()
            self._check_order_completion(order)
            
            self.db.commit()
            
            return {
                'success': True,
                'item_id': item_id,
                'order_id': item.order_id,
                'completed_at': item.ready_at.isoformat(),
                'message': 'Item successfully bumped'
            }
            
        except Exception as e:
            self.db.rollback()
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to bump item'
            }
    
    def start_item_preparation(self, item_id: int, station_id: int, staff_id: int) -> Dict[str, Any]:
        """Start preparing an item"""
        try:
            item = self.db.query(OrderItem).filter(OrderItem.id == item_id).first()
            if not item:
                return {'success': False, 'message': 'Order item not found'}
            
            if item.status != 'pending':
                return {'success': False, 'message': f'Item already {item.status}'}
            
            # Update item status
            item.status = 'preparing'
            item.started_at = datetime.now()
            item.prepared_by = staff_id
            
            # Update order status if first item
            order = self.db.query(Order).filter(Order.id == item.order_id).first()
            if order.status == 'new':
                order.status = 'preparing'
                order.preparation_started_at = datetime.now()
            
            # Calculate estimated completion
            prep_time = item.menu_item.prep_time_min or 15
            item.estimated_completion = datetime.now() + timedelta(minutes=prep_time)
            
            self.db.commit()
            
            return {
                'success': True,
                'item_id': item_id,
                'order_id': item.order_id,
                'started_at': item.started_at.isoformat(),
                'estimated_completion': item.estimated_completion.isoformat(),
                'prep_time_minutes': prep_time,
                'message': 'Item preparation started'
            }
            
        except Exception as e:
            self.db.rollback()
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to start item preparation'
            }
    
    def get_station_performance(self, station_id: int, date_from: datetime, date_to: datetime) -> Dict[str, Any]:
        """Get comprehensive station performance metrics"""
        try:
            # Get station info
            station = self.db.query(KitchenStation).filter(KitchenStation.id == station_id).first()
            if not station:
                return {'success': False, 'message': 'Station not found'}
            
            # Get completed items for this station
            completed_items = self.db.query(OrderItem).join(Order).filter(
                OrderItem.ready_at.between(date_from, date_to),
                OrderItem.status == 'completed',
                Order.created_at.between(date_from, date_to)
            ).all()
            
            # Filter items by station type
            station_items = []
            for item in completed_items:
                if self._get_item_station(item.menu_item) == station.station_type:
                    station_items.append(item)
            
            # Calculate metrics
            total_items = len(station_items)
            if total_items == 0:
                return {
                    'success': True,
                    'station': station.name,
                    'period': {'from': date_from.isoformat(), 'to': date_to.isoformat()},
                    'metrics': {
                        'total_items': 0,
                        'avg_prep_time': 0,
                        'items_per_hour': 0,
                        'on_time_percentage': 100
                    }
                }
            
            # Calculate preparation times
            prep_times = []
            on_time_count = 0
            
            for item in station_items:
                if item.started_at and item.ready_at:
                    prep_time = (item.ready_at - item.started_at).total_seconds() / 60
                    prep_times.append(prep_time)
                    
                    # Check if on time (within estimated time + 5 minutes)
                    if item.estimated_completion:
                        if item.ready_at <= item.estimated_completion + timedelta(minutes=5):
                            on_time_count += 1
            
            avg_prep_time = sum(prep_times) / len(prep_times) if prep_times else 0
            on_time_percentage = (on_time_count / total_items) * 100 if total_items > 0 else 100
            
            # Calculate items per hour
            hours_period = (date_to - date_from).total_seconds() / 3600
            items_per_hour = total_items / hours_period if hours_period > 0 else 0
            
            # Get top performers
            staff_performance = defaultdict(lambda: {'count': 0, 'time': 0})
            for item in station_items:
                if item.prepared_by and item.started_at and item.ready_at:
                    staff = item.prepared_by
                    staff_performance[staff]['count'] += 1
                    staff_performance[staff]['time'] += (item.ready_at - item.started_at).total_seconds() / 60
            
            top_performers = []
            for staff_id, data in staff_performance.items():
                staff_user = self.db.query(User).filter(User.id == staff_id).first()
                if staff_user:
                    avg_time = data['time'] / data['count'] if data['count'] > 0 else 0
                    top_performers.append({
                        'staff_id': staff_id,
                        'staff_name': staff_user.full_name,
                        'items_completed': data['count'],
                        'avg_prep_time': avg_time
                    })
            
            top_performers.sort(key=lambda x: x['items_completed'], reverse=True)
            
            return {
                'success': True,
                'station': station.name,
                'station_type': station.station_type,
                'period': {'from': date_from.isoformat(), 'to': date_to.isoformat()},
                'metrics': {
                    'total_items': total_items,
                    'avg_prep_time': round(avg_prep_time, 2),
                    'items_per_hour': round(items_per_hour, 2),
                    'on_time_percentage': round(on_time_percentage, 2)
                },
                'top_performers': top_performers[:5]
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to get station performance'
            }
    
    def get_bump_screen_data(self, station_id: int) -> Dict[str, Any]:
        """Get data for bump screen display"""
        try:
            # Get recently completed items
            recent_items = self.db.query(OrderItem).join(Order).join(MenuItem).filter(
                OrderItem.status == 'completed',
                OrderItem.ready_at >= datetime.now() - timedelta(minutes=30)
            ).order_by(OrderItem.ready_at.desc()).limit(20).all()
            
            # Filter by station
            station = self.db.query(KitchenStation).filter(KitchenStation.id == station_id).first()
            if station:
                station_items = []
                for item in recent_items:
                    if self._get_item_station(item.menu_item) == station.station_type:
                        station_items.append(item)
            else:
                station_items = recent_items
            
            # Format for bump screen
            bump_data = []
            for item in station_items:
                order = self.db.query(Order).filter(Order.id == item.order_id).first()
                bump_data.append({
                    'item_id': item.id,
                    'order_id': item.order_id,
                    'table_number': order.table.number if order and order.table else None,
                    'menu_item_name': item.menu_item.name,
                    'quantity': item.quantity,
                    'completed_at': item.ready_at.isoformat(),
                    'prep_time_minutes': int((item.ready_at - item.started_at).total_seconds() / 60) if item.started_at else 0,
                    'prepared_by': item.prepared_by
                })
            
            return {
                'success': True,
                'station_id': station_id,
                'bump_items': bump_data,
                'timestamp': datetime.now().isoformat(),
                'total_items': len(bump_data)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to get bump screen data'
            }
    
    def _get_item_station(self, menu_item: MenuItem) -> str:
        """Determine which station should handle this item"""
        # This could be enhanced with category mapping
        if menu_item.category_id:
            category = self.db.query(MenuItem).filter(MenuItem.id == menu_item.category_id).first()
            if category:
                # Map categories to stations
                category_station_map = {
                    1: 'hot_food',  # Ana yeməklər
                    2: 'hot_food',  # Şorbalar
                    3: 'cold_food', # Salatlar
                    4: 'beverages', # İçkilər
                    5: 'cold_food'  # Desertlər
                }
                return category_station_map.get(menu_item.category_id, 'hot_food')
        return 'hot_food'
    
    def _update_station_performance(self, station_id: int, staff_id: int, item: OrderItem):
        """Update station performance metrics"""
        # This could update a separate performance tracking table
        pass
    
    def _check_order_completion(self, order: Order):
        """Check if all items in order are completed"""
        if not order:
            return
        
        active_items = self.db.query(OrderItem).filter(
            OrderItem.order_id == order.id,
            OrderItem.status.in_(['pending', 'preparing'])
        ).count()
        
        if active_items == 0:
            order.status = 'ready'
            order.ready_at = datetime.now()
            
            # Update table status
            if order.table:
                order.table.status = 'ready'
    
    def get_kitchen_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive kitchen dashboard data"""
        try:
            # Get all stations
            stations = self.db.query(KitchenStation).filter(KitchenStation.is_active == True).all()
            
            dashboard_data = {
                'stations': [],
                'summary': {
                    'total_orders': 0,
                    'total_items': 0,
                    'overdue_items': 0,
                    'staff_working': 0
                },
                'timestamp': datetime.now().isoformat()
            }
            
            for station in stations:
                # Get station queue
                queue_result = self.get_kitchen_queue(station.id)
                station_data = {
                    'id': station.id,
                    'name': station.name,
                    'type': station.station_type,
                    'queue_count': 0,
                    'overdue_count': 0,
                    'staff_count': 0
                }
                
                if queue_result['success']:
                    station_data['queue_count'] = len(queue_result['queue'])
                    
                    # Count overdue items
                    now = datetime.now()
                    for order in queue_result['queue']:
                        for item in order['items']:
                            if item['estimated_completion'] and item['estimated_completion'] < now:
                                station_data['overdue_count'] += 1
                            dashboard_data['summary']['total_items'] += 1
                
                dashboard_data['stations'].append(station_data)
                dashboard_data['summary']['total_orders'] += station_data['queue_count']
                dashboard_data['summary']['overdue_items'] += station_data['overdue_count']
            
            return {
                'success': True,
                'dashboard': dashboard_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to get kitchen dashboard'
            }
