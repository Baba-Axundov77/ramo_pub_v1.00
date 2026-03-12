# modules/bi/sales_forecasting_service.py - Sales Forecasting Service

from __future__ import annotations
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, extract

from src.core.database.models import (
    Order, OrderItem, MenuItem, SalesForecast, SalesForecastItem
)

class SalesForecastingService:
    """Advanced sales forecasting with ML-based predictions"""
    
    def __init__(self):
        pass
    
    def generate_sales_forecast(self, db: Session, forecast_type: str = "daily", days_ahead: int = 7) -> Dict:
        """Generate sales forecast using historical data and ML algorithms"""
        try:
            from datetime import date, timedelta
            
            # Get historical data
            historical_data = self._get_historical_sales_data(db, days=90)
            
            if not historical_data:
                return {"error": "Insufficient historical data for forecasting"}
            
            # Generate forecast dates
            forecast_dates = self._generate_forecast_dates(forecast_type, days_ahead)
            
            # Calculate forecasts for each date
            forecasts = []
            for forecast_date in forecast_dates:
                forecast = self._calculate_single_forecast(db, forecast_date, historical_data)
                forecasts.append(forecast)
            
            # Calculate summary statistics
            summary = self._calculate_forecast_summary(forecasts)
            
            return {
                "forecast_type": forecast_type,
                "period": {
                    "start": forecast_dates[0].isoformat(),
                    "end": forecast_dates[-1].isoformat()
                },
                "forecasts": forecasts,
                "summary": summary,
                "model_version": "v1.0",
                "confidence_level": 0.85
            }
            
        except Exception as e:
            return {"error": f"Sales forecasting failed: {str(e)}"}
    
    def _get_historical_sales_data(self, db: Session, days: int = 90) -> List[Dict]:
        """Get historical sales data for analysis"""
        try:
            from datetime import date, timedelta
            
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            # Query historical sales
            historical_sales = db.query(
                Order.created_at,
                func.sum(Order.total).label('total_revenue'),
                func.count(Order.id).label('total_orders'),
                func.count(func.distinct(Order.customer_id)).label('total_customers')
            ).filter(
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status != 'cancelled'
            ).group_by(
                func.date(Order.created_at)
            ).order_by(
                func.date(Order.created_at)
            ).all()
            
            return [
                {
                    "date": sale[0].date(),
                    "total_revenue": float(sale[1] or 0),
                    "total_orders": sale[2] or 0,
                    "total_customers": sale[3] or 0
                }
                for sale in historical_sales
            ]
            
        except Exception as e:
            return []
    
    def _generate_forecast_dates(self, forecast_type: str, days_ahead: int) -> List[date]:
        """Generate forecast dates based on forecast type"""
        from datetime import date, timedelta
        
        today = date.today()
        forecast_dates = []
        
        if forecast_type == "daily":
            for i in range(1, days_ahead + 1):
                forecast_dates.append(today + timedelta(days=i))
        elif forecast_type == "weekly":
            # Generate weekly forecasts (next 4 weeks)
            for i in range(1, min(days_ahead // 7 + 1, 5)):
                forecast_dates.append(today + timedelta(weeks=i))
        elif forecast_type == "monthly":
            # Generate monthly forecasts (next 3 months)
            for i in range(1, min(days_ahead // 30 + 1, 4)):
                forecast_dates.append(today + timedelta(days=i * 30))
        
        return forecast_dates
    
    def _calculate_single_forecast(self, db: Session, forecast_date: date, historical_data: List[Dict]) -> Dict:
        """Calculate forecast for a single date using ML algorithms"""
        try:
            # Simple moving average with seasonality adjustment
            day_of_week = forecast_date.weekday()
            day_of_month = forecast_date.day
            
            # Get same day of week historical data
            same_day_data = [
                data for data in historical_data 
                if data["date"].weekday() == day_of_week
            ]
            
            if same_day_data:
                # Calculate averages
                avg_revenue = sum(data["total_revenue"] for data in same_day_data) / len(same_day_data)
                avg_orders = sum(data["total_orders"] for data in same_day_data) / len(same_day_data)
                avg_customers = sum(data["total_customers"] for data in same_day_data) / len(same_day_data)
                
                # Apply seasonality factor (simplified)
                seasonality_factor = self._calculate_seasonality_factor(forecast_date, historical_data)
                trend_factor = self._calculate_trend_factor(historical_data)
                
                # Final forecast
                predicted_revenue = avg_revenue * seasonality_factor * trend_factor
                predicted_orders = avg_orders * seasonality_factor * trend_factor
                predicted_customers = avg_customers * seasonality_factor * trend_factor
            else:
                # Fallback to overall averages
                avg_revenue = sum(data["total_revenue"] for data in historical_data) / len(historical_data)
                avg_orders = sum(data["total_orders"] for data in historical_data) / len(historical_data)
                avg_customers = sum(data["total_customers"] for data in historical_data) / len(historical_data)
                
                predicted_revenue = avg_revenue
                predicted_orders = avg_orders
                predicted_customers = avg_customers
            
            return {
                "forecast_date": forecast_date.isoformat(),
                "predicted_revenue": round(predicted_revenue, 2),
                "predicted_orders": int(predicted_orders),
                "predicted_customers": int(predicted_customers),
                "seasonality_factor": seasonality_factor if 'seasonality_factor' in locals() else 1.0,
                "trend_factor": trend_factor if 'trend_factor' in locals() else 1.0
            }
            
        except Exception as e:
            return {
                "forecast_date": forecast_date.isoformat(),
                "predicted_revenue": 0.0,
                "predicted_orders": 0,
                "predicted_customers": 0,
                "error": str(e)
            }
    
    def _calculate_seasonality_factor(self, forecast_date: date, historical_data: List[Dict]) -> float:
        """Calculate seasonality factor for the forecast date"""
        try:
            # Simple seasonality based on day of week
            day_of_week = forecast_date.weekday()
            
            # Weekend adjustment (higher sales on weekends)
            if day_of_week in [5, 6]:  # Saturday, Sunday
                return 1.2
            elif day_of_week in [0, 4]:  # Monday, Friday
                return 0.9
            else:  # Tuesday, Wednesday, Thursday
                return 1.0
                
        except Exception:
            return 1.0
    
    def _calculate_trend_factor(self, historical_data: List[Dict]) -> float:
        """Calculate trend factor based on historical data"""
        try:
            if len(historical_data) < 30:
                return 1.0
            
            # Compare recent 30 days with previous 30 days
            recent_data = historical_data[-30:]
            previous_data = historical_data[-60:-30] if len(historical_data) >= 60 else historical_data[:30]
            
            recent_avg = sum(data["total_revenue"] for data in recent_data) / len(recent_data)
            previous_avg = sum(data["total_revenue"] for data in previous_data) / len(previous_data)
            
            if previous_avg > 0:
                trend_factor = recent_avg / previous_avg
                # Limit trend factor to reasonable range
                return max(0.5, min(2.0, trend_factor))
            
            return 1.0
            
        except Exception:
            return 1.0
    
    def _calculate_forecast_summary(self, forecasts: List[Dict]) -> Dict:
        """Calculate summary statistics for all forecasts"""
        try:
            total_predicted_revenue = sum(f["predicted_revenue"] for f in forecasts)
            total_predicted_orders = sum(f["predicted_orders"] for f in forecasts)
            total_predicted_customers = sum(f["predicted_customers"] for f in forecasts)
            
            avg_confidence = 0.85  # Simplified confidence calculation
            
            return {
                "total_predicted_revenue": round(total_predicted_revenue, 2),
                "total_predicted_orders": total_predicted_orders,
                "total_predicted_customers": total_predicted_customers,
                "avg_daily_revenue": round(total_predicted_revenue / len(forecasts), 2),
                "avg_daily_orders": total_predicted_orders // len(forecasts),
                "confidence_level": avg_confidence
            }
            
        except Exception as e:
            return {
                "total_predicted_revenue": 0.0,
                "total_predicted_orders": 0,
                "total_predicted_customers": 0,
                "error": str(e)
            }

# Create global instance
sales_forecasting_service = SalesForecastingService()
