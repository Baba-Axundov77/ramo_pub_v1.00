# modules/desktop/api_client.py — Desktop API Client for Web Integration
from __future__ import annotations
import requests
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from src.core.modules.auth.token_manager import token_manager

logger = logging.getLogger(__name__)

class DesktopAPIClient:
    """Enterprise API client for desktop application"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.access_token = None
        self.refresh_token = None
        self.user_data = None
        
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Login and store JWT tokens"""
        try:
            login_data = {
                "username": username,
                "password": password
            }
            
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.access_token = result['data']['access_token']
                    self.refresh_token = result['data']['refresh_token']
                    self.user_data = result['data']['user']
                    
                    # Set authorization header for future requests
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.access_token}',
                        'Content-Type': 'application/json'
                    })
                    
                    logger.info(f"Desktop login successful for user: {username}")
                    return {
                        'success': True,
                        'user': self.user_data,
                        'message': 'Login successful'
                    }
                else:
                    return {
                        'success': False,
                        'message': result.get('message', 'Login failed')
                    }
            else:
                return {
                    'success': False,
                    'message': f'Login failed with status {response.status_code}'
                }
                
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'message': 'Cannot connect to server. Please check your connection.',
                'error_code': 'CONNECTION_ERROR'
            }
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return {
                'success': False,
                'message': 'An unexpected error occurred during login',
                'error_code': 'LOGIN_ERROR'
            }
    
    def refresh_access_token(self) -> bool:
        """Refresh the access token"""
        if not self.refresh_token:
            return False
            
        try:
            refresh_data = {"refresh_token": self.refresh_token}
            response = self.session.post(
                f"{self.base_url}/auth/api/refresh",
                json=refresh_data
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.access_token = result['data']['access_token']
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.access_token}'
                    })
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if client has valid authentication"""
        return self.access_token is not None and self.user_data is not None
    
    def logout(self) -> bool:
        """Logout and clear tokens"""
        try:
            if self.access_token:
                response = self.session.post(f"{self.base_url}/auth/api/logout")
                # Server response doesn't matter much for logout
            
            self.access_token = None
            self.refresh_token = None
            self.user_data = None
            self.session.headers.pop('Authorization', None)
            
            logger.info("Desktop logout successful")
            return True
            
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return False
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated API request with token refresh"""
        if not self.is_authenticated():
            return {
                'success': False,
                'message': 'Not authenticated',
                'error_code': 'NOT_AUTHENTICATED'
            }
        
        try:
            response = self.session.request(
                method,
                f"{self.base_url}{endpoint}",
                **kwargs
            )
            
            # Handle token expiration
            if response.status_code == 401:
                if self.refresh_access_token():
                    # Retry with new token
                    response = self.session.request(
                        method,
                        f"{self.base_url}{endpoint}",
                        **kwargs
                    )
                else:
                    return {
                        'success': False,
                        'message': 'Session expired. Please login again.',
                        'error_code': 'SESSION_EXPIRED'
                    }
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'success': False,
                    'message': f'API request failed with status {response.status_code}',
                    'error_code': 'API_ERROR'
                }
                
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'message': 'Cannot connect to server',
                'error_code': 'CONNECTION_ERROR'
            }
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return {
                'success': False,
                'message': 'An unexpected error occurred',
                'error_code': 'REQUEST_ERROR'
            }
    
    def get_dashboard_overview(self) -> Dict[str, Any]:
        """Get dashboard overview data"""
        return self._make_request('GET', '/api/v2/dashboard/overview')
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system metrics"""
        return self._make_request('GET', '/api/v2/system/metrics')
    
    def get_revenue_data(self, days: int = 7) -> Dict[str, Any]:
        """Get revenue analytics"""
        return self._make_request('GET', f'/api/v2/dashboard/revenue?days={days}')
    
    def get_critical_inventory(self) -> Dict[str, Any]:
        """Get critical stock items"""
        return self._make_request('GET', '/api/v2/dashboard/inventory/critical')
    
    def get_table_occupancy(self) -> Dict[str, Any]:
        """Get table occupancy data"""
        return self._make_request('GET', '/api/v2/dashboard/tables/occupancy')
    
    def get_top_selling_items(self, days: int = 7, limit: int = 10) -> Dict[str, Any]:
        """Get top selling items"""
        return self._make_request('GET', f'/api/v2/dashboard/top-items?days={days}&limit={limit}')
    
    def get_orders_history(self, limit: int = 50) -> Dict[str, Any]:
        """Get orders history"""
        return self._make_request('GET', f'/api/v2/orders/history?limit={limit}')
    
    def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new order"""
        return self._make_request('POST', '/api/v2/orders', json=order_data)
    
    def update_order(self, order_id: int, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing order"""
        return self._make_request('PUT', f'/api/v2/orders/{order_id}', json=order_data)
    
    def get_menu_items(self, category_id: Optional[int] = None) -> Dict[str, Any]:
        """Get menu items"""
        params = {}
        if category_id:
            params['category_id'] = category_id
        return self._make_request('GET', '/api/v2/menu/items', params=params)
    
    def get_tables(self) -> Dict[str, Any]:
        """Get all tables"""
        return self._make_request('GET', '/api/v2/tables')
    
    def update_table_status(self, table_id: int, status: str) -> Dict[str, Any]:
        """Update table status"""
        return self._make_request('PUT', f'/api/v2/tables/{table_id}/status', json={'status': status})
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get current user information"""
        return self.user_data
    
    def check_server_connection(self) -> bool:
        """Check if server is accessible"""
        try:
            response = self.session.get(f"{self.base_url}/api/v2/system/health", timeout=5)
            return response.status_code == 200
        except:
            return False
