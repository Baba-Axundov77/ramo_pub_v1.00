# modules/staff/advanced_staff_service.py - Enterprise Staff Management
from __future__ import annotations
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date, timedelta, time
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_

from src.core.database.models import (
    User, Shift, UserRole, Order, Payment, TipDistribution,
    StaffPerformance, StaffSchedule, LeaveRequest
)

class AdvancedStaffService:
    """Enterprise-level staff management with scheduling and performance tracking"""
    
    def __init__(self):
        pass
    
    def create_shift_schedule(self, db: Session, start_date: date, 
                           end_date: date, template_id: Optional[int] = None) -> Dict:
        """Create optimized shift schedule based on historical data"""
        try:
            # Get historical traffic patterns
            traffic_patterns = self._get_traffic_patterns(db, start_date, end_date)
            
            # Get staff availability
            staff_availability = self._get_staff_availability(db, start_date, end_date)
            
            # Generate schedule
            schedule = []
            current_date = start_date
            
            while current_date <= end_date:
                day_schedule = self._generate_day_schedule(
                    current_date, traffic_patterns, staff_availability
                )
                schedule.extend(day_schedule)
                current_date += timedelta(days=1)
            
            # Save schedule to database
            for shift_data in schedule:
                shift = StaffSchedule(
                    staff_id=shift_data['staff_id'],
                    shift_date=shift_data['date'],
                    start_time=shift_data['start_time'],
                    end_time=shift_data['end_time'],
                    position=shift_data['position'],
                    is_published=True,
                    created_at=datetime.utcnow()
                )
                db.add(shift)
            
            db.commit()
            
            return {
                'schedule': schedule,
                'coverage_analysis': self._analyze_schedule_coverage(schedule, traffic_patterns),
                'labor_cost_estimate': self._estimate_labor_cost(db, schedule)
            }
            
        except Exception as e:
            db.rollback()
            return {'error': str(e)}
    
    def track_staff_performance(self, db: Session, staff_id: int, 
                             performance_data: Dict) -> Tuple[bool, str]:
        """Track detailed staff performance metrics"""
        try:
            # Create or update performance record
            existing = db.query(StaffPerformance).filter(
                StaffPerformance.staff_id == staff_id,
                StaffPerformance.performance_date == performance_data['date']
            ).first()
            
            if existing:
                # Update existing record
                existing.orders_served = performance_data.get('orders_served', existing.orders_served)
                existing.revenue_generated = performance_data.get('revenue_generated', existing.revenue_generated)
                existing.table_turnover = performance_data.get('table_turnover', existing.table_turnover)
                existing.customer_satisfaction = performance_data.get('customer_satisfaction', existing.customer_satisfaction)
                existing.attendance_score = performance_data.get('attendance_score', existing.attendance_score)
                existing.updated_at = datetime.utcnow()
            else:
                # Create new performance record
                performance = StaffPerformance(
                    staff_id=staff_id,
                    performance_date=performance_data['date'],
                    orders_served=performance_data.get('orders_served', 0),
                    revenue_generated=Decimal(str(performance_data.get('revenue_generated', 0))),
                    table_turnover=performance_data.get('table_turnover', 0),
                    customer_satisfaction=performance_data.get('customer_satisfaction', 0),
                    attendance_score=performance_data.get('attendance_score', 100),
                    created_at=datetime.utcnow()
                )
                db.add(performance)
            
            db.commit()
            return True, "Performance data uğurla qeyd edildi"
            
        except Exception as e:
            db.rollback()
            return False, f"Performance tracking xətası: {str(e)}"
    
    def generate_labor_cost_report(self, db: Session, start_date: date, 
                                 end_date: date) -> Dict:
        """Generate comprehensive labor cost analysis"""
        try:
            # Get all shifts in period
            shifts = db.query(StaffSchedule).options(
                joinedload(StaffSchedule.staff)
            ).filter(
                StaffSchedule.shift_date >= start_date,
                StaffSchedule.shift_date <= end_date
            ).all()
            
            # Calculate labor metrics
            total_hours = 0
            total_labor_cost = Decimal('0.00')
            labor_by_role = {}
            labor_by_day = {}
            
            for shift in shifts:
                # Calculate shift duration
                shift_start = datetime.combine(shift.shift_date, shift.start_time)
                shift_end = datetime.combine(shift.shift_date, shift.end_time)
                shift_duration = (shift_end - shift_start).total_seconds() / 3600
                
                total_hours += shift_duration
                
                # Calculate cost (hourly rate would come from staff profile)
                hourly_rate = self._get_hourly_rate(db, shift.staff_id, shift.position)
                shift_cost = Decimal(str(shift_duration * hourly_rate))
                total_labor_cost += shift_cost
                
                # Group by role
                role = shift.position
                labor_by_role[role] = labor_by_role.get(role, {'hours': 0, 'cost': 0})
                labor_by_role[role]['hours'] += shift_duration
                labor_by_role[role]['cost'] += shift_cost
                
                # Group by day
                day = shift.shift_date.strftime('%Y-%m-%d')
                labor_by_day[day] = labor_by_day.get(day, {'hours': 0, 'cost': 0})
                labor_by_day[day]['hours'] += shift_duration
                labor_by_day[day]['cost'] += shift_cost
            
            # Calculate labor cost percentage
            period_revenue = self._get_period_revenue(db, start_date, end_date)
            labor_cost_percentage = (total_labor_cost / period_revenue * 100) if period_revenue > 0 else 0
            
            return {
                'period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'summary': {
                    'total_hours': total_hours,
                    'total_labor_cost': float(total_labor_cost),
                    'period_revenue': float(period_revenue),
                    'labor_cost_percentage': float(labor_cost_percentage),
                    'average_hourly_cost': float(total_labor_cost / total_hours) if total_hours > 0 else 0
                },
                'by_role': labor_by_role,
                'by_day': labor_by_day,
                'efficiency_metrics': self._calculate_labor_efficiency(db, start_date, end_date, total_hours)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def optimize_staffing_levels(self, db: Session, target_date: date) -> Dict:
        """Optimize staffing levels based on predicted demand"""
        try:
            # Get historical data for similar day
            historical_data = self._get_similar_day_data(db, target_date)
            
            # Get current staff availability
            available_staff = self._get_available_staff(db, target_date)
            
            # Calculate optimal staffing
            positions_needed = {
                'waiter': self._calculate_waiters_needed(historical_data),
                'kitchen': self._calculate_kitchen_staff_needed(historical_data),
                'cashier': self._calculate_cashiers_needed(historical_data),
                'manager': 1  # Always need at least one manager
            }
            
            # Generate staffing recommendations
            recommendations = []
            for position, needed_count in positions_needed.items():
                available_for_position = [
                    staff for staff in available_staff 
                    if self._can_work_position(staff, position)
                ]
                
                if len(available_for_position) < needed_count:
                    recommendations.append({
                        'position': position,
                        'needed': needed_count,
                        'available': len(available_for_position),
                        'shortage': needed_count - len(available_for_position),
                        'urgency': 'high' if len(available_for_position) == 0 else 'medium'
                    })
                
                # Assign available staff
                assigned = available_for_position[:needed_count]
                for staff in assigned:
                    recommendations.append({
                        'type': 'assignment',
                        'staff_id': staff.id,
                        'staff_name': staff.full_name,
                        'position': position,
                        'date': target_date
                    })
            
            return {
                'target_date': target_date,
                'positions_needed': positions_needed,
                'recommendations': recommendations,
                'total_available': len(available_staff),
                'coverage_score': self._calculate_coverage_score(positions_needed, available_staff)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def manage_leave_requests(self, db: Session, leave_request: Dict) -> Tuple[bool, str]:
        """Process leave requests with approval workflow"""
        try:
            # Create leave request
            leave = LeaveRequest(
                staff_id=leave_request['staff_id'],
                leave_type=leave_request['leave_type'],  # vacation, sick, personal
                start_date=leave_request['start_date'],
                end_date=leave_request['end_date'],
                reason=leave_request['reason'],
                status='pending',
                requested_at=datetime.utcnow()
            )
            db.add(leave)
            
            # Check for conflicts
            conflicts = self._check_leave_conflicts(db, leave_request)
            if conflicts:
                leave.status = 'conflict'
                leave.conflict_details = conflicts
                db.commit()
                return False, f"Leave conflict: {', '.join(conflicts)}"
            
            # Auto-approve based on rules
            if self._should_auto_approve(leave_request):
                leave.status = 'approved'
                leave.approved_by = 'system'
                leave.approved_at = datetime.utcnow()
                
                # Update schedule to mark unavailable
                self._block_schedule_for_leave(db, leave_request)
            
            db.commit()
            return True, "Leave request processed"
            
        except Exception as e:
            db.rollback()
            return False, f"Leave request xətası: {str(e)}"
    
    def _get_traffic_patterns(self, db: Session, start_date: date, end_date: date) -> Dict:
        """Get historical traffic patterns for scheduling"""
        # This would analyze order patterns, customer counts, etc.
        # Simplified for demo
        return {
            'weekend_multiplier': 1.5,
            'evening_multiplier': 1.3,
            'lunch_peak': 1.4,
            'dinner_peak': 1.6
        }
    
    def _generate_day_schedule(self, date_obj: date, traffic_patterns: Dict, 
                            availability: List) -> List[Dict]:
        """Generate schedule for a specific day"""
        # Simplified schedule generation
        day_of_week = date_obj.strftime('%A')
        is_weekend = day_of_week in ['Saturday', 'Sunday']
        
        # Base staffing requirements
        base_requirements = {
            'waiter': 2,
            'kitchen': 3,
            'cashier': 1
        }
        
        # Apply traffic multipliers
        if is_weekend:
            for role in base_requirements:
                base_requirements[role] = int(base_requirements[role] * traffic_patterns['weekend_multiplier'])
        
        schedule = []
        for role, count in base_requirements.items():
            available_for_role = [
                staff for staff in availability 
                if self._can_work_position(staff, role) and self._is_available(staff, date_obj)
            ]
            
            # Assign staff to shifts
            assigned = available_for_role[:count]
            for i, staff in enumerate(assigned):
                schedule.append({
                    'staff_id': staff.id,
                    'date': date_obj,
                    'position': role,
                    'start_time': time(9, 0),  # 9:00 AM
                    'end_time': time(17 + i, 0),  # Staggered end times
                    'shift_type': 'regular'
                })
        
        return schedule
    
    def _analyze_schedule_coverage(self, schedule: List[Dict], traffic_patterns: Dict) -> Dict:
        """Analyze schedule coverage against expected demand"""
        # Simplified coverage analysis
        return {
            'overall_coverage': 95,  # Percentage
            'peak_coverage': 88,
            'off_peak_coverage': 98,
            'gaps': []
        }
    
    def _estimate_labor_cost(self, db: Session, schedule: List[Dict]) -> Decimal:
        """Estimate total labor cost for schedule"""
        total_cost = Decimal('0.00')
        for shift in schedule:
            hourly_rate = self._get_hourly_rate(db, shift['staff_id'], shift['position'])
            shift_duration = 8  # 8 hours
            total_cost += Decimal(str(shift_duration * hourly_rate))
        
        return total_cost
    
    def _calculate_labor_efficiency(self, db: Session, start_date: date, 
                                  end_date: date, total_hours: float) -> Dict:
        """Calculate labor efficiency metrics"""
        period_revenue = self._get_period_revenue(db, start_date, end_date)
        revenue_per_hour = period_revenue / total_hours if total_hours > 0 else 0
        
        return {
            'revenue_per_hour': revenue_per_hour,
            'labor_efficiency': 'good' if revenue_per_hour > 100 else 'needs_improvement',
            'target_revenue_per_hour': 150,
            'efficiency_score': min(100, (revenue_per_hour / 150) * 100)
        }

advanced_staff_service = AdvancedStaffService()
