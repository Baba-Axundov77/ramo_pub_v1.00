#!/usr/bin/env python3
# web_app.py — Enterprise Restaurant Management System Web Application
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web.app import create_app
from database.connection import init_database
from modules.auth.auth_service import create_default_admin

def main():
    """Start the Enterprise Restaurant Management System Web Application"""
    
    print("Starting Enterprise Restaurant Management System...")
    print("=" * 60)
    
    # Initialize database
    print("Initializing database...")
    ok, msg = init_database()
    if not ok:
        print(f"Database initialization failed: {msg}")
        sys.exit(1)
    
    print("Database initialized successfully")
    
    # Create default admin user
    print("Creating default admin user...")
    from database.connection import get_db
    db = get_db()
    create_default_admin(db)
    print("Default admin user created/verified")
    
    # Create Flask app
    print("Creating Flask application...")
    app = create_app()
    
    # Load advanced API routes
    print("Loading API routes...")
    try:
        from web.routes.advanced_api import advanced_bp
        app.register_blueprint(advanced_bp)
        print("Advanced API routes loaded")
    except ImportError as e:
        print(f"Warning: Could not load advanced API routes: {e}")
    
    print("=" * 60)
    print("Enterprise Restaurant Management System Ready!")
    print("Access at: http://localhost:5000")
    print("Login: admin / admin123")
    print("Dashboard: http://localhost:5000/dashboard-enterprise")
    print("API: http://localhost:5000/api/v2/*")
    print("=" * 60)
    
    # Start Flask application
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=False
        )
    except KeyboardInterrupt:
        print("\nShutting down Enterprise Restaurant Management System...")
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
