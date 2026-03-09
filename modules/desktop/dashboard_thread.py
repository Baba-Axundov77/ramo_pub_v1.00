# modules/desktop/dashboard_thread.py — Background Dashboard Data Fetcher
from __future__ import annotations
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from typing import Dict, Any, Optional
import logging
from modules.desktop.api_client import DesktopAPIClient

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
        self.refresh_interval = 30000  # 30 seconds
        self.current_data = {}
        
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
                        self.current_data = result
                        self.data_received.emit(result)
                        
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
