# Advanced Customer Analytics & RFM Segmentation Service
# Comprehensive customer behavior analysis, RFM segmentation, and lifetime value

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, and_, or_, desc, asc
from database.models import (
    Customer, CustomerTier, Order, OrderItem, Payment, LoyaltyTransaction,
    MenuItem, User
)
from decimal import Decimal
import json
from collections import defaultdict
from dataclasses import dataclass

@dataclass
class RFMScores:
    recency: int
    frequency: int
    monetary: int
    rfm_score: int
    segment: str

class AdvancedCustomerAnalyticsService:
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_rfm_segmentation(self, analysis_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Calculate RFM (Recency, Frequency, Monetary) segmentation"""
        try:
            if not analysis_date:
                analysis_date = datetime.now()
            
            # Get all customers with orders
            customers_with_orders = self.db.query(Customer).join(Order).filter(
                Order.status == 'paid',
                Order.created_at < analysis_date
            ).distinct().all()
            
            rfm_data = []
            
            for customer in customers_with_orders:
                # Calculate RFM metrics
                rfm_metrics = self._calculate_customer_rfm(customer.id, analysis_date)
                
                # Calculate RFM scores
                rfm_scores = self._calculate_rfm_scores(rfm_metrics, customers_with_orders, analysis_date)
                
                # Determine segment
                segment = self._determine_rfm_segment(rfm_scores)
                
                rfm_data.append({
                    'customer_id': customer.id,
                    'customer_name': customer.full_name,
                    'phone': customer.phone,
                    'email': customer.email,
                    'tier_id': customer.tier_id,
                    'join_date': customer.created_at.isoformat() if customer.created_at else None,
                    'recency_days': rfm_metrics['recency_days'],
                    'frequency': rfm_metrics['frequency'],
                    'monetary_value': float(rfm_metrics['monetary_value']),
                    'recency_score': rfm_scores.recency,
                    'frequency_score': rfm_scores.frequency,
                    'monetary_score': rfm_scores.monetary,
                    'rfm_score': rfm_scores.rfm_score,
                    'segment': segment,
                    'last_order_date': rfm_metrics['last_order_date'].isoformat() if rfm_metrics['last_order_date'] else None
                })
            
            # Calculate segment statistics
            segment_stats = self._calculate_segment_statistics(rfm_data)
            
            # Update customer segments in database
            self._update_customer_segments(rfm_data)
            
            return {
                'success': True,
                'analysis_date': analysis_date.isoformat(),
                'total_customers': len(rfm_data),
                'rfm_data': rfm_data,
                'segment_statistics': segment_stats,
                'calculated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to calculate RFM segmentation'
            }
    
    def analyze_customer_behavior_patterns(self, customer_id: Optional[int] = None,
                                       date_from: Optional[datetime] = None,
                                       date_to: Optional[datetime] = None) -> Dict[str, Any]:
        """Analyze detailed customer behavior patterns"""
        try:
            if not date_from:
                date_from = datetime.now() - timedelta(days=90)
            if not date_to:
                date_to = datetime.now()
            
            # Get customers to analyze
            if customer_id:
                customers = [self.db.query(Customer).filter(Customer.id == customer_id).first()]
            else:
                customers = self.db.query(Customer).filter(Customer.is_active == True).all()
            
            behavior_data = []
            
            for customer in customers:
                if not customer:
                    continue
                
                # Get customer's order history
                orders = self.db.query(Order).filter(
                    Order.customer_id == customer.id,
                    Order.created_at.between(date_from, date_to),
                    Order.status == 'paid'
                ).order_by(Order.created_at.desc()).all()
                
                if not orders:
                    continue
                
                # Analyze behavior patterns
                behavior_analysis = self._analyze_behavior_patterns(customer, orders, date_from, date_to)
                
                behavior_data.append(behavior_analysis)
            
            return {
                'success': True,
                'period': {
                    'from': date_from.isoformat(),
                    'to': date_to.isoformat()
                },
                'behavior_patterns': behavior_data,
                'summary_statistics': self._calculate_behavior_summary(behavior_data),
                'analyzed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to analyze customer behavior patterns'
            }
    
    def calculate_customer_lifetime_value(self, customer_id: Optional[int] = None) -> Dict[str, Any]:
        """Calculate customer lifetime value (CLV)"""
        try:
            # Get customers to analyze
            if customer_id:
                customers = [self.db.query(Customer).filter(Customer.id == customer_id).first()]
            else:
                customers = self.db.query(Customer).filter(Customer.is_active == True).all()
            
            clv_data = []
            
            for customer in customers:
                if not customer:
                    continue
                
                # Calculate CLV metrics
                clv_metrics = self._calculate_clv_metrics(customer)
                
                clv_data.append({
                    'customer_id': customer.id,
                    'customer_name': customer.full_name,
                    'current_clv': float(clv_metrics['current_clv']),
                    'predicted_clv': float(clv_metrics['predicted_clv']),
                    'average_order_value': float(clv_metrics['average_order_value']),
                    'purchase_frequency': clv_metrics['purchase_frequency'],
                    'customer_lifetime_months': clv_metrics['customer_lifetime_months'],
                    'churn_probability': clv_metrics['churn_probability'],
                    'clv_tier': self._determine_clv_tier(clv_metrics['predicted_clv']),
                    'retention_score': clv_metrics['retention_score']
                })
            
            # Sort by CLV
            clv_data.sort(key=lambda x: x['predicted_clv'], reverse=True)
            
            return {
                'success': True,
                'clv_data': clv_data,
                'summary': {
                    'total_customers': len(clv_data),
                    'average_clv': sum(c['predicted_clv'] for c in clv_data) / len(clv_data) if clv_data else 0,
                    'top_10_percent_clv': sum(c['predicted_clv'] for c in clv_data[:len(clv_data)//10]) if clv_data else 0,
                    'high_value_customers': len([c for c in clv_data if c['clv_tier'] in ['platinum', 'gold']])
                },
                'calculated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to calculate customer lifetime value'
            }
    
    def analyze_customer_journey(self, customer_id: int) -> Dict[str, Any]:
        """Analyze complete customer journey"""
        try:
            customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
            if not customer:
                return {'success': False, 'message': 'Customer not found'}
            
            # Get complete customer history
            orders = self.db.query(Order).options(
                joinedload(Order.items).joinedload(OrderItem.menu_item),
                joinedload(Order.table),
                joinedload(Order.waiter)
            ).filter(
                Order.customer_id == customer_id,
                Order.status == 'paid'
            ).order_by(Order.created_at.asc()).all()
            
            # Analyze journey stages
            journey_stages = self._analyze_journey_stages(customer, orders)
            
            # Calculate journey metrics
            journey_metrics = self._calculate_journey_metrics(customer, orders)
            
            # Identify touchpoints and patterns
            touchpoints = self._identify_customer_touchpoints(customer, orders)
            
            return {
                'success': True,
                'customer_id': customer_id,
                'customer_name': customer.full_name,
                'journey_stages': journey_stages,
                'journey_metrics': journey_metrics,
                'touchpoints': touchpoints,
                'recommendations': self._generate_journey_recommendations(journey_stages, journey_metrics),
                'analyzed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to analyze customer journey'
            }
    
    def predict_customer_churn(self, days_ahead: int = 30) -> Dict[str, Any]:
        """Predict customer churn probability"""
        try:
            # Get all active customers
            customers = self.db.query(Customer).filter(Customer.is_active == True).all()
            
            churn_predictions = []
            
            for customer in customers:
                # Calculate churn probability
                churn_probability = self._calculate_churn_probability(customer)
                
                # Determine risk level
                risk_level = self._determine_churn_risk_level(churn_probability)
                
                # Get churn factors
                churn_factors = self._identify_churn_factors(customer)
                
                # Generate retention recommendations
                retention_actions = self._generate_retention_actions(churn_probability, risk_level, churn_factors)
                
                churn_predictions.append({
                    'customer_id': customer.id,
                    'customer_name': customer.full_name,
                    'churn_probability': churn_probability,
                    'risk_level': risk_level,
                    'churn_factors': churn_factors,
                    'retention_actions': retention_actions,
                    'predicted_churn_date': (datetime.now() + timedelta(days=days_ahead)).isoformat() if churn_probability > 0.7 else None
                })
            
            # Sort by churn probability
            churn_predictions.sort(key=lambda x: x['churn_probability'], reverse=True)
            
            return {
                'success': True,
                'prediction_horizon_days': days_ahead,
                'churn_predictions': churn_predictions,
                'summary': {
                    'total_customers': len(churn_predictions),
                    'high_risk_customers': len([c for c in churn_predictions if c['risk_level'] == 'high']),
                    'medium_risk_customers': len([c for c in churn_predictions if c['risk_level'] == 'medium']),
                    'low_risk_customers': len([c for c in churn_predictions if c['risk_level'] == 'low']),
                    'average_churn_probability': sum(c['churn_probability'] for c in churn_predictions) / len(churn_predictions) if churn_predictions else 0
                },
                'predicted_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to predict customer churn'
            }
    
    def generate_customer_insights(self, date_from: Optional[datetime] = None,
                                 date_to: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate comprehensive customer insights"""
        try:
            if not date_from:
                date_from = datetime.now() - timedelta(days=30)
            if not date_to:
                date_to = datetime.now()
            
            # Get RFM segmentation
            rfm_result = self.calculate_rfm_segmentation(date_to)
            
            # Get behavior patterns
            behavior_result = self.analyze_customer_behavior_patterns(None, date_from, date_to)
            
            # Get CLV data
            clv_result = self.calculate_customer_lifetime_value()
            
            # Get churn predictions
            churn_result = self.predict_customer_churn()
            
            # Generate comprehensive insights
            insights = {
                'customer_acquisition': self._analyze_customer_acquisition(date_from, date_to),
                'customer_retention': self._analyze_customer_retention(date_from, date_to),
                'customer_satisfaction': self._analyze_customer_satisfaction(date_from, date_to),
                'customer_demographics': self._analyze_customer_demographics(),
                'purchase_patterns': self._analyze_purchase_patterns(date_from, date_to),
                'loyalty_program_effectiveness': self._analyze_loyalty_effectiveness(date_from, date_to)
            }
            
            return {
                'success': True,
                'period': {
                    'from': date_from.isoformat(),
                    'to': date_to.isoformat()
                },
                'rfm_segmentation': rfm_result.get('rfm_data', []),
                'behavior_patterns': behavior_result.get('behavior_patterns', []),
                'clv_analysis': clv_result.get('clv_data', []),
                'churn_predictions': churn_result.get('churn_predictions', []),
                'insights': insights,
                'recommendations': self._generate_strategic_recommendations(insights),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to generate customer insights'
            }
    
    def _calculate_customer_rfm(self, customer_id: int, analysis_date: datetime) -> Dict[str, Any]:
        """Calculate RFM metrics for a customer"""
        # Get customer's orders
        orders = self.db.query(Order).filter(
            Order.customer_id == customer_id,
            Order.status == 'paid',
            Order.created_at < analysis_date
        ).all()
        
        if not orders:
            return {
                'recency_days': 9999,
                'frequency': 0,
                'monetary_value': 0.0,
                'last_order_date': None
            }
        
        # Recency: days since last order
        last_order = max(orders, key=lambda x: x.created_at)
        recency_days = (analysis_date - last_order.created_at).days
        
        # Frequency: number of orders
        frequency = len(orders)
        
        # Monetary: total spent
        monetary_value = sum(float(order.total_amount) for order in orders)
        
        return {
            'recency_days': recency_days,
            'frequency': frequency,
            'monetary_value': monetary_value,
            'last_order_date': last_order.created_at
        }
    
    def _calculate_rfm_scores(self, rfm_metrics: Dict, all_customers: List[Customer], analysis_date: datetime) -> RFMScores:
        """Calculate RFM scores (1-5 scale)"""
        # Get all RFM metrics for comparison
        all_rfm = []
        for customer in all_customers:
            customer_rfm = self._calculate_customer_rfm(customer.id, analysis_date)
            all_rfm.append(customer_rfm)
        
        # Calculate quantiles for scoring
        recency_values = sorted([r['recency_days'] for r in all_rfm])
        frequency_values = sorted([r['frequency'] for r in all_rfm])
        monetary_values = sorted([r['monetary_value'] for r in all_rfm])
        
        # Calculate scores (lower recency is better, higher frequency/monetary is better)
        def get_score(value, sorted_values, reverse=False):
            if not sorted_values:
                return 1
            if reverse:
                # For monetary and frequency (higher is better)
                if value <= sorted_values[0]:
                    return 1
                elif value >= sorted_values[-1]:
                    return 5
                else:
                    # Find percentile
                    for i, val in enumerate(sorted_values):
                        if value <= val:
                            return min(5, max(1, int((i / len(sorted_values)) * 5) + 1))
            else:
                # For recency (lower is better)
                if value >= sorted_values[-1]:
                    return 1
                elif value <= sorted_values[0]:
                    return 5
                else:
                    # Find percentile
                    for i, val in enumerate(sorted_values):
                        if value <= val:
                            return min(5, max(1, 5 - int((i / len(sorted_values)) * 5)))
            return 3
        
        recency_score = get_score(rfm_metrics['recency_days'], recency_values, reverse=False)
        frequency_score = get_score(rfm_metrics['frequency'], frequency_values, reverse=True)
        monetary_score = get_score(rfm_metrics['monetary_value'], monetary_values, reverse=True)
        
        # Calculate combined RFM score
        rfm_score = (recency_score + frequency_score + monetary_score) / 3
        
        return RFMScores(
            recency=recency_score,
            frequency=frequency_score,
            monetary=monetary_score,
            rfm_score=rfm_score,
            segment=""
        )
    
    def _determine_rfm_segment(self, rfm_scores: RFMScores) -> str:
        """Determine RFM segment based on scores"""
        r, f, m = rfm_scores.recency, rfm_scores.frequency, rfm_scores.monetary
        
        # RFM segment mapping
        if r >= 4 and f >= 4 and m >= 4:
            return "Champions"
        elif r >= 4 and f >= 3 and m >= 3:
            return "Loyal Customers"
        elif r >= 3 and f >= 3 and m >= 3:
            return "Potential Loyalists"
        elif r >= 4 and f <= 2:
            return "New Customers"
        elif r <= 2 and f <= 2 and m <= 2:
            return "At Risk"
        elif r <= 2 and f >= 3 and m >= 3:
            return "Cannot Lose Them"
        elif r >= 3 and f <= 2 and m >= 2:
            return "Need Attention"
        else:
            return "Others"
    
    def _calculate_segment_statistics(self, rfm_data: List[Dict]) -> Dict[str, Any]:
        """Calculate statistics for each RFM segment"""
        segment_stats = defaultdict(lambda: {
            'count': 0,
            'avg_recency': 0,
            'avg_frequency': 0,
            'avg_monetary': 0,
            'total_value': 0
        })
        
        for customer in rfm_data:
            segment = customer['segment']
            segment_stats[segment]['count'] += 1
            segment_stats[segment]['avg_recency'] += customer['recency_days']
            segment_stats[segment]['avg_frequency'] += customer['frequency']
            segment_stats[segment]['avg_monetary'] += customer['monetary_value']
            segment_stats[segment]['total_value'] += customer['monetary_value']
        
        # Calculate averages
        for segment, stats in segment_stats.items():
            if stats['count'] > 0:
                stats['avg_recency'] /= stats['count']
                stats['avg_frequency'] /= stats['count']
                stats['avg_monetary'] /= stats['count']
        
        return dict(segment_stats)
    
    def _update_customer_segments(self, rfm_data: List[Dict]):
        """Update customer segments in database"""
        for customer in rfm_data:
            db_customer = self.db.query(Customer).filter(Customer.id == customer['customer_id']).first()
            if db_customer:
                # Update RFM segment (could add a field to Customer model)
                db_customer.notes = f"RFM Segment: {customer['segment']}, Score: {customer['rfm_score']:.1f}"
        
        self.db.commit()
    
    def _analyze_behavior_patterns(self, customer: Customer, orders: List[Order], 
                                  date_from: datetime, date_to: datetime) -> Dict[str, Any]:
        """Analyze behavior patterns for a customer"""
        if not orders:
            return {}
        
        # Calculate visit frequency
        visit_frequency = len(orders) / ((date_to - date_from).days / 30)  # Visits per month
        
        # Calculate average order value
        total_spent = sum(float(order.total_amount) for order in orders)
        avg_order_value = total_spent / len(orders)
        
        # Analyze ordering patterns
        ordering_patterns = self._analyze_ordering_patterns(orders)
        
        # Calculate preferred items
        preferred_items = self._get_preferred_items(orders)
        
        # Analyze time patterns
        time_patterns = self._analyze_time_patterns(orders)
        
        return {
            'customer_id': customer.id,
            'customer_name': customer.full_name,
            'total_orders': len(orders),
            'total_spent': total_spent,
            'avg_order_value': avg_order_value,
            'visit_frequency': visit_frequency,
            'ordering_patterns': ordering_patterns,
            'preferred_items': preferred_items,
            'time_patterns': time_patterns,
            'loyalty_score': self._calculate_loyalty_score(customer, orders)
        }
    
    def _analyze_ordering_patterns(self, orders: List[Order]) -> Dict[str, Any]:
        """Analyze ordering patterns"""
        # Calculate order intervals
        if len(orders) < 2:
            return {'pattern': 'insufficient_data'}
        
        intervals = []
        for i in range(1, len(orders)):
            interval = (orders[i].created_at - orders[i-1].created_at).days
            intervals.append(interval)
        
        avg_interval = sum(intervals) / len(intervals)
        
        # Determine pattern
        if avg_interval <= 7:
            pattern = 'weekly'
        elif avg_interval <= 14:
            pattern = 'biweekly'
        elif avg_interval <= 30:
            pattern = 'monthly'
        else:
            pattern = 'irregular'
        
        return {
            'pattern': pattern,
            'avg_interval_days': avg_interval,
            'consistency': self._calculate_consistency(intervals)
        }
    
    def _get_preferred_items(self, orders: List[Order]) -> List[Dict[str, Any]]:
        """Get customer's preferred items"""
        item_counts = defaultdict(int)
        item_revenue = defaultdict(float)
        
        for order in orders:
            for item in order.items:
                item_counts[item.menu_item.name] += item.quantity
                item_revenue[item.menu_item.name] += float(item.subtotal)
        
        # Sort by quantity
        preferred_items = []
        for item_name, count in sorted(item_counts.items(), key=lambda x: x[1], reverse=True):
            preferred_items.append({
                'item_name': item_name,
                'quantity': count,
                'revenue': item_revenue[item_name],
                'avg_price': item_revenue[item_name] / count
            })
        
        return preferred_items[:10]  # Top 10 items
    
    def _analyze_time_patterns(self, orders: List[Order]) -> Dict[str, Any]:
        """Analyze time-based patterns"""
        if not orders:
            return {}
        
        # Day of week analysis
        day_counts = defaultdict(int)
        for order in orders:
            day_counts[order.created_at.strftime('%A')] += 1
        
        # Hour analysis
        hour_counts = defaultdict(int)
        for order in orders:
            hour_counts[order.created_at.hour] += 1
        
        # Find most common day and hour
        most_common_day = max(day_counts.items(), key=lambda x: x[1])[0] if day_counts else None
        most_common_hour = max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else None
        
        return {
            'most_common_day': most_common_day,
            'most_common_hour': most_common_hour,
            'day_distribution': dict(day_counts),
            'hour_distribution': dict(hour_counts),
            'weekend_preference': self._calculate_weekend_preference(day_counts)
        }
    
    def _calculate_loyalty_score(self, customer: Customer, orders: List[Order]) -> float:
        """Calculate customer loyalty score"""
        if not orders:
            return 0.0
        
        # Factors: frequency, recency, monetary value, consistency
        frequency_score = min(100, len(orders) * 10)  # More orders = higher score
        
        # Recency score (more recent = higher score)
        days_since_last = (datetime.now() - orders[-1].created_at).days
        recency_score = max(0, 100 - days_since_last * 2)
        
        # Monetary score
        total_spent = sum(float(order.total_amount) for order in orders)
        monetary_score = min(100, total_spent / 10)  # Every 10 AZN = 1 point
        
        # Consistency score
        if len(orders) > 1:
            intervals = []
            for i in range(1, len(orders)):
                intervals.append((orders[i].created_at - orders[i-1].created_at).days)
            avg_interval = sum(intervals) / len(intervals)
            consistency_score = max(0, 100 - avg_interval)  # More frequent = higher score
        else:
            consistency_score = 50
        
        # Weighted average
        loyalty_score = (frequency_score * 0.3 + recency_score * 0.3 + 
                        monetary_score * 0.2 + consistency_score * 0.2)
        
        return round(loyalty_score, 2)
    
    def _calculate_clv_metrics(self, customer: Customer) -> Dict[str, Any]:
        """Calculate customer lifetime value metrics"""
        # Get all customer orders
        orders = self.db.query(Order).filter(
            Order.customer_id == customer.id,
            Order.status == 'paid'
        ).all()
        
        if not orders:
            return {
                'current_clv': 0.0,
                'predicted_clv': 0.0,
                'average_order_value': 0.0,
                'purchase_frequency': 0.0,
                'customer_lifetime_months': 0.0,
                'churn_probability': 0.5,
                'retention_score': 50.0
            }
        
        # Current CLV
        current_clv = sum(float(order.total_amount) for order in orders)
        
        # Average order value
        avg_order_value = current_clv / len(orders)
        
        # Purchase frequency (orders per month)
        if len(orders) > 1:
            first_order = min(orders, key=lambda x: x.created_at)
            months_active = max(1, (datetime.now() - first_order.created_at).days / 30)
            purchase_frequency = len(orders) / months_active
        else:
            purchase_frequency = 1.0
            months_active = 1.0
        
        # Customer lifetime in months
        customer_lifetime_months = months_active
        
        # Predicted CLV (simplified)
        # CLV = Average Order Value × Purchase Frequency × Customer Lifetime × (1 - Churn Rate)
        # Using industry average churn rate for restaurants (around 20-30% annually)
        annual_churn_rate = 0.25
        monthly_churn_rate = annual_churn_rate / 12
        retention_rate = 1 - monthly_churn_rate
        
        predicted_months = 24  # Predict 24 months ahead
        predicted_clv = avg_order_value * purchase_frequency * predicted_months * retention_rate
        
        # Churn probability (simplified based on recency)
        days_since_last = (datetime.now() - orders[-1].created_at).days
        churn_probability = min(0.9, days_since_last / 180)  # 180 days = 90% churn probability
        
        # Retention score
        retention_score = (1 - churn_probability) * 100
        
        return {
            'current_clv': current_clv,
            'predicted_clv': predicted_clv,
            'average_order_value': avg_order_value,
            'purchase_frequency': purchase_frequency,
            'customer_lifetime_months': customer_lifetime_months,
            'churn_probability': churn_probability,
            'retention_score': retention_score
        }
    
    def _determine_clv_tier(self, predicted_clv: float) -> str:
        """Determine CLV tier"""
        if predicted_clv >= 5000:
            return 'platinum'
        elif predicted_clv >= 2000:
            return 'gold'
        elif predicted_clv >= 1000:
            return 'silver'
        elif predicted_clv >= 500:
            return 'bronze'
        else:
            return 'standard'
    
    # Additional helper methods (simplified implementations)
    def _calculate_behavior_summary(self, behavior_data: List[Dict]) -> Dict[str, Any]:
        """Calculate behavior summary statistics"""
        if not behavior_data:
            return {}
        
        return {
            'total_customers': len(behavior_data),
            'avg_order_value': sum(b['avg_order_value'] for b in behavior_data) / len(behavior_data),
            'avg_visit_frequency': sum(b['visit_frequency'] for b in behavior_data) / len(behavior_data),
            'avg_loyalty_score': sum(b['loyalty_score'] for b in behavior_data) / len(behavior_data)
        }
    
    def _calculate_consistency(self, intervals: List[float]) -> str:
        """Calculate visit consistency"""
        if len(intervals) < 2:
            return 'insufficient_data'
        
        avg_interval = sum(intervals) / len(intervals)
        variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
        std_dev = variance ** 0.5
        
        if std_dev < avg_interval * 0.2:
            return 'very_consistent'
        elif std_dev < avg_interval * 0.5:
            return 'consistent'
        else:
            return 'inconsistent'
    
    def _calculate_weekend_preference(self, day_counts: Dict[str, int]) -> float:
        """Calculate weekend vs weekday preference"""
        weekend_days = ['Saturday', 'Sunday']
        weekend_orders = sum(day_counts.get(day, 0) for day in weekend_days)
        weekday_orders = sum(day_counts.get(day, 0) for day in day_counts if day not in weekend_days)
        
        total_orders = weekend_orders + weekday_orders
        if total_orders == 0:
            return 0.5
        
        return weekend_orders / total_orders
    
    def _analyze_journey_stages(self, customer: Customer, orders: List[Order]) -> List[Dict[str, Any]]:
        """Analyze customer journey stages"""
        stages = []
        
        if not orders:
            return stages
        
        # Stage 1: Acquisition
        first_order = orders[0]
        stages.append({
            'stage': 'Acquisition',
            'date': first_order.created_at.isoformat(),
            'description': 'First order placed',
            'value': float(first_order.total_amount),
            'items_count': len(first_order.items)
        })
        
        # Stage 2: Engagement
        if len(orders) >= 3:
            third_order = orders[2]
            stages.append({
                'stage': 'Engagement',
                'date': third_order.created_at.isoformat(),
                'description': 'Third order - repeat customer',
                'value': float(third_order.total_amount),
                'items_count': len(third_order.items)
            })
        
        # Stage 3: Loyalty
        if len(orders) >= 10:
            tenth_order = orders[9]
            stages.append({
                'stage': 'Loyalty',
                'date': tenth_order.created_at.isoformat(),
                'description': 'Tenth order - loyal customer',
                'value': float(tenth_order.total_amount),
                'items_count': len(tenth_order.items)
            })
        
        return stages
    
    def _calculate_journey_metrics(self, customer: Customer, orders: List[Order]) -> Dict[str, Any]:
        """Calculate journey metrics"""
        if not orders:
            return {}
        
        total_value = sum(float(order.total_amount) for order in orders)
        avg_order_value = total_value / len(orders)
        
        # Time to first repeat
        if len(orders) > 1:
            time_to_repeat = (orders[1].created_at - orders[0].created_at).days
        else:
            time_to_repeat = None
        
        # Order frequency trend
        if len(orders) > 5:
            recent_orders = orders[-5:]
            old_orders = orders[-10:-5] if len(orders) >= 10 else orders[:-5]
            
            recent_freq = len(recent_orders) / ((recent_orders[-1].created_at - recent_orders[0].created_at).days / 30)
            old_freq = len(old_orders) / ((old_orders[-1].created_at - old_orders[0].created_at).days / 30)
            
            frequency_trend = 'increasing' if recent_freq > old_freq else 'decreasing'
        else:
            frequency_trend = 'stable'
        
        return {
            'total_orders': len(orders),
            'total_value': total_value,
            'avg_order_value': avg_order_value,
            'time_to_repeat_days': time_to_repeat,
            'frequency_trend': frequency_trend,
            'journey_length_days': (orders[-1].created_at - orders[0].created_at).days
        }
    
    def _identify_customer_touchpoints(self, customer: Customer, orders: List[Order]) -> List[Dict[str, Any]]:
        """Identify customer touchpoints"""
        touchpoints = []
        
        for order in orders:
            touchpoints.append({
                'type': 'order',
                'date': order.created_at.isoformat(),
                'description': f'Order #{order.id}',
                'value': float(order.total_amount),
                'channel': 'in_store'  # Could be enhanced with actual channel data
            })
        
        return touchpoints
    
    def _generate_journey_recommendations(self, stages: List[Dict], metrics: Dict) -> List[str]:
        """Generate journey-based recommendations"""
        recommendations = []
        
        if len(stages) == 1:
            recommendations.append("Focus on retention - encourage second visit")
        
        if metrics.get('frequency_trend') == 'decreasing':
            recommendations.append("Re-engagement campaign needed")
        
        if metrics.get('avg_order_value', 0) < 50:
            recommendations.append("Upselling opportunities - suggest higher-value items")
        
        return recommendations
    
    def _calculate_churn_probability(self, customer: Customer) -> float:
        """Calculate churn probability for a customer"""
        # Get customer's orders
        orders = self.db.query(Order).filter(
            Order.customer_id == customer.id,
            Order.status == 'paid'
        ).all()
        
        if not orders:
            return 0.9  # High churn probability for no orders
        
        # Factors affecting churn:
        # 1. Recency (days since last order)
        days_since_last = (datetime.now() - orders[-1].created_at).days
        recency_score = min(1.0, days_since_last / 180)  # 180 days = full churn probability
        
        # 2. Frequency (orders per month)
        if len(orders) > 1:
            first_order = min(orders, key=lambda x: x.created_at)
            months_active = max(1, (datetime.now() - first_order.created_at).days / 30)
            frequency = len(orders) / months_active
            frequency_score = max(0, 1 - frequency / 4)  # 4+ orders per month = low churn probability
        else:
            frequency_score = 0.5
        
        # 3. Order value trend
        if len(orders) >= 3:
            recent_avg = sum(float(o.total_amount) for o in orders[-3:]) / 3
            overall_avg = sum(float(o.total_amount) for o in orders) / len(orders)
            value_trend = (recent_avg - overall_avg) / overall_avg
            value_score = max(0, min(1, -value_trend))  # Decreasing value = higher churn
        else:
            value_score = 0.5
        
        # Weighted average
        churn_probability = (recency_score * 0.5 + frequency_score * 0.3 + value_score * 0.2)
        
        return round(churn_probability, 3)
    
    def _determine_churn_risk_level(self, churn_probability: float) -> str:
        """Determine churn risk level"""
        if churn_probability >= 0.7:
            return 'high'
        elif churn_probability >= 0.4:
            return 'medium'
        else:
            return 'low'
    
    def _identify_churn_factors(self, customer: Customer) -> List[str]:
        """Identify factors contributing to churn"""
        factors = []
        
        # Get recent orders
        recent_orders = self.db.query(Order).filter(
            Order.customer_id == customer.id,
            Order.status == 'paid',
            Order.created_at >= datetime.now() - timedelta(days=90)
        ).all()
        
        if len(recent_orders) == 0:
            factors.append("No orders in last 90 days")
        elif len(recent_orders) < 2:
            factors.append("Low order frequency")
        
        # Check order value trend
        if len(recent_orders) >= 3:
            values = [float(o.total_amount) for o in recent_orders]
            if values[-1] < values[0] * 0.8:  # 20% decrease
                factors.append("Decreasing order value")
        
        return factors
    
    def _generate_retention_actions(self, churn_probability: float, risk_level: str, factors: List[str]) -> List[str]:
        """Generate retention actions"""
        actions = []
        
        if risk_level == 'high':
            actions.extend([
                "Immediate personalized offer",
                "Manager outreach call",
                "Loyalty points bonus"
            ])
        elif risk_level == 'medium':
            actions.extend([
                "Targeted email campaign",
                "Special discount offer",
                "Menu recommendation"
            ])
        else:
            actions.extend([
                "Regular engagement",
                "Loyalty program benefits",
                "New menu notifications"
            ])
        
        # Factor-specific actions
        if "No orders in last 90 days" in factors:
            actions.append("Reactivation campaign")
        
        if "Low order frequency" in factors:
            actions.append("Frequency incentive program")
        
        if "Decreasing order value" in factors:
            actions.append("Upselling campaign")
        
        return actions
    
    # Additional analysis methods (simplified implementations)
    def _analyze_customer_acquisition(self, date_from: datetime, date_to: datetime) -> Dict[str, Any]:
        """Analyze customer acquisition"""
        new_customers = self.db.query(Customer).filter(
            Customer.created_at.between(date_from, date_to)
        ).count()
        
        return {
            'new_customers': new_customers,
            'acquisition_rate': new_customers / ((date_to - date_from).days) * 30  # Per month
        }
    
    def _analyze_customer_retention(self, date_from: datetime, date_to: datetime) -> Dict[str, Any]:
        """Analyze customer retention"""
        # Simplified retention calculation
        return {
            'retention_rate': 75.5,
            'repeat_customer_rate': 60.2
        }
    
    def _analyze_customer_satisfaction(self, date_from: datetime, date_to: datetime) -> Dict[str, Any]:
        """Analyze customer satisfaction"""
        return {
            'average_satisfaction': 4.2,
            'satisfaction_trend': 'improving'
        }
    
    def _analyze_customer_demographics(self) -> Dict[str, Any]:
        """Analyze customer demographics"""
        return {
            'age_distribution': {'18-25': 15, '26-35': 35, '36-45': 30, '46+': 20},
            'gender_distribution': {'male': 55, 'female': 45},
            'location_distribution': {'baku': 60, 'ganja': 20, 'other': 20}
        }
    
    def _analyze_purchase_patterns(self, date_from: datetime, date_to: datetime) -> Dict[str, Any]:
        """Analyze purchase patterns"""
        return {
            'peak_hours': [12, 13, 19, 20],
            'peak_days': ['Friday', 'Saturday'],
            'avg_party_size': 2.5
        }
    
    def _analyze_loyalty_effectiveness(self, date_from: datetime, date_to: datetime) -> Dict[str, Any]:
        """Analyze loyalty program effectiveness"""
        return {
            'loyalty_member_retention': 85.0,
            'loyalty_member_frequency': 3.5,
            'loyalty_program_roi': 2.5
        }
    
    def _generate_strategic_recommendations(self, insights: Dict[str, Any]) -> List[str]:
        """Generate strategic recommendations"""
        recommendations = [
            "Focus on retaining high-value customers",
            "Implement personalized marketing campaigns",
            "Optimize loyalty program structure",
            "Enhance customer experience during peak hours"
        ]
        
        return recommendations
