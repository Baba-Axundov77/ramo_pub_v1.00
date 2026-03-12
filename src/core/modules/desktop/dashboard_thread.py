# modules/desktop/dashboard_thread.py — Background Dashboard Data Fetcher
from __future__ import annotations
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from typing import Dict, Any, Optional
import logging
from src.core.modules.desktop.api_client import DesktopAPIClient

logger = logging.getLogger(__name__)

class DashboardDataThread(QThread):
    """Background thread for fetching dashboard data"""
    
    # Signals
    data_received = pyqtSignal(dict)  # Successfully received data
    error_occurred = pyqtSignal(str)    # Error message
    connection_lost = pyqtSignal()       # Connection lost
    connection_restored = pyqtSignal()     # Connection restored
    
    def __init__(self, api_client: DesktopAPIClient):
        super().__init__()
        self.api_client = api_client
        self.is_running = False
        self.auto_refresh = True
        self.refresh_interval = 2000  # 2 seconds as recommended
        self.current_data = {}
        self.last_data_hash = None  # Track data changes to avoid unnecessary updates
        
    def _data_hash(self, data: dict) -> str:
        """Generate hash of data to detect changes"""
        import json
        try:
            # Create a simplified version for comparison
            simplified = {
                'tables': data.get('tables', {}),
                'orders': data.get('orders', {}),
                'revenue': data.get('revenue', {})
            }
            return json.dumps(simplified, sort_keys=True)
        except:
            return str(hash(str(data)))
        
    def run(self):
        """Main thread loop"""
        self.is_running = True
        logger.info("Dashboard data thread started")
        
        while self.is_running:
            try:
                if self.auto_refresh:
                    # Fetch dashboard overview
                    result = self.api_client.get_dashboard_overview()
                    
                    if result.get('success'):
                        # Check if data actually changed
                        current_hash = self._data_hash(result)
                        if current_hash != self.last_data_hash:
                            self.current_data = result
                            self.last_data_hash = current_hash
                            self.data_received.emit(result)
                            logger.debug("Dashboard data updated - changes detected")
                            
                            # Reset no-change counter on activity
                            if hasattr(self, 'no_change_count'):
                                self.no_change_count = 0
                            else:
                                self.no_change_count = 0
                        else:
                            # Increment no-change counter
                            if hasattr(self, 'no_change_count'):
                                self.no_change_count += 1
                            else:
                                self.no_change_count = 1
                            logger.debug(f"Dashboard data unchanged - skipping update (count: {self.no_change_count})")
                        
                        # Adjust refresh interval based on activity
                        self._adjust_refresh_interval()
                        
                        # Emit connection restored if we were disconnected
                        if not hasattr(self, '_was_connected'):
                            self._was_connected = True
                            self.connection_restored.emit()
                    else:
                        error_msg = result.get('message', 'Unknown error')
                        self.error_occurred.emit(error_msg)
                        
                        # Check if it's a connection error
                        if result.get('error_code') in ['CONNECTION_ERROR', 'SESSION_EXPIRED']:
                            if hasattr(self, '_was_connected') and self._was_connected:
                                self.connection_lost.emit()
                                self._was_connected = False
                
                # Sleep for refresh interval
                self.msleep(self.refresh_interval)
                
            except Exception as e:
                logger.error(f"Dashboard thread error: {str(e)}")
                self.error_occurred.emit(f"Thread error: {str(e)}")
                self.msleep(5000)  # Wait 5 seconds before retry
    
    def stop(self):
        """Stop the thread"""
        self.is_running = False
        logger.info("Dashboard data thread stopped")
    
    def set_refresh_interval(self, interval_ms: int):
        """Update refresh interval"""
        self.refresh_interval = interval_ms
        logger.info(f"Dashboard refresh interval set to {interval_ms}ms")
    
    def set_adaptive_refresh(self, enabled: bool = True):
        """Enable adaptive refresh based on activity"""
        self.adaptive_refresh = enabled
        self.activity_counter = 0
        logger.info(f"Dashboard adaptive refresh {'enabled' if enabled else 'disabled'}")
    
    def _adjust_refresh_interval(self):
        """Adjust refresh interval based on recent activity"""
        if not hasattr(self, 'adaptive_refresh') or not self.adaptive_refresh:
            return
            
        # If no data changes for 10 consecutive cycles, increase interval
        if hasattr(self, 'no_change_count'):
            if self.no_change_count >= 10:
                self.refresh_interval = min(10000, self.refresh_interval + 1000)  # Max 10 seconds
                logger.debug(f"Increased refresh interval to {self.refresh_interval}ms due to inactivity")
                self.no_change_count = 0
            else:
                # Reset on activity
                self.refresh_interval = 2000  # Back to normal 2 seconds
        else:
            self.no_change_count = 0
    
    def set_auto_refresh(self, enabled: bool):
        """Enable/disable auto refresh"""
        self.auto_refresh = enabled
        logger.info(f"Dashboard auto refresh {'enabled' if enabled else 'disabled'}")
    
    def manual_refresh(self):
        """Trigger immediate refresh"""
        if self.isRunning():
            try:
                result = self.api_client.get_dashboard_overview()
                if result.get('success'):
                    self.current_data = result
                    self.data_received.emit(result)
                else:
                    self.error_occurred.emit(result.get('message', 'Refresh failed'))
            except Exception as e:
                self.error_occurred.emit(f"Manual refresh error: {str(e)}")

class MetricsUpdateThread(QThread):
    """Background thread for specific metrics updates"""
    
    # Signals
    metrics_updated = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, api_client: DesktopAPIClient):
        super().__init__()
        self.api_client = api_client
        self.is_running = False
        
    def run(self):
        """Update specific metrics"""
        self.is_running = True
        
        while self.is_running:
            try:
                # Fetch different metrics
                metrics = {}
                
                # System metrics
                system_result = self.api_client.get_system_metrics()
                if system_result.get('success'):
                    metrics['system'] = system_result.get('metrics', {})
                
                # Revenue data
                revenue_result = self.api_client.get_revenue_data(days=1)
                if revenue_result.get('success'):
                    metrics['revenue'] = revenue_result.get('data', {})
                
                # Critical inventory
                inventory_result = self.api_client.get_critical_inventory()
                if inventory_result.get('success'):
                    metrics['inventory'] = inventory_result.get('data', {})
                
                # Table occupancy
                occupancy_result = self.api_client.get_table_occupancy()
                if occupancy_result.get('success'):
                    metrics['occupancy'] = occupancy_result.get('data', {})
                
                if metrics:
                    self.metrics_updated.emit(metrics)
                
                # Update every 60 seconds
                self.msleep(60000)
                
            except Exception as e:
                logger.error(f"Metrics update thread error: {str(e)}")
                self.error_occurred.emit(f"Metrics error: {str(e)}")
                self.msleep(10000)  # Wait 10 seconds before retry
    
    def stop(self):
        """Stop the thread"""
        self.is_running = False
