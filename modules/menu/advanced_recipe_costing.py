# Advanced Recipe Costing & Menu Engineering Service
# Comprehensive cost analysis, price optimization, and menu engineering

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, and_, or_
from database.models import (
    MenuItem, MenuItemRecipe, InventoryItem, OrderItem, Order, 
    MenuCategory, CustomerTier, Customer
)
from decimal import Decimal
import json

class AdvancedRecipeCostingService:
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_recipe_cost(self, menu_item_id: int, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Calculate detailed recipe cost for a menu item"""
        try:
            if not date:
                date = datetime.now()
            
            menu_item = self.db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
            if not menu_item:
                return {'success': False, 'message': 'Menu item not found'}
            
            # Get recipe ingredients
            recipes = self.db.query(MenuItemRecipe).join(InventoryItem).filter(
                MenuItemRecipe.menu_item_id == menu_item_id,
                MenuItemRecipe.is_active == True,
                or_(
                    MenuItemRecipe.valid_from <= date,
                    MenuItemRecipe.valid_from.is_(None)
                ),
                or_(
                    MenuItemRecipe.valid_until >= date,
                    MenuItemRecipe.valid_until.is_(None)
                )
            ).all()
            
            if not recipes:
                return {
                    'success': True,
                    'menu_item_id': menu_item_id,
                    'menu_item_name': menu_item.name,
                    'recipe_cost': 0.0,
                    'ingredients': [],
                    'message': 'No recipe found for this item'
                }
            
            # Calculate ingredient costs
            ingredients = []
            total_cost = 0.0
            
            for recipe in recipes:
                inventory_item = recipe.inventory_item
                if not inventory_item:
                    continue
                
                # Get current inventory price
                unit_cost = float(inventory_item.unit_cost or 0.0)
                
                # Calculate total ingredient cost
                ingredient_cost = unit_cost * float(recipe.quantity_per_unit or 1.0)
                total_cost += ingredient_cost
                
                ingredients.append({
                    'inventory_item_id': inventory_item.id,
                    'inventory_item_name': inventory_item.name,
                    'quantity_per_unit': float(recipe.quantity_per_unit or 1.0),
                    'unit': recipe.quantity_unit or inventory_item.unit or 'unit',
                    'unit_cost': unit_cost,
                    'total_cost': ingredient_cost,
                    'cost_percentage': 0.0  # Will be calculated below
                })
            
            # Calculate cost percentages
            if total_cost > 0:
                for ingredient in ingredients:
                    ingredient['cost_percentage'] = (ingredient['total_cost'] / total_cost) * 100
            
            # Calculate profit metrics
            selling_price = float(menu_item.price)
            profit_margin = ((selling_price - total_cost) / selling_price) * 100 if selling_price > 0 else 0
            profit_amount = selling_price - total_cost
            
            return {
                'success': True,
                'menu_item_id': menu_item_id,
                'menu_item_name': menu_item.name,
                'category_id': menu_item.category_id,
                'selling_price': selling_price,
                'recipe_cost': total_cost,
                'profit_amount': profit_amount,
                'profit_margin': profit_margin,
                'ingredients': sorted(ingredients, key=lambda x: x['total_cost'], reverse=True),
                'calculated_at': date.isoformat(),
                'cost_per_serving': total_cost,
                'food_cost_percentage': (total_cost / selling_price) * 100 if selling_price > 0 else 0
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to calculate recipe cost'
            }
    
    def batch_recipe_costing(self, menu_item_ids: List[int]) -> Dict[str, Any]:
        """Calculate recipe costs for multiple menu items"""
        try:
            results = []
            total_cost = 0.0
            total_revenue = 0.0
            
            for menu_item_id in menu_item_ids:
                cost_result = self.calculate_recipe_cost(menu_item_id)
                if cost_result['success']:
                    results.append(cost_result)
                    total_cost += cost_result['recipe_cost']
                    total_revenue += cost_result['selling_price']
            
            # Calculate overall metrics
            overall_margin = ((total_revenue - total_cost) / total_revenue) * 100 if total_revenue > 0 else 0
            
            return {
                'success': True,
                'items': results,
                'summary': {
                    'total_items': len(results),
                    'total_cost': total_cost,
                    'total_revenue': total_revenue,
                    'overall_profit': total_revenue - total_cost,
                    'overall_margin': overall_margin
                },
                'calculated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to calculate batch recipe costs'
            }
    
    def analyze_menu_engineering(self, category_id: Optional[int] = None, 
                               date_from: Optional[datetime] = None,
                               date_to: Optional[datetime] = None) -> Dict[str, Any]:
        """Comprehensive menu engineering analysis"""
        try:
            if not date_from:
                date_from = datetime.now() - timedelta(days=30)
            if not date_to:
                date_to = datetime.now()
            
            # Get menu items with sales data
            query = self.db.query(MenuItem).outerjoin(OrderItem).join(Order).filter(
                Order.created_at.between(date_from, date_to),
                Order.status == 'paid'
            )
            
            if category_id:
                query = query.filter(MenuItem.category_id == category_id)
            
            menu_items = query.group_by(MenuItem.id).all()
            
            analysis_results = []
            
            for menu_item in menu_items:
                # Get sales data
                sales_data = self.db.query(
                    func.sum(OrderItem.quantity).label('total_quantity'),
                    func.sum(OrderItem.subtotal).label('total_revenue'),
                    func.count(Order.id).label('order_count')
                ).join(Order).filter(
                    OrderItem.menu_item_id == menu_item.id,
                    Order.created_at.between(date_from, date_to),
                    Order.status == 'paid'
                ).first()
                
                quantity = int(sales_data.total_quantity or 0)
                revenue = float(sales_data.total_revenue or 0.0)
                order_count = int(sales_data.order_count or 0)
                
                # Calculate cost
                cost_result = self.calculate_recipe_cost(menu_item.id)
                item_cost = cost_result['recipe_cost'] if cost_result['success'] else 0.0
                
                # Calculate metrics
                profit = revenue - (item_cost * quantity)
                profit_margin = (profit / revenue) * 100 if revenue > 0 else 0
                popularity_score = order_count  # Simple popularity metric
                
                # Menu engineering classification
                me_classification = self._classify_menu_item(popularity_score, profit_margin)
                
                analysis_results.append({
                    'menu_item_id': menu_item.id,
                    'menu_item_name': menu_item.name,
                    'category_id': menu_item.category_id,
                    'selling_price': float(menu_item.price),
                    'recipe_cost': item_cost,
                    'quantity_sold': quantity,
                    'revenue': revenue,
                    'profit': profit,
                    'profit_margin': profit_margin,
                    'order_count': order_count,
                    'popularity_score': popularity_score,
                    'me_classification': me_classification,
                    'food_cost_percentage': (item_cost / float(menu_item.price)) * 100 if menu_item.price > 0 else 0
                })
            
            # Sort by profit
            analysis_results.sort(key=lambda x: x['profit'], reverse=True)
            
            # Calculate category summary
            category_summary = {}
            for item in analysis_results:
                cat_id = item['category_id']
                if cat_id not in category_summary:
                    category_summary[cat_id] = {
                        'items': [],
                        'total_revenue': 0.0,
                        'total_profit': 0.0,
                        'total_quantity': 0.0
                    }
                
                category_summary[cat_id]['items'].append(item)
                category_summary[cat_id]['total_revenue'] += item['revenue']
                category_summary[cat_id]['total_profit'] += item['profit']
                category_summary[cat_id]['total_quantity'] += item['quantity_sold']
            
            return {
                'success': True,
                'period': {
                    'from': date_from.isoformat(),
                    'to': date_to.isoformat()
                },
                'menu_items': analysis_results,
                'category_summary': category_summary,
                'total_items': len(analysis_results),
                'analyzed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to analyze menu engineering'
            }
    
    def optimize_prices(self, target_food_cost_percentage: float = 30.0,
                        min_margin: float = 20.0,
                        max_margin: float = 80.0) -> Dict[str, Any]:
        """Price optimization recommendations"""
        try:
            # Get all menu items
            menu_items = self.db.query(MenuItem).filter(MenuItem.is_active == True).all()
            
            recommendations = []
            
            for menu_item in menu_items:
                # Calculate current cost
                cost_result = self.calculate_recipe_cost(menu_item.id)
                if not cost_result['success']:
                    continue
                
                current_price = float(menu_item.price)
                current_cost = cost_result['recipe_cost']
                current_food_cost_pct = (current_cost / current_price) * 100 if current_price > 0 else 0
                current_margin = ((current_price - current_cost) / current_price) * 100 if current_price > 0 else 0
                
                # Calculate optimal price
                if current_cost > 0:
                    optimal_price = current_cost / (target_food_cost_percentage / 100)
                    
                    # Ensure margin constraints
                    min_price = current_cost / (1 - min_margin / 100)
                    max_price = current_cost / (1 - max_margin / 100)
                    
                    optimal_price = max(min_price, min(max_price, optimal_price))
                    
                    # Generate recommendation
                    if abs(current_price - optimal_price) > 0.5:  # Only recommend if difference is significant
                        price_change_pct = ((optimal_price - current_price) / current_price) * 100
                        
                        recommendation = {
                            'menu_item_id': menu_item.id,
                            'menu_item_name': menu_item.name,
                            'current_price': current_price,
                            'current_cost': current_cost,
                            'current_food_cost_percentage': current_food_cost_pct,
                            'current_margin': current_margin,
                            'recommended_price': round(optimal_price, 2),
                            'recommended_food_cost_percentage': target_food_cost_percentage,
                            'recommended_margin': ((optimal_price - current_cost) / optimal_price) * 100,
                            'price_change_percentage': round(price_change_pct, 2),
                            'action': 'increase' if optimal_price > current_price else 'decrease',
                            'potential_impact': round((optimal_price - current_price) * 10, 2)  # Assuming 10 units sold
                        }
                        
                        recommendations.append(recommendation)
            
            # Sort by potential impact
            recommendations.sort(key=lambda x: abs(x['potential_impact']), reverse=True)
            
            return {
                'success': True,
                'parameters': {
                    'target_food_cost_percentage': target_food_cost_percentage,
                    'min_margin': min_margin,
                    'max_margin': max_margin
                },
                'recommendations': recommendations,
                'summary': {
                    'total_recommendations': len(recommendations),
                    'price_increases': len([r for r in recommendations if r['action'] == 'increase']),
                    'price_decreases': len([r for r in recommendations if r['action'] == 'decrease']),
                    'total_potential_impact': sum(r['potential_impact'] for r in recommendations)
                },
                'analyzed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to optimize prices'
            }
    
    def detect_cost_changes(self, days_back: int = 7) -> Dict[str, Any]:
        """Detect significant cost changes in ingredients"""
        try:
            # Get recent inventory price changes
            # This would require price history tracking - simplified version
            
            # Get current inventory costs
            inventory_items = self.db.query(InventoryItem).filter(
                InventoryItem.is_active == True
            ).all()
            
            cost_changes = []
            
            for item in inventory_items:
                # This is simplified - in reality, you'd track price history
                current_cost = float(item.unit_cost or 0.0)
                
                # Simulate previous cost (would come from history)
                previous_cost = current_cost * 0.95  # Assume 5% increase for demo
                
                if current_cost > 0 and previous_cost > 0:
                    change_percentage = ((current_cost - previous_cost) / previous_cost) * 100
                    
                    if abs(change_percentage) > 5:  # Significant change (>5%)
                        # Find affected menu items
                        affected_items = self.db.query(MenuItemRecipe).filter(
                            MenuItemRecipe.inventory_item_id == item.id,
                            MenuItemRecipe.is_active == True
                        ).all()
                        
                        affected_menu_items = []
                        for recipe in affected_items:
                            menu_item = self.db.query(MenuItem).filter(MenuItem.id == recipe.menu_item_id).first()
                            if menu_item:
                                affected_menu_items.append({
                                    'menu_item_id': menu_item.id,
                                    'menu_item_name': menu_item.name,
                                    'quantity_per_unit': float(recipe.quantity_per_unit or 1.0)
                                })
                        
                        cost_change = {
                            'inventory_item_id': item.id,
                            'inventory_item_name': item.name,
                            'previous_cost': previous_cost,
                            'current_cost': current_cost,
                            'change_percentage': round(change_percentage, 2),
                            'change_type': 'increase' if change_percentage > 0 else 'decrease',
                            'affected_menu_items': affected_menu_items,
                            'estimated_impact': round(change_percentage * len(affected_menu_items), 2)
                        }
                        
                        cost_changes.append(cost_change)
            
            # Sort by impact
            cost_changes.sort(key=lambda x: abs(x['estimated_impact']), reverse=True)
            
            return {
                'success': True,
                'period_days': days_back,
                'cost_changes': cost_changes,
                'summary': {
                    'total_changes': len(cost_changes),
                    'increases': len([c for c in cost_changes if c['change_type'] == 'increase']),
                    'decreases': len([c for c in cost_changes if c['change_type'] == 'decrease']),
                    'high_impact_changes': len([c for c in cost_changes if abs(c['estimated_impact']) > 20])
                },
                'detected_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to detect cost changes'
            }
    
    def _classify_menu_item(self, popularity_score: float, profit_margin: float) -> str:
        """Classify menu item using menu engineering matrix"""
        # Define thresholds (these could be configurable)
        avg_popularity = 10.0  # Average orders per period
        avg_margin = 30.0     # Average profit margin percentage
        
        if popularity_score >= avg_popularity and profit_margin >= avg_margin:
            return 'star'        # High popularity, high profit
        elif popularity_score >= avg_popularity and profit_margin < avg_margin:
            return 'plowhorse'   # High popularity, low profit
        elif popularity_score < avg_popularity and profit_margin >= avg_margin:
            return 'puzzle'      # Low popularity, high profit
        else:
            return 'dog'         # Low popularity, low profit
    
    def get_profit_margin_analysis(self, date_from: Optional[datetime] = None,
                                  date_to: Optional[datetime] = None) -> Dict[str, Any]:
        """Detailed profit margin analysis"""
        try:
            if not date_from:
                date_from = datetime.now() - timedelta(days=30)
            if not date_to:
                date_to = datetime.now()
            
            # Get all sales data
            sales_data = self.db.query(
                MenuItem.id,
                MenuItem.name,
                MenuItem.price,
                func.sum(OrderItem.quantity).label('total_quantity'),
                func.sum(OrderItem.subtotal).label('total_revenue')
            ).join(OrderItem).join(Order).filter(
                Order.created_at.between(date_from, date_to),
                Order.status == 'paid'
            ).group_by(MenuItem.id).all()
            
            analysis = []
            
            for item in sales_data:
                # Calculate cost
                cost_result = self.calculate_recipe_cost(item.id)
                item_cost = cost_result['recipe_cost'] if cost_result['success'] else 0.0
                
                quantity = int(item.total_quantity or 0)
                revenue = float(item.total_revenue or 0.0)
                total_cost = item_cost * quantity
                profit = revenue - total_cost
                margin = (profit / revenue) * 100 if revenue > 0 else 0
                
                analysis.append({
                    'menu_item_id': item.id,
                    'menu_item_name': item.name,
                    'selling_price': float(item.price),
                    'recipe_cost': item_cost,
                    'quantity_sold': quantity,
                    'revenue': revenue,
                    'total_cost': total_cost,
                    'profit': profit,
                    'profit_margin': margin
                })
            
            # Sort by margin
            analysis.sort(key=lambda x: x['profit_margin'], reverse=True)
            
            # Calculate summary statistics
            if analysis:
                avg_margin = sum(item['profit_margin'] for item in analysis) / len(analysis)
                total_revenue = sum(item['revenue'] for item in analysis)
                total_profit = sum(item['profit'] for item in analysis)
                overall_margin = (total_profit / total_revenue) * 100 if total_revenue > 0 else 0
            else:
                avg_margin = overall_margin = 0.0
                total_revenue = total_profit = 0.0
            
            return {
                'success': True,
                'period': {
                    'from': date_from.isoformat(),
                    'to': date_to.isoformat()
                },
                'items': analysis,
                'summary': {
                    'total_items': len(analysis),
                    'average_margin': round(avg_margin, 2),
                    'overall_margin': round(overall_margin, 2),
                    'total_revenue': total_revenue,
                    'total_profit': total_profit
                },
                'analyzed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to analyze profit margins'
            }
