#!/usr/bin/env python3
"""
src/main.py - Docker Entry Point for Ramo Pub
Production-ready Flask application entry point
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

def main():
    """Main entry point for Docker/Production deployment"""
    # Import and run Flask app
    from src.web.app import create_app
    
    # Create Flask application
    app = create_app()
    
    # Run with production server
    if __name__ == "__main__":
        # Use Gunicorn in production, but fallback to Flask dev server
        port = int(os.environ.get('PORT', 5000))
        host = os.environ.get('HOST', '0.0.0.0')
        debug = os.environ.get('DEBUG', 'False').lower() == 'true'
        
        print(f"Starting Ramo Pub Web Server on {host}:{port}")
        print(f"Debug mode: {debug}")
        
        if not debug:
            # Production mode - would use Gunicorn in real deployment
            app.run(host=host, port=port, debug=False)
        else:
            # Development mode
            app.run(host=host, port=port, debug=True)

if __name__ == "__main__":
    main()
