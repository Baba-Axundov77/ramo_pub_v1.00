# modules/staff/shift_scheduling_service.py - Advanced Shift Scheduling
from __future__ import annotations
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date, timedelta, time
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_

from database.models import (
    User, StaffSchedule, UserRole, Order, StaffPerformance,
    LeaveRequest, Shift
)

class ShiftSchedulingService:
    """Advanced staff scheduling with optimization and conflict resolution"""
    
    def __init__(self):
        pass
    
    def generate_weekly_schedule(self, db: Session, start_date: date, 
                               optimization_level: str = 'balanced') -> Dict:
        """Generate optimized weekly schedule"""
        try:
            # Get historical traffic patterns
            traffic_patterns = self._get_traffic_patterns(db, start_date)
            
            # Get staff availability and preferences
            staff_data = self._get_staff_availability(db, start_date)
            
            # Calculate staffing requirements
            requirements = self._calculate_staffing_requirements(traffic_patterns)
            
            # Generate schedule
            schedule = []
            current_date = start_date
            
            for day_offset in range(7):  # 7 days
                day_date = current_date + timedelta(days=day_offset)
                day_name = day_date.strftime('%A')
                
                day_schedule = self._generate_day_schedule(
                    day_date, day_name, requirements[day_name], 
                    staff_data, optimization_level
                )
                schedule.extend(day_schedule)
            
            # Save schedule to database
            self._save_schedule(db, schedule)
            
            # Analyze generated schedule
            analysis = self._analyze_schedule(schedule, requirements, staff_data)
            
            return {
                'schedule': schedule,
                'analysis': analysis,
                'requirements': requirements,
                'traffic_patterns': traffic_patterns,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def optimize_shift_assignments(self, db: Session, schedule_id: int) -> Dict:
        """Optimize existing shift assignments"""
        try:
            # Get existing schedule
            existing_schedule = db.query(StaffSchedule).filter(
                StaffSchedule.schedule_id == schedule_id
            ).all()
            
            # Get performance data
            performance_data = self._get_staff_performance(db)
            
            # Get constraints
            constraints = self._get_scheduling_constraints(db)
            
            # Optimization algorithm
            optimized_assignments = self._optimize_assignments(
                existing_schedule, performance_data, constraints
            )
            
            # Update schedule
            for assignment in optimized_assignments:
                schedule_item = next(
                    (s for s in existing_schedule if s.id == assignment['schedule_id']), 
                    None
                )
                if schedule_item:
                    schedule_item.staff_id = assignment['staff_id']
                    schedule_item.optimization_score = assignment['score']
            
            db.commit()
            
            return {
                'optimized_assignments': len(optimized_assignments),
                'improvement_score': self._calculate_improvement_score(
                    existing_schedule, optimized_assignments
                ),
                'updated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            db.rollback()
            return {'error': str(e)}
    
    def handle_shift_swaps(self, db: Session, swap_request: Dict) -> Tuple[bool, str]:
        """Handle shift swap requests with approval workflow"""
        try:
            # Validate swap request
            validation = self._validate_swap_request(db, swap_request)
            if not validation['valid']:
                return False, validation['error']
            
            # Create swap records
            original_shift = db.query(StaffSchedule).filter(
                StaffSchedule.id == swap_request['original_shift_id']
            ).first()
            
            target_shift = db.query(StaffSchedule).filter(
                StaffSchedule.id == swap_request['target_shift_id']
            ).first()
            
            if not original_shift or not target_shift:
                return False, "Shift tapılmadı"
            
            # Check for conflicts
            if self._has_shift_conflict(db, swap_request['requester_id'], target_shift):
                return False, "Target shift zamanında konflikt var"
            
            # Create swap request record
            swap_record = ShiftSwapRequest(
                original_shift_id=swap_request['original_shift_id'],
                target_shift_id=swap_request['target_shift_id'],
                requester_id=swap_request['requester_id'],
                target_staff_id=swap_request['target_staff_id'],
                reason=swap_request['reason'],
                status='pending',
                created_at=datetime.utcnow()
            )
            db.add(swap_record)
            
            db.commit()
            return True, "Swap request göndərildi"
            
        except Exception as e:
            db.rollback()
            return False, f"Swap request xətası: {str(e)}"
    
    def get_schedule_coverage(self, db: Session, start_date: date, 
                           end_date: date) -> Dict:
        """Analyze schedule coverage and gaps"""
        try:
            # Get all shifts in period
            shifts = db.query(StaffSchedule).options(
                joinedload(StaffSchedule.staff)
            ).filter(
                StaffSchedule.shift_date >= start_date,
                StaffSchedule.shift_date <= end_date
            ).all()
            
            # Group by day and position
            coverage_data = {}
            current_date = start_date
            
            while current_date <= end_date:
                day_shifts = [s for s in shifts if s.shift_date == current_date]
                day_name = current_date.strftime('%A')
                
                # Calculate required vs actual staffing
                required = self._get_day_requirements(current_date)
                actual = self._get_actual_coverage(day_shifts)
                
                coverage_data[day_name] = {
                    'date': current_date.isoformat(),
                    'required': required,
                    'actual': actual,
                    'coverage_percentage': self._calculate_coverage_percentage(required, actual),
                    'gaps': self._identify_coverage_gaps(required, actual),
                    'overstaffing': self._identify_overstaffing(required, actual),
                    'shifts': [
                        {
                            'id': shift.id,
                            'staff_name': shift.staff.full_name,
                            'position': shift.position,
                            'start_time': shift.start_time.isoformat(),
                            'end_time': shift.end_time.isoformat()
                        } for shift in day_shifts
                    ]
                }
                
                current_date += timedelta(days=1)
            
            # Calculate overall metrics
            overall_metrics = self._calculate_overall_coverage_metrics(coverage_data)
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'daily_coverage': coverage_data,
                'overall_metrics': overall_metrics,
                'recommendations': self._generate_coverage_recommendations(coverage_data)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def auto_fill_shift_gaps(self, db: Session, date: date, 
                              position: str) -> Dict:
        """Automatically fill shift gaps with available staff"""
        try:
            # Get required staffing for the day
            required = self._get_day_requirements(date)
            position_required = required.get(position, 0)
            
            # Get current assignments
            current_assignments = db.query(StaffSchedule).filter(
                StaffSchedule.shift_date == date,
                StaffSchedule.position == position
            ).all()
            
            if len(current_assignments) >= position_required:
                return {'message': 'Gap yoxdur, tam doldurulub'}
            
            # Get available staff
            available_staff = self._get_available_staff_for_shift(db, date, position)
            
            # Calculate how many more staff needed
            staff_needed = position_required - len(current_assignments)
            
            # Select best candidates
            candidates = self._select_best_candidates(available_staff, staff_needed)
            
            # Create assignments
            new_assignments = []
            for i, candidate in enumerate(candidates):
                # Find appropriate shift time
                shift_time = self._determine_shift_time(position, i, len(current_assignments) + i)
                
                assignment = StaffSchedule(
                    staff_id=candidate['staff_id'],
                    shift_date=date,
                    start_time=shift_time['start'],
                    end_time=shift_time['end'],
                    position=position,
                    assignment_type='auto_fill',
                    created_at=datetime.utcnow()
                )
                db.add(assignment)
                new_assignments.append(assignment)
            
            db.commit()
            
            return {
                'filled_positions': len(new_assignments),
                'candidates': candidates,
                'shift_times': [self._determine_shift_time(position, i, len(current_assignments) + i) for i in range(len(new_assignments))],
                'filled_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            db.rollback()
            return {'error': str(e)}
    
    def _generate_day_schedule(self, day_date: date, day_name: str, 
                              requirements: Dict, staff_data: Dict, 
                              optimization_level: str) -> List[Dict]:
        """Generate schedule for a specific day"""
        schedule = []
        
        for position, required_count in requirements.items():
            if required_count == 0:
                continue
            
            # Get available staff for this position
            available_staff = [
                staff for staff in staff_data['all_staff']
                if self._can_work_position(staff, position) and 
                self._is_staff_available(staff, day_date, staff_data)
            ]
            
            # Sort by preference and performance
            available_staff.sort(key=lambda x: (
                x.get('preference_score', 0),
                x.get('performance_score', 0)
            ), reverse=True)
            
            # Assign staff to shifts
            assigned_count = min(required_count, len(available_staff))
            
            for i in range(assigned_count):
                staff = available_staff[i]
                shift_time = self._determine_shift_time(position, i, required_count)
                
                schedule.append({
                    'staff_id': staff['id'],
                    'staff_name': staff['full_name'],
                    'position': position,
                    'date': day_date,
                    'start_time': shift_time['start'],
                    'end_time': shift_time['end'],
                    'shift_type': shift_time['type'],
                    'optimization_score': self._calculate_assignment_score(staff, position, day_name)
                })
        
        return schedule
    
    def _determine_shift_time(self, position: str, index: int, total_required: int) -> Dict:
        """Determine optimal shift time based on position and index"""
        base_shifts = {
            'waiter': [
                {'start': time(9, 0), 'end': time(17, 0), 'type': 'morning'},
                {'start': time(17, 0), 'end': time(1, 0), 'type': 'evening'}
            ],
            'kitchen': [
                {'start': time(8, 0), 'end': time(16, 0), 'type': 'morning'},
                {'start': time(16, 0), 'end': time(0, 0), 'type': 'evening'}
            ],
            'cashier': [
                {'start': time(9, 0), 'end': time(17, 0), 'type': 'morning'},
                {'start': time(17, 0), 'end': time(1, 0), 'type': 'evening'}
            ],
            'manager': [
                {'start': time(9, 0), 'end': time(18, 0), 'type': 'regular'}
            ]
        }
        
        if position in base_shifts:
            shifts = base_shifts[position]
            return shifts[index % len(shifts)]
        
        # Default shift
        return {
            'start': time(9, 0),
            'end': time(17, 0),
            'type': 'regular'
        }
    
    def _calculate_staffing_requirements(self, traffic_patterns: Dict) -> Dict:
        """Calculate staffing requirements based on traffic patterns"""
        base_requirements = {
            'Monday': {'waiter': 2, 'kitchen': 3, 'cashier': 1, 'manager': 1},
            'Tuesday': {'waiter': 2, 'kitchen': 3, 'cashier': 1, 'manager': 1},
            'Wednesday': {'waiter': 2, 'kitchen': 3, 'cashier': 1, 'manager': 1},
            'Thursday': {'waiter': 2, 'kitchen': 3, 'cashier': 1, 'manager': 1},
            'Friday': {'waiter': 3, 'kitchen': 4, 'cashier': 1, 'manager': 1},
            'Saturday': {'waiter': 4, 'kitchen': 5, 'cashier': 2, 'manager': 1},
            'Sunday': {'waiter': 4, 'kitchen': 5, 'cashier': 2, 'manager': 1}
        }
        
        # Apply traffic multipliers
        for day in base_requirements:
            multiplier = traffic_patterns.get('daily_multipliers', {}).get(day, 1.0)
            for position in base_requirements[day]:
                base_requirements[day][position] = int(base_requirements[day][position] * multiplier)
        
        return base_requirements
    
    def _analyze_schedule(self, schedule: List[Dict], requirements: Dict, 
                         staff_data: Dict) -> Dict:
        """Analyze generated schedule for quality metrics"""
        total_shifts = len(schedule)
        total_hours = sum(
            self._calculate_shift_duration(shift['start_time'], shift['end_time'])
            for shift in schedule
        )
        
        # Calculate coverage
        coverage_score = 0
        for day_name, day_requirements in requirements.items():
            day_shifts = [s for s in schedule if s['date'].strftime('%A') == day_name]
            actual_coverage = {}
            for shift in day_shifts:
                position = shift['position']
                actual_coverage[position] = actual_coverage.get(position, 0) + 1
            
            day_score = 0
            for position, required in day_requirements.items():
                actual = actual_coverage.get(position, 0)
                if actual >= required:
                    day_score += 1
                else:
                    day_score += actual / required  # Partial coverage
            
            coverage_score += (day_score / len(day_requirements)) * 100
        
        overall_coverage = coverage_score / 7  # 7 days
        
        return {
            'total_shifts': total_shifts,
            'total_hours': total_hours,
            'estimated_labor_cost': self._estimate_labor_cost(schedule, staff_data),
            'coverage_percentage': overall_coverage,
            'staff_utilization': self._calculate_staff_utilization(schedule, staff_data),
            'balance_score': self._calculate_work_life_balance(schedule, staff_data)
        }

shift_scheduling_service = ShiftSchedulingService()
