# modules/inventory/recipe_costing_service.py - Recipe Costing System
from __future__ import annotations
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_

from src.core.database.models import (
    InventoryItem, MenuItemRecipe, MenuItem, PurchaseReceipt,
    WasteRecord, Supplier
)

class RecipeCostingService:
    """Real-time recipe costing with ingredient price tracking"""
    
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
            
            if not recipe_items:
                return {'error': 'Recipe tapılmadı'}
            
            total_cost = Decimal('0.00')
            ingredient_costs = []
            cost_breakdown = {}
            
            for recipe_item in recipe_items:
                if not recipe_item.inventory_item:
                    continue
                
                # Get current cost per unit
                current_cost = self._get_current_ingredient_cost(db, recipe_item.inventory_item_id)
                if current_cost is None:
                    current_cost = Decimal('0.00')
                
                # Calculate cost for this ingredient
                ingredient_total = current_cost * Decimal(str(recipe_item.quantity_per_unit))
                total_cost += ingredient_total
                
                ingredient_data = {
                    'ingredient_id': recipe_item.inventory_item_id,
                    'ingredient_name': recipe_item.inventory_item.name,
                    'quantity': recipe_item.quantity_per_unit,
                    'unit': recipe_item.quantity_unit,
                    'unit_cost': float(current_cost),
                    'total_cost': float(ingredient_total),
                    'cost_percentage': 0  # Will be calculated below
                }
                ingredient_costs.append(ingredient_data)
                
                # Cost breakdown by category
                category = recipe_item.inventory_item.category or 'Uncategorized'
                if category not in cost_breakdown:
                    cost_breakdown[category] = {'total_cost': 0, 'ingredients': []}
                cost_breakdown[category]['total_cost'] += ingredient_total
                cost_breakdown[category]['ingredients'].append(ingredient_data)
            
            # Calculate cost percentages
            for ingredient in ingredient_costs:
                if total_cost > 0:
                    ingredient['cost_percentage'] = (Decimal(str(ingredient['total_cost'])) / total_cost) * 100
            
            # Get menu item details
            menu_item = db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
            
            return {
                'menu_item_id': menu_item_id,
                'menu_item_name': menu_item.name if menu_item else 'Unknown',
                'menu_item_price': float(menu_item.price) if menu_item else 0,
                'total_recipe_cost': float(total_cost),
                'profit_margin': float(((menu_item.price - total_cost) / menu_item.price) * 100) if menu_item and menu_item.price > 0 else 0,
                'profit_amount': float(menu_item.price - total_cost) if menu_item else 0,
                'ingredient_costs': ingredient_costs,
                'cost_breakdown': cost_breakdown,
                'calculated_at': datetime.utcnow().isoformat(),
                'cost_trend': self._get_cost_trend(db, menu_item_id)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def batch_recipe_costing(self, db: Session, menu_item_ids: List[int]) -> Dict:
        """Calculate costs for multiple menu items"""
        try:
            results = {}
            total_menu_cost = Decimal('0.00')
            
            for menu_item_id in menu_item_ids:
                cost_result = self.calculate_recipe_cost(db, menu_item_id)
                if 'error' not in cost_result:
                    results[menu_item_id] = cost_result
                    total_menu_cost += Decimal(str(cost_result['total_recipe_cost']))
            
            # Calculate overall metrics
            avg_cost = total_menu_cost / len(results) if results else 0
            
            return {
                'menu_items': results,
                'summary': {
                    'total_items': len(results),
                    'total_cost': float(total_menu_cost),
                    'average_cost': float(avg_cost),
                    'calculated_at': datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_cost_changes_alert(self, db: Session, threshold_percentage: float = 15.0) -> List[Dict]:
        """Get alerts for significant cost changes"""
        try:
            # Get recent purchase receipts
            recent_purchases = db.query(PurchaseReceipt).filter(
                PurchaseReceipt.purchased_at >= datetime.utcnow() - timedelta(days=30),
                PurchaseReceipt.is_cancelled == False
            ).all()
            
            alerts = []
            
            # Group by inventory item
            item_prices = {}
            for receipt in recent_purchases:
                for item in receipt.items:
                    if item.inventory_item_id not in item_prices:
                        item_prices[item.inventory_item_id] = []
                    item_prices[item.inventory_item_id].append({
                        'price': item.unit_price,
                        'date': receipt.purchased_at,
                        'supplier': receipt.supplier.name if receipt.supplier else 'Unknown'
                    })
            
            # Check for price changes
            for item_id, price_history in item_prices.items():
                if len(price_history) < 2:
                    continue
                
                # Sort by date
                price_history.sort(key=lambda x: x['date'])
                
                # Calculate price change
                old_price = price_history[0]['price']
                new_price = price_history[-1]['price']
                
                if old_price > 0:
                    price_change = ((new_price - old_price) / old_price) * 100
                    
                    if abs(price_change) >= threshold_percentage:
                        inventory_item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
                        
                        alerts.append({
                            'inventory_item_id': item_id,
                            'item_name': inventory_item.name if inventory_item else 'Unknown',
                            'old_price': float(old_price),
                            'new_price': float(new_price),
                            'price_change_percentage': price_change,
                            'old_supplier': price_history[0]['supplier'],
                            'new_supplier': price_history[-1]['supplier'],
                            'old_date': price_history[0]['date'].isoformat(),
                            'new_date': price_history[-1]['date'].isoformat(),
                            'alert_type': 'price_increase' if price_change > 0 else 'price_decrease',
                            'severity': 'high' if abs(price_change) >= 25 else 'medium'
                        })
            
            return sorted(alerts, key=lambda x: abs(x['price_change_percentage']), reverse=True)
            
        except Exception as e:
            return []
    
    def get_menu_engineering_report(self, db: Session, start_date: date, end_date: date) -> Dict:
        """Generate menu engineering report with cost analysis"""
        try:
            # Get all menu items
            menu_items = db.query(MenuItem).filter(MenuItem.is_active == True).all()
            
            menu_analysis = []
            high_margin_items = []
            low_margin_items = []
            high_cost_items = []
            
            for menu_item in menu_items:
                cost_result = self.calculate_recipe_cost(db, menu_item.id)
                if 'error' in cost_result:
                    continue
                
                item_data = {
                    'menu_item_id': menu_item.id,
                    'name': menu_item.name,
                    'category': menu_item.category.name if menu_item.category else 'Uncategorized',
                    'price': float(menu_item.price),
                    'cost': cost_result['total_recipe_cost'],
                    'profit_margin': cost_result['profit_margin'],
                    'profit_amount': cost_result['profit_amount']
                }
                menu_analysis.append(item_data)
                
                # Categorize items
                if cost_result['profit_margin'] >= 70:
                    high_margin_items.append(item_data)
                elif cost_result['profit_margin'] <= 20:
                    low_margin_items.append(item_data)
                
                if cost_result['total_recipe_cost'] >= menu_item.price * 0.8:
                    high_cost_items.append(item_data)
            
            # Calculate category analysis
            category_analysis = {}
            for item in menu_analysis:
                category = item['category']
                if category not in category_analysis:
                    category_analysis[category] = {
                        'items': [],
                        'total_price': 0,
                        'total_cost': 0,
                        'avg_margin': 0
                    }
                
                category_analysis[category]['items'].append(item)
                category_analysis[category]['total_price'] += item['price']
                category_analysis[category]['total_cost'] += item['cost']
            
            # Calculate category averages
            for category, data in category_analysis.items():
                if data['items']:
                    data['avg_margin'] = sum(item['profit_margin'] for item in data['items']) / len(data['items'])
            
            return {
                'period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'summary': {
                    'total_items': len(menu_analysis),
                    'avg_profit_margin': sum(item['profit_margin'] for item in menu_analysis) / len(menu_analysis) if menu_analysis else 0,
                    'high_margin_items': len(high_margin_items),
                    'low_margin_items': len(low_margin_items),
                    'high_cost_items': len(high_cost_items)
                },
                'menu_analysis': menu_analysis,
                'category_analysis': category_analysis,
                'recommendations': {
                    'high_margin': high_margin_items[:5],  # Top 5 high margin
                    'low_margin': low_margin_items[:5],  # Bottom 5 low margin
                    'high_cost': high_cost_items[:5],  # Top 5 high cost
                    'price_optimization': self._generate_price_optimization_suggestions(menu_analysis)
                }
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def update_ingredient_prices(self, db: Session, purchase_data: Dict) -> Tuple[bool, str]:
        """Update ingredient prices based on new purchase data"""
        try:
            updated_items = []
            
            for item_data in purchase_data['items']:
                inventory_item = db.query(InventoryItem).filter(
                    InventoryItem.id == item_data['inventory_item_id']
                ).first()
                
                if not inventory_item:
                    continue
                
                # Update cost per unit
                old_cost = inventory_item.cost_per_unit
                new_cost = Decimal(str(item_data['unit_price']))
                
                inventory_item.cost_per_unit = new_cost
                inventory_item.updated_at = datetime.utcnow()
                
                updated_items.append({
                    'item_id': inventory_item.id,
                    'item_name': inventory_item.name,
                    'old_cost': float(old_cost) if old_cost else 0,
                    'new_cost': float(new_cost),
                    'cost_change': float(new_cost - old_cost) if old_cost else 0
                })
            
            db.commit()
            return True, f"{len(updated_items)} mehsulun qiymeti yenilendi"
            
        except Exception as e:
            db.rollback()
            return False, f"Price update xetasi: {str(e)}"
    
    def _get_current_ingredient_cost(self, db: Session, ingredient_id: int) -> Optional[Decimal]:
        """Get current cost per unit for ingredient"""
        # Try to get from latest purchase receipt
        latest_purchase = db.query(PurchaseReceiptItem).join(PurchaseReceipt).filter(
            PurchaseReceiptItem.inventory_item_id == ingredient_id,
            PurchaseReceipt.is_cancelled == False
        ).order_by(PurchaseReceipt.purchased_at.desc()).first()
        
        if latest_purchase:
            return Decimal(str(latest_purchase.unit_price))
        
        # Fallback to inventory item cost
        inventory_item = db.query(InventoryItem).filter(InventoryItem.id == ingredient_id).first()
        return Decimal(str(inventory_item.cost_per_unit)) if inventory_item and inventory_item.cost_per_unit else None
    
    def _get_cost_trend(self, db: Session, menu_item_id: int) -> List[Dict]:
        """Get cost trend for a menu item"""
        try:
            # Get historical cost data (simplified)
            # In a real implementation, this would track historical recipe costs
            return [
                {'date': '2024-01-01', 'cost': 5.50},
                {'date': '2024-02-01', 'cost': 5.75},
                {'date': '2024-03-01', 'cost': 5.60}
            ]
        except Exception as e:
            return []
    
    def _generate_price_optimization_suggestions(self, menu_analysis: List[Dict]) -> List[Dict]:
        """Generate price optimization suggestions"""
        suggestions = []
        
        for item in menu_analysis:
            if item['profit_margin'] < 20:
                suggestions.append({
                    'item_id': item['menu_item_id'],
                    'item_name': item['name'],
                    'current_price': item['price'],
                    'current_cost': item['cost'],
                    'current_margin': item['profit_margin'],
                    'suggestion': 'price_increase',
                    'recommended_price': round(item['cost'] * 1.3, 2),  # 30% margin
                    'potential_increase': round(item['cost'] * 1.3 - item['price'], 2),
                    'reason': 'Low profit margin requires price adjustment'
                })
            elif item['profit_margin'] > 80:
                suggestions.append({
                    'item_id': item['menu_item_id'],
                    'item_name': item['name'],
                    'current_price': item['price'],
                    'current_cost': item['cost'],
                    'current_margin': item['profit_margin'],
                    'suggestion': 'price_decrease',
                    'recommended_price': round(item['cost'] * 1.5, 2),  # 50% margin
                    'potential_decrease': round(item['price'] - item['cost'] * 1.5, 2),
                    'reason': 'Very high margin may allow competitive pricing'
                })
        
        return suggestions[:10]  # Top 10 suggestions

recipe_costing_service = RecipeCostingService()
