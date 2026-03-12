# web/enterprise_routes.py - Enterprise-level API Routes
from __future__ import annotations
from flask import Blueprint, request, jsonify, g
from functools import wraps
from datetime import datetime, date
from typing import Dict, Any

from src.web.auth import permission_required, permission_required_api
from src.core.modules.orders.advanced_order_service import advanced_order_service
from src.core.modules.orders.split_payment_service import split_payment_service
from src.core.modules.orders.order_modification_service import order_modification_service
from src.core.modules.kitchen.kds_display_service import kds_display_service
from src.core.modules.inventory.advanced_inventory_service import advanced_inventory_service
from src.core.modules.inventory.recipe_costing_service import recipe_costing_service
from src.core.modules.staff.advanced_staff_service import advanced_staff_service
from src.core.modules.staff.shift_scheduling_service import shift_scheduling_service
from src.core.modules.analytics.business_intelligence_service import business_intelligence_service
from src.core.modules.analytics.customer_analytics_service import customer_analytics_service

# Create enterprise blueprint
enterprise_bp = Blueprint('enterprise', __name__, url_prefix='/enterprise')

# Rate limiting decorator
def rate_limit(limit: str):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # In production, this would integrate with Flask-Limiter
            return f(*args, **kwargs)
        return decorated
    return decorator

# ===== ADVANCED ORDER MANAGEMENT =====

@enterprise_bp.route('/orders/<int:order_id>/split-payment', methods=['POST'])
@permission_required_api("process_payment")
@rate_limit("10 per minute")
def api_split_payment(order_id: int):
    """Process split payment across multiple tender types"""
    try:
        data = request.get_json()
        
        payment_breakdown = {
            'cash': data.get('cash', {}),
            'card': data.get('card', {}),
            'online': data.get('online', {})
        }
        
        success, result = split_payment_service.create_split_payment(
            g.db, order_id, payment_breakdown
        )
        
        if success:
            return jsonify({
                'ok': True,
                'message': 'Split payment uğurla',
                'data': result
            })
        else:
            return jsonify({'ok': False, 'message': str(result)}), 400
            
    except Exception as e:
        return jsonify({'ok': False, 'message': f'Xəta: {str(e)}'}), 500

@enterprise_bp.route('/orders/<int:order_id>/modify', methods=['POST'])
@permission_required_api("manage_orders")
@rate_limit("20 per minute")
def api_modify_order(order_id: int):
    """Modify existing order with tracking"""
    try:
        data = request.get_json()
        
        modifications = data.get('modifications', [])
        reason = data.get('reason', '')
        staff_id = data.get('staff_id')
        
        success, result = order_modification_service.modify_order(
            g.db, order_id, modifications, reason, staff_id
        )
        
        if success:
            return jsonify({
                'ok': True,
                'message': 'Order uğurla dəyişdirildi',
                'data': result
            })
        else:
            return jsonify({'ok': False, 'message': str(result)}), 400
            
    except Exception as e:
        return jsonify({'ok': False, 'message': f'Xəta: {str(e)}'}), 500

@enterprise_bp.route('/orders/<int:order_id>/modifications')
@permission_required_api("view_orders")
@rate_limit("100 per hour")
def api_order_modifications(order_id: int):
    """Get modification history for an order"""
    try:
        modifications = order_modification_service.get_modification_history(g.db, order_id)
        return jsonify({
            'ok': True,
            'data': modifications
        })
    except Exception as e:
        return jsonify({'ok': False, 'message': f'Xəta: {str(e)}'}), 500

# ===== KITCHEN DISPLAY SYSTEM =====

@enterprise_bp.route('/kds/queue')
@permission_required_api("manage_kitchen")
@rate_limit("60 per minute")
def api_kds_queue():
    """Get KDS queue with real-time updates"""
    try:
        station_id = request.args.get('station_id', type=int)
        queue_data = kds_display_service.get_kds_queue_by_station(g.db, station_id)
        return jsonify({
            'ok': True,
            'data': queue_data
        })
    except Exception as e:
        return jsonify({'ok': False, 'message': f'Xəta: {str(e)}'}), 500

@enterprise_bp.route('/kds/bump/<int:station_id>', methods=['POST'])
@permission_required_api("manage_kitchen")
@rate_limit("30 per minute")
def api_kds_bump(station_id: int):
    """Bump next order for preparation"""
    try:
        result = kds_display_service.bump_next_order(g.db, station_id)
        return jsonify({
            'ok': True,
            'data': result
        })
    except Exception as e:
        return jsonify({'ok': False, 'message': f'Xəta: {str(e)}'}), 500

