# Ramo Pub & TeaHouse - Management System

Python 3.10+ | PyQt6 Desktop | Flask Web Panel | PostgreSQL

## Quick Start

1. Install dependencies:
   pip install -r requirements.txt

2. Configure database:
   copy .env.example .env
   (edit DB_PASSWORD in .env)

3. Run desktop app:
   python main.py

4. Run web panel (separate terminal):
   python -m web.app
   Open: http://localhost:5000

Default login: admin / <RAMO_DEFAULT_ADMIN_PASSWORD or generated at first startup>

## Modules

- Login & Auth (3 roles: Admin, Waiter, Cashier)
- Tables (image support, status management)
- Orders (add/remove items, status tracking)
- Menu (categories, images, CRUD)
- POS / Cashier (payment, discount codes)
- Inventory (stock alerts, add/remove)
- Reservations (conflict detection)
- Staff (shifts, role management)
- Reports (daily/monthly/yearly charts)
- Loyalty (customer points, tiers, discounts)
- Receipt (thermal printer, PDF, screen preview)
- Web Panel (Flask: all modules via browser)

## Install Required Packages

pip install SQLAlchemy psycopg2-binary python-dotenv PyQt6 matplotlib Pillow Flask reportlab

## Web Panel Routes

http://localhost:5000           - Dashboard
http://localhost:5000/tables    - Tables
http://localhost:5000/orders    - Orders
http://localhost:5000/menu      - Menu
http://localhost:5000/reports   - Reports
http://localhost:5000/reservations - Reservations
http://localhost:5000/loyalty   - Loyalty & Customers
http://localhost:5000/inventory - Inventory

## Loyalty System

- 1 AZN spent = 1 point earned
- 100 points = 1 AZN discount
- Tiers: Bronze (0-499) | Silver (500-1499) | Gold (1500-4999) | Platinum (5000+)
- Birthday bonus: 50 points
- Welcome bonus: 20 points

## Database Tables

users, tables, menu_categories, menu_items, orders, order_items,
payments, inventory_items, shifts, customers, loyalty_transactions,
reservations, discounts, receipt_logs
