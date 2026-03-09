# modules/analytics/dashboard_service.py — Real-time Dashboard Analytics
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import text, func, and_, or_
from database.connection import get_db
from database.models import Order, OrderItem, MenuItem, InventoryItem, User, Table, Customer
import logging

logger = logging.getLogger(__name__)

class DashboardService:
    """Real-time dashboard analytics with PostgreSQL integration"""
    
    def __init__(self, db_session=None):
        self.db = db_session or get_db()
    
    def get_today_revenue(self) -> float:
        """Get today's total revenue"""
        try:
            today = datetime.now().date()
            result = self.db.execute(text("""
                SELECT COALESCE(SUM(total), 0) as revenue
                FROM orders 
                WHERE DATE(created_at) = :today 
                AND status = 'paid'
            """), {"today": today}).scalar()
            return float(result) if result else 0.0
        except Exception as e:
            logger.error(f"Error getting today's revenue: {str(e)}")
            return 0.0
    
    def get_today_orders(self) -> int:
        """Get today's order count"""
        try:
            today = datetime.now().date()
            result = self.db.execute(text("""
                SELECT COUNT(*) as count
                FROM orders 
                WHERE DATE(created_at) = :today
            """), {"today": today}).scalar()
            return int(result) if result else 0
        except Exception as e:
            logger.error(f"Error getting today's orders: {str(e)}")
            return 0
    
    def get_active_staff_count(self) -> int:
        """Get currently active staff (simplified - based on recent activity)"""
        try:
            # Active in last 2 hours
            two_hours_ago = datetime.now() - timedelta(hours=2)
            result = self.db.execute(text("""
                SELECT COUNT(DISTINCT waiter_id) as count
                FROM orders 
                WHERE created_at >= :since
                AND waiter_id IS NOT NULL
            """), {"since": two_hours_ago}).scalar()
            return int(result) if result else 0
        except Exception as e:
            logger.error(f"Error getting active staff: {str(e)}")
            return 0
    
    def get_table_occupancy_rate(self) -> float:
        """Get current table occupancy rate"""
        try:
            total_tables = self.db.execute(text("SELECT COUNT(*) FROM tables WHERE is_active = true")).scalar()
            occupied_tables = self.db.execute(text("""
                SELECT COUNT(*) FROM tables 
                WHERE status = 'occupied' AND is_active = true
            """)).scalar()
            
            if total_tables == 0:
                return 0.0
            return round((occupied_tables / total_tables) * 100, 2)
        except Exception as e:
            logger.error(f"Error getting table occupancy: {str(e)}")
            return 0.0
    
    def get_critical_stock_items(self) -> List[Dict[str, Any]]:
        """Get items with critical stock levels"""
        try:
            result = self.db.execute(text("""
                SELECT 
                    id,
                    name,
                    quantity,
                    min_quantity,
                    unit,
                    CASE 
                        WHEN quantity <= 0 THEN 'Out of Stock'
                        WHEN quantity < min_quantity THEN 'Low Stock'
                        ELSE 'OK'
                    END as status
                FROM inventory_items 
                WHERE is_active = true 
                AND quantity <= min_quantity
                ORDER BY quantity ASC
                LIMIT 10
            """)).fetchall()
            
            return [dict(row) for row in result] if result else []
        except Exception as e:
            logger.error(f"Error getting critical stock items: {str(e)}")
            return []
    
    def get_top_selling_items(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get top selling items in the last N days"""
        try:
            since_date = datetime.now() - timedelta(days=days)
            result = self.db.execute(text("""
                SELECT 
                    mi.name,
                    mi.price,
                    SUM(oi.quantity) as total_sold,
                    SUM(oi.quantity * oi.unit_price) as total_revenue
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                JOIN menu_items mi ON oi.menu_item_id = mi.id
                WHERE o.created_at >= :since_date
                AND o.status = 'paid'
                GROUP BY mi.id, mi.name, mi.price
                ORDER BY total_sold DESC
                LIMIT 10
            """), {"since_date": since_date}).fetchall()
            
            return [dict(row) for row in result] if result else []
        except Exception as e:
            logger.error(f"Error getting top selling items: {str(e)}")
            return []
    
    def get_sales_chart_data(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get sales data for chart visualization"""
        try:
            since_date = datetime.now() - timedelta(days=days)
            result = self.db.execute(text("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as order_count,
                    COALESCE(SUM(total_amount), 0) as revenue
                FROM orders 
                WHERE created_at >= :since_date
                AND status = 'paid'
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            """), {"since_date": since_date}).fetchall()
            
            return [dict(row) for row in result] if result else []
        except Exception as e:
            logger.error(f"Error getting sales chart data: {str(e)}")
            return []
    
    def get_hourly_sales_data(self) -> List[Dict[str, Any]]:
        """Get hourly sales data for today"""
        try:
            today = datetime.now().date()
            result = self.db.execute(text("""
                SELECT 
                    EXTRACT(HOUR FROM created_at) as hour,
                    COUNT(*) as order_count,
                    COALESCE(SUM(total_amount), 0) as revenue
                FROM orders 
                WHERE DATE(created_at) = :today
                AND status = 'paid'
                GROUP BY EXTRACT(HOUR FROM created_at)
                ORDER BY hour ASC
            """), {"today": today}).fetchall()
            
            # Fill missing hours with 0 values
            hourly_data = []
            for hour in range(24):
                found = False
                for row in result:
                    if int(row.hour) == hour:
                        hourly_data.append({
                            'hour': hour,
                            'order_count': row.order_count,
                            'revenue': float(row.revenue)
                        })
                        found = True
                        break
                if not found:
                    hourly_data.append({
                        'hour': hour,
                        'order_count': 0,
                        'revenue': 0.0
                    })
            
            return hourly_data
        except Exception as e:
            logger.error(f"Error getting hourly sales data: {str(e)}")
            return []
    
    def get_order_status_breakdown(self) -> Dict[str, int]:
        """Get current order status distribution"""
        try:
            result = self.db.execute(text("""
                SELECT status, COUNT(*) as count
                FROM orders 
                WHERE DATE(created_at) = CURRENT_DATE
                GROUP BY status
            """)).fetchall()
            
            return {row.status: row.count for row in result} if result else {}
        except Exception as e:
            logger.error(f"Error getting order status breakdown: {str(e)}")
            return {}
    
    def get_comprehensive_dashboard(self) -> Dict[str, Any]:
        """Get all dashboard data in a single call"""
        try:
            return {
                'success': True,
                'data': {
                    'revenue': {
                        'today': self.get_today_revenue(),
                        'trend': '+12.5%'  # This would be calculated against previous period
                    },
                    'orders': {
                        'today': self.get_today_orders(),
                        'breakdown': self.get_order_status_breakdown()
                    },
                    'tables': {
                        'occupancy_rate': self.get_table_occupancy_rate(),
                        'total': self.db.execute(text("SELECT COUNT(*) FROM tables WHERE is_active = true")).scalar(),
                        'occupied': self.db.execute(text("SELECT COUNT(*) FROM tables WHERE status = 'occupied' AND is_active = true")).scalar()
                    },
                    'staff': {
                        'active_count': self.get_active_staff_count(),
                        'total': self.db.execute(text("SELECT COUNT(*) FROM users WHERE is_active = true")).scalar()
                    },
                    'inventory': {
                        'critical_items': self.get_critical_stock_items(),
                        'total_items': self.db.execute(text("SELECT COUNT(*) FROM inventory_items WHERE is_active = true")).scalar()
                    },
                    'top_items': self.get_top_selling_items(),
                    'sales_chart': self.get_sales_chart_data(),
                    'hourly_sales': self.get_hourly_sales_data()
                },
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting comprehensive dashboard: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to load dashboard data',
                'error_code': 'DASHBOARD_ERROR'
            }
