# modules/inventory/advanced_inventory_service.py - Enterprise Inventory Management
from __future__ import annotations
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_

from database.models import (
    InventoryItem, InventoryAdjustment, MenuItemRecipe,
    PurchaseReceipt, WasteRecord, Supplier
)

class AdvancedInventoryService:
    """Enterprise-level inventory with costing, waste tracking, and forecasting"""
    
    def __init__(self):
        pass
    
    def calculate_recipe_cost(self, db: Session, menu_item_id: int) -> Dict:
        """Calculate real-time recipe cost based on current ingredient prices"""
        try:
            # Get recipe ingredients
            recipe_items = db.query(MenuItemRecipe).options(
                joinedload(MenuItemRecipe.inventory_item)
            ).filter(
                MenuItemRecipe.menu_item_id == menu_item_id,
                MenuItemRecipe.is_active == True
            ).all()
            
            total_cost = Decimal('0.00')
            ingredient_costs = []
            
            for recipe_item in recipe_items:
                if not recipe_item.inventory_item:
                    continue
                
                # Get current cost per unit
                current_cost = self._get_current_ingredient_cost(db, recipe_item.inventory_item_id)
                if current_cost:
                    ingredient_total = current_cost * Decimal(str(recipe_item.quantity_per_unit))
                    total_cost += ingredient_total
                    
                    ingredient_costs.append({
                        'ingredient_name': recipe_item.inventory_item.name,
                        'quantity': recipe_item.quantity_per_unit,
                        'unit': recipe_item.quantity_unit,
                        'unit_cost': float(current_cost),
                        'total_cost': float(ingredient_total)
                    })
            
            return {
                'menu_item_id': menu_item_id,
                'total_cost': float(total_cost),
                'ingredient_costs': ingredient_costs,
                'calculated_at': datetime.utcnow()
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def track_waste(self, db: Session, waste_data: List[Dict]) -> Tuple[bool, str]:
        """Track food waste with detailed categorization"""
        try:
            waste_records = []
            for waste in waste_data:
                waste_record = WasteRecord(
                    inventory_item_id=waste['inventory_item_id'],
                    quantity=Decimal(str(waste['quantity'])),
                    unit=waste['unit'],
                    waste_type=waste['waste_type'],  # spoilage, overportion, customer_return, etc.
                    reason=waste['reason'],
                    estimated_cost=Decimal(str(waste.get('estimated_cost', 0))),
                    recorded_by=waste['staff_id'],
                    recorded_at=datetime.utcnow()
                )
                waste_records.append(waste_record)
            
            # Add all waste records
            for record in waste_records:
                db.add(record)
            
            # Update inventory quantities
            for waste in waste_data:
                self._adjust_inventory_for_waste(db, waste['inventory_item_id'], waste['quantity'])
            
            db.commit()
            return True, f"{len(waste_records)} waste record uğurla əlavə edildi"
            
        except Exception as e:
            db.rollback()
            return False, f"Waste tracking xətası: {str(e)}"
    
    def generate_inventory_report(self, db: Session, start_date: date, end_date: date) -> Dict:
        """Generate comprehensive inventory report"""
        try:
            # Get all inventory movements
            adjustments = db.query(InventoryAdjustment).filter(
                InventoryAdjustment.created_at >= start_date,
                InventoryAdjustment.created_at <= end_date
            ).all()
            
            waste_records = db.query(WasteRecord).filter(
                WasteRecord.recorded_at >= start_date,
                WasteRecord.recorded_at <= end_date
            ).all()
            
            purchases = db.query(PurchaseReceipt).filter(
                PurchaseReceipt.purchased_at >= start_date,
                PurchaseReceipt.purchased_at <= end_date,
                PurchaseReceipt.is_cancelled == False
            ).all()
            
            # Calculate metrics
            total_purchases = sum(p.total_amount for p in purchases)
            total_waste_cost = sum(w.estimated_cost for w in waste_records)
            
            # Current inventory value
            current_inventory = db.query(InventoryItem).filter(
                InventoryItem.is_active == True
            ).all()
            
            current_inventory_value = sum(
                item.quantity * self._get_current_ingredient_cost(db, item.id) or Decimal('0.00')
                for item in current_inventory
            )
            
            # Waste analysis
            waste_by_type = {}
            for waste in waste_records:
                waste_type = waste.waste_type
                waste_by_type[waste_type] = waste_by_type.get(waste_type, 0) + float(waste.estimated_cost)
            
            # Top waste items
            top_waste_items = db.query(
                WasteRecord.inventory_item_id,
                func.sum(WasteRecord.quantity).label('total_waste'),
                func.sum(WasteRecord.estimated_cost).label('total_cost')
            ).filter(
                WasteRecord.recorded_at >= start_date,
                WasteRecord.recorded_at <= end_date
            ).group_by(WasteRecord.inventory_item_id).order_by(
                func.sum(WasteRecord.estimated_cost).desc()
            ).limit(10).all()
            
            return {
                'period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'financial_summary': {
                    'total_purchases': float(total_purchases),
                    'total_waste_cost': float(total_waste_cost),
                    'waste_percentage': float(total_waste_cost / total_purchases * 100) if total_purchases > 0 else 0,
                    'current_inventory_value': float(current_inventory_value)
                },
                'waste_analysis': {
                    'by_type': waste_by_type,
                    'top_items': [
                        {
                            'item_id': item.inventory_item_id,
                            'total_quantity': float(item.total_waste),
                            'total_cost': float(item.total_cost)
                        } for item in top_waste_items
                    ]
                },
                'movement_summary': {
                    'total_adjustments': len(adjustments),
                    'total_waste_records': len(waste_records),
                    'total_purchase_receipts': len(purchases)
                }
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def forecast_demand(self, db: Session, days_ahead: int = 7) -> Dict:
        """Forecast inventory demand based on historical data"""
        try:
            # Get historical sales data for the last 4 weeks
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(weeks=4)
            
            # This would typically query sales/order data
            # For demo, we'll use a simplified approach
            historical_consumption = db.query(
                InventoryAdjustment.inventory_item_id,
                func.sum(func.abs(InventoryAdjustment.delta_quantity)).label('total_consumed')
            ).filter(
                InventoryAdjustment.adjustment_type == 'manual',
                InventoryAdjustment.created_at >= start_date,
                InventoryAdjustment.created_at <= end_date
            ).group_by(InventoryAdjustment.inventory_item_id).all()
            
            forecasts = []
            for item_data in historical_consumption:
                # Simple average daily consumption
                avg_daily_consumption = item_data.total_consumed / 28  # 4 weeks = 28 days
                forecasted_demand = avg_daily_consumption * days_ahead
                
                # Get current stock
                current_stock = self._get_current_stock(db, item_data.inventory_item_id)
                
                # Calculate recommended order
                min_stock = self._get_min_stock_level(db, item_data.inventory_item_id)
                recommended_order = max(0, forecasted_demand - current_stock + min_stock)
                
                forecasts.append({
                    'inventory_item_id': item_data.inventory_item_id,
                    'item_name': self._get_item_name(db, item_data.inventory_item_id),
                    'current_stock': current_stock,
                    'avg_daily_consumption': avg_daily_consumption,
                    'forecasted_demand': forecasted_demand,
                    'min_stock_level': min_stock,
                    'recommended_order_quantity': recommended_order,
                    'days_of_stock_remaining': current_stock / avg_daily_consumption if avg_daily_consumption > 0 else 999
                })
            
            # Sort by recommended order quantity (descending)
            forecasts.sort(key=lambda x: x['recommended_order_quantity'], reverse=True)
            
            return {
                'forecast_period_days': days_ahead,
                'generated_at': datetime.utcnow(),
                'forecasts': forecasts,
                'total_recommended_orders': sum(f['recommended_order_quantity'] for f in forecasts)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def suggest_auto_orders(self, db: Session) -> List[Dict]:
        """Suggest automatic orders based on current stock and demand"""
        try:
            # Get items that need reordering
            items_to_order = db.query(InventoryItem).filter(
                InventoryItem.is_active == True,
                InventoryItem.quantity <= InventoryItem.min_quantity
            ).all()
            
            suggestions = []
            for item in items_to_order:
                # Calculate optimal order quantity
                avg_monthly_usage = self._get_avg_monthly_usage(db, item.id)
                lead_time_days = self._get_supplier_lead_time(db, item.id)
                
                # Safety stock calculation
                safety_stock = avg_monthly_usage / 30 * lead_time_days * 1.5  # 50% safety factor
                
                # Economic Order Quantity (EOQ) - simplified
                holding_cost = 0.1  # 10% annual holding cost
                order_cost = 10  # Fixed order cost
                eoq = ((2 * avg_monthly_usage * order_cost) / (holding_cost * item.cost_per_unit or 1)) ** 0.5
                
                suggested_quantity = max(
                    item.min_quantity * 2,  # At least double min stock
                    int(eoq),
                    safety_stock + item.min_quantity
                )
                
                suggestions.append({
                    'inventory_item_id': item.id,
                    'item_name': item.name,
                    'current_stock': item.quantity,
                    'min_stock': item.min_quantity,
                    'suggested_quantity': suggested_quantity,
                    'estimated_cost': float(suggested_quantity * (item.cost_per_unit or 0)),
                    'supplier': self._get_preferred_supplier(db, item.id),
                    'urgency': self._calculate_urgency(item.quantity, item.min_quantity),
                    'reason': self._get_order_reason(item.quantity, item.min_quantity, avg_monthly_usage)
                })
            
            # Sort by urgency
            suggestions.sort(key=lambda x: x['urgency'], reverse=True)
            
            return suggestions
            
        except Exception as e:
            return []
    
    def _get_current_ingredient_cost(self, db: Session, ingredient_id: int) -> Optional[Decimal]:
        """Get current cost per unit for ingredient"""
        # This would typically come from latest purchase data
        latest_purchase = db.query(PurchaseReceipt).join(
            # Join through purchase receipt items to get cost
        ).filter(
            # Filter for this ingredient
        ).order_by(PurchaseReceipt.purchased_at.desc()).first()
        
        # Simplified - return from inventory item
        item = db.query(InventoryItem).filter(InventoryItem.id == ingredient_id).first()
        return Decimal(str(item.cost_per_unit)) if item else None
    
    def _adjust_inventory_for_waste(self, db: Session, inventory_item_id: int, quantity: float):
        """Adjust inventory for waste"""
        item = db.query(InventoryItem).filter(InventoryItem.id == inventory_item_id).first()
        if item:
            item.quantity = max(0, item.quantity - quantity)
    
    def _calculate_urgency(self, current_stock: float, min_stock: float) -> int:
        """Calculate urgency level for reordering"""
        if current_stock <= 0:
            return 5  # Critical - out of stock
        elif current_stock < min_stock * 0.5:
            return 4  # Very urgent
        elif current_stock < min_stock:
            return 3  # Urgent
        elif current_stock < min_stock * 1.5:
            return 2  # Moderate
        else:
            return 1  # Low priority
    
    def _get_order_reason(self, current_stock: float, min_stock: float, avg_usage: float) -> str:
        """Generate reason for order suggestion"""
        if current_stock <= 0:
            return "Stok qurtarıb - təcili sifariş lazımdır"
        elif current_stock < min_stock * 0.5:
            return "Stok təhlükəli aşağıdır - sürətli sifariş tövsiyyə olunur"
        elif current_stock < min_stock:
            return "Stok minimum səviyyənin altındadır"
        elif avg_usage > 0 and current_stock / avg_usage < 7:
            return "7 gündən az stok qalacaq"
        else:
            return "Planlı sifariş tövsiyyə olunur"

advanced_inventory_service = AdvancedInventoryService()
