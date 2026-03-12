# Performance Optimization - Database Indexes
# This file contains optimized indexes for the restaurant management system

from sqlalchemy import text

# Performance indexes for better query performance
PERFORMANCE_INDEXES = [
    # Orders table indexes
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_created_at_status ON orders(created_at, status);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_table_status_created_at ON orders(table_id, status, created_at);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_customer_status ON orders(customer_id, status);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_waiter_created_at ON orders(waiter_id, created_at);",
    
    # Payments table indexes
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_created_at_method ON payments(created_at, method);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_order_id ON payments(order_id);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_status_created_at ON payments(status, created_at);",
    
    # Order Items table indexes
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_order_items_menu_item_id ON order_items(menu_item_id);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_order_items_status ON order_items(status);",
    
    # Menu Items table indexes
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_menu_items_category_id ON menu_items(category_id);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_menu_items_is_active ON menu_items(is_active);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_menu_items_category_active ON menu_items(category_id, is_active);",
    
    # Customers table indexes
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customers_phone ON customers(phone);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customers_is_active ON customers(is_active);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customers_tier_id ON customers(tier_id);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customers_created_at ON customers(created_at);",
    
    # Tables table indexes
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tables_status ON tables(status);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tables_location ON tables(location);",
    
    # Reservations table indexes
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_reservations_date_table ON reservations(date, table_id);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_reservations_date_cancelled ON reservations(date, is_cancelled);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_reservations_customer_id ON reservations(customer_id);",
    
    # Inventory Items table indexes
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_items_name ON inventory_items(name);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_items_is_active ON inventory_items(is_active);",
    
    # Menu Item Recipes table indexes
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_menu_item_recipes_menu_item ON menu_item_recipes(menu_item_id);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_menu_item_recipes_inventory_item ON menu_item_recipes(inventory_item_id);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_menu_item_recipes_active_dates ON menu_item_recipes(is_active, valid_from, valid_until);",
    
    # Staff Performance table indexes
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_staff_performance_staff_date ON staff_performance(staff_id, performance_date);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_staff_performance_date_type ON staff_performance(performance_date, metric_type);",
    
    # Staff Schedule table indexes
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_staff_schedule_staff_date ON staff_schedules(staff_id, shift_date);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_staff_schedule_date_type ON staff_schedules(shift_date, shift_type);",
    
    # Loyalty Transactions table indexes
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_loyalty_transactions_customer_id ON loyalty_transactions(customer_id);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_loyalty_transactions_created_at ON loyalty_transactions(created_at);",
    
    # Dashboard Widgets table indexes
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dashboard_widgets_dashboard ON dashboard_widgets(dashboard_name);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dashboard_widgets_type ON dashboard_widgets(widget_type);",
]

def create_performance_indexes(db):
    """Create performance indexes for better query performance"""
    try:
        # Use regular CREATE INDEX instead of CONCURRENTLY for simplicity
        simple_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_orders_created_at_status ON orders(created_at, status);",
            "CREATE INDEX IF NOT EXISTS idx_orders_table_status_created_at ON orders(table_id, status, created_at);",
            "CREATE INDEX IF NOT EXISTS idx_orders_customer_status ON orders(customer_id, status);",
            "CREATE INDEX IF NOT EXISTS idx_orders_waiter_created_at ON orders(waiter_id, created_at);",
            "CREATE INDEX IF NOT EXISTS idx_payments_created_at_method ON payments(created_at, method);",
            "CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id);",
            "CREATE INDEX IF NOT EXISTS idx_payments_status_created_at ON payments(status, created_at);",
            "CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);",
            "CREATE INDEX IF NOT EXISTS idx_order_items_menu_item_id ON order_items(menu_item_id);",
            "CREATE INDEX IF NOT EXISTS idx_order_items_status ON order_items(status);",
            "CREATE INDEX IF NOT EXISTS idx_menu_items_category_id ON menu_items(category_id);",
            "CREATE INDEX IF NOT EXISTS idx_menu_items_is_active ON menu_items(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_menu_items_category_active ON menu_items(category_id, is_active);",
            "CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);",
            "CREATE INDEX IF NOT EXISTS idx_customers_is_active ON customers(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_customers_tier_id ON customers(tier_id);",
            "CREATE INDEX IF NOT EXISTS idx_customers_created_at ON customers(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_tables_status ON tables(status);",
            "CREATE INDEX IF NOT EXISTS idx_tables_location ON tables(location);",
            "CREATE INDEX IF NOT EXISTS idx_reservations_date_table ON reservations(date, table_id);",
            "CREATE INDEX IF NOT EXISTS idx_reservations_date_cancelled ON reservations(date, is_cancelled);",
            "CREATE INDEX IF NOT EXISTS idx_reservations_customer_id ON reservations(customer_id);",
            "CREATE INDEX IF NOT EXISTS idx_inventory_items_name ON inventory_items(name);",
            "CREATE INDEX IF NOT EXISTS idx_inventory_items_is_active ON inventory_items(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_menu_item_recipes_menu_item ON menu_item_recipes(menu_item_id);",
            "CREATE INDEX IF NOT EXISTS idx_menu_item_recipes_inventory_item ON menu_item_recipes(inventory_item_id);",
            "CREATE INDEX IF NOT EXISTS idx_menu_item_recipes_active_dates ON menu_item_recipes(is_active, valid_from, valid_until);",
            "CREATE INDEX IF NOT EXISTS idx_staff_performance_staff_date ON staff_performance(staff_id, performance_date);",
            "CREATE INDEX IF NOT EXISTS idx_staff_performance_date_type ON staff_performance(performance_date, metric_type);",
            "CREATE INDEX IF NOT EXISTS idx_staff_schedule_staff_date ON staff_schedules(staff_id, shift_date);",
            "CREATE INDEX IF NOT EXISTS idx_staff_schedule_date_type ON staff_schedules(shift_date, shift_type);",
            "CREATE INDEX IF NOT EXISTS idx_loyalty_transactions_customer_id ON loyalty_transactions(customer_id);",
            "CREATE INDEX IF NOT EXISTS idx_loyalty_transactions_created_at ON loyalty_transactions(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_dashboard_widgets_dashboard ON dashboard_widgets(dashboard_name);",
            "CREATE INDEX IF NOT EXISTS idx_dashboard_widgets_type ON dashboard_widgets(widget_type);",
        ]
        
        for index_sql in simple_indexes:
            print(f"Creating index: {index_sql[:50]}...")
            db.execute(text(index_sql))
        db.commit()
        print("[OK] All performance indexes created successfully!")
        return True, "Performance indexes created"
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error creating indexes: {e}")
        return False, f"Error creating indexes: {e}"

def analyze_query_performance(db, query_sql):
    """Analyze query performance using EXPLAIN ANALYZE"""
    try:
        explain_sql = f"EXPLAIN (ANALYZE, BUFFERS) {query_sql}"
        result = db.execute(text(explain_sql)).fetchall()
        return result
    except Exception as e:
        return f"Error analyzing query: {e}"