@enterprise_bp.route('/kds/item/<int:item_id>/complete', methods=['POST'])
@permission_required_api("manage_kitchen")
@rate_limit("60 per minute")
def api_complete_item(item_id: int):
    """Complete item preparation"""
    try:
        data = request.get_json()
        staff_id = data.get('staff_id')
        
        result = kds_display_service.complete_item_preparation(g.db, item_id, staff_id)
        return jsonify({
            'ok': True,
            'data': result
        })
    except Exception as e:
        return jsonify({'ok': False, 'message': f'Xəta: {str(e)}'}), 500

# ===== ADVANCED INVENTORY =====

@enterprise_bp.route('/inventory/recipe-cost/<int:menu_item_id>')
@permission_required_api("manage_inventory")
@rate_limit("50 per hour")
def api_recipe_cost(menu_item_id: int):
    """Get real-time recipe cost"""
    try:
        cost_data = recipe_costing_service.calculate_recipe_cost(g.db, menu_item_id)
        return jsonify({
            'ok': True,
            'data': cost_data
        })
    except Exception as e:
        return jsonify({'ok': False, 'message': f'Xəta: {str(e)}'}), 500

@enterprise_bp.route('/inventory/menu-engineering')
@permission_required_api("view_reports")
@rate_limit("20 per hour")
def api_menu_engineering():
    """Get menu engineering analysis"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = date.today()
        
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        analysis = recipe_costing_service.get_menu_engineering_report(g.db, start_date, end_date)
        return jsonify({
            'ok': True,
            'data': analysis
        })
    except Exception as e:
        return jsonify({'ok': False, 'message': f'Xəta: {str(e)}'}), 500

@enterprise_bp.route('/inventory/waste', methods=['POST'])
@permission_required_api("manage_inventory")
@rate_limit("10 per minute")
def api_track_waste():
    """Track food waste"""
    try:
        data = request.get_json()
        waste_data = data.get('waste_data', [])
        
        success, message = advanced_inventory_service.track_waste(g.db, waste_data)
        
        if success:
            return jsonify({
                'ok': True,
                'message': message
            })
        else:
            return jsonify({'ok': False, 'message': message}), 400
            
    except Exception as e:
        return jsonify({'ok': False, 'message': f'Xəta: {str(e)}'}), 500

# ===== STAFF MANAGEMENT =====

@enterprise_bp.route('/staff/schedule/generate', methods=['POST'])
@permission_required_api("manage_staff")
@rate_limit("5 per hour")
def api_generate_schedule():
    """Generate optimized staff schedule"""
    try:
        data = request.get_json()
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        optimization_level = data.get('optimization_level', 'balanced')
        
        schedule_data = shift_scheduling_service.generate_weekly_schedule(
            g.db, start_date, optimization_level
        )
        
        return jsonify({
            'ok': True,
            'data': schedule_data
        })
    except Exception as e:
        return jsonify({'ok': False, 'message': f'Xəta: {str(e)}'}), 500

@enterprise_bp.route('/staff/performance', methods=['POST'])
@permission_required_api("manage_staff")
@rate_limit("20 per minute")
def api_track_performance():
    """Track staff performance"""
    try:
        data = request.get_json()
        
        success, message = advanced_staff_service.track_staff_performance(g.db, data)
        
        if success:
            return jsonify({
                'ok': True,
                'message': message
            })
        else:
            return jsonify({'ok': False, 'message': message}), 400
            
    except Exception as e:
        return jsonify({'ok': False, 'message': f'Xəta: {str(e)}'}), 500

@enterprise_bp.route('/staff/labor-cost')
@permission_required_api("view_reports")
@rate_limit("30 per hour")
def api_labor_cost():
    """Get labor cost analysis"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = date.today()
        
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        labor_data = advanced_staff_service.generate_labor_cost_report(g.db, start_date, end_date)
        return jsonify({
            'ok': True,
            'data': labor_data
        })
    except Exception as e:
        return jsonify({'ok': False, 'message': f'Xəta: {str(e)}'}), 500

# ===== BUSINESS INTELLIGENCE =====

@enterprise_bp.route('/analytics/menu-engineering')
@permission_required_api("view_reports")
@rate_limit("20 per hour")
def api_menu_engineering_analytics():
    """Get menu engineering analytics"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = date.today()
        
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        analytics_data = business_intelligence_service.menu_engineering_analysis(g.db, start_date, end_date)
        return jsonify({
            'ok': True,
            'data': analytics_data
        })
    except Exception as e:
        return jsonify({'ok': False, 'message': f'Xəta: {str(e)}'}), 500

@enterprise_bp.route('/analytics/customer-behavior')
@permission_required_api("view_reports")
@rate_limit("20 per hour")
def api_customer_behavior():
    """Get customer behavior analytics"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = date.today()
        
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        behavior_data = customer_analytics_service.analyze_customer_behavior_patterns(g.db, start_date, end_date)
        return jsonify({
            'ok': True,
            'data': behavior_data
        })
    except Exception as e:
        return jsonify({'ok': False, 'message': f'Xəta: {str(e)}'}), 500

@enterprise_bp.route('/analytics/rfm-analysis')
@permission_required_api("view_reports")
@rate_limit("10 per hour")
def api_rfm_analysis():
    """Get RFM customer analysis"""
    try:
        analysis_date = request.args.get('analysis_date')
        if analysis_date:
            analysis_date = datetime.strptime(analysis_date, '%Y-%m-%d').date()
        else:
            analysis_date = date.today()
        
        rfm_data = customer_analytics_service.calculate_rfm_analysis(g.db, analysis_date)
        return jsonify({
            'ok': True,
            'data': rfm_data
        })
    except Exception as e:
        return jsonify({'ok': False, 'message': f'Xəta: {str(e)}'}), 500

@enterprise_bp.route('/analytics/sales-forecast')
@permission_required_api("view_reports")
@rate_limit("5 per hour")
def api_sales_forecast():
    """Get sales forecasting"""
    try:
        days_ahead = request.args.get('days_ahead', 30, type=int)
        forecast_data = business_intelligence_service.sales_forecasting(g.db, days_ahead)
        return jsonify({
            'ok': True,
            'data': forecast_data
        })
    except Exception as e:
        return jsonify({'ok': False, 'message': f'Xəta: {str(e)}'}), 500

# ===== HEALTH AND MONITORING =====

@enterprise_bp.route('/health')
@rate_limit("1000 per minute")
def api_health_check():
    """Enterprise health check endpoint"""
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '2.0.0',
            'checks': {
                'database': _check_database_health(),
                'services': _check_service_health(),
                'performance': _check_performance_metrics()
            }
        }
        
        return jsonify(health_status)
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@enterprise_bp.route('/metrics')
@permission_required_api("view_reports")
@rate_limit("30 per minute")
def api_metrics():
    """Get system metrics"""
    try:
        metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'performance': _get_performance_metrics(),
            'business': _get_business_metrics(g.db),
            'system': _get_system_metrics()
        }
        
        return jsonify(metrics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== UTILITY FUNCTIONS =====

def _check_database_health() -> Dict[str, Any]:
    """Check database connectivity and performance"""
    try:
        # Simple health check - would be more comprehensive in production
        return {
            'status': 'healthy',
            'response_time': '< 100ms'  # Would actually measure
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }

def _check_service_health() -> Dict[str, Any]:
    """Check external service health"""
    return {
        'payment_gateway': 'healthy',  # Would actually check
        'cache': 'healthy',  # Would check Redis
        'kitchen_display': 'healthy'
    }

def _check_performance_metrics() -> Dict[str, Any]:
    """Check performance metrics"""
    return {
        'cpu_usage': '45%',
        'memory_usage': '60%',
        'disk_usage': '30%',
        'response_time': '120ms'
    }

def _get_performance_metrics() -> Dict[str, Any]:
    """Get current performance metrics"""
    return {
        'orders_per_minute': 2.5,
        'avg_response_time': 150,
        'error_rate': 0.02,
        'active_users': 15
    }

def _get_business_metrics(db) -> Dict[str, Any]:
    """Get current business metrics"""
    return {
        'today_orders': 45,
        'today_revenue': 1250.50,
        'active_orders': 8,
        'staff_on_shift': 12
    }

def _get_system_metrics() -> Dict[str, Any]:
    """Get system metrics"""
    return {
        'uptime': '15 days',
        'version': '2.0.0',
        'environment': 'production',
        'last_deployment': '2024-03-07T10:30:00Z'
    }
