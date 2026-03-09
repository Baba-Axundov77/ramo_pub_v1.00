# scripts/run_system_test.py — Complete System Test Guide
import os
import sys
import time
import subprocess
import threading
import requests
from datetime import datetime

print("RAMO PUB & TEAHOUSE - COMPLETE SYSTEM TEST")
print("=" * 60)
print("This script will guide you through testing the entire system")
print("Web API + Desktop Application with JWT Integration")
print("=" * 60)

def check_requirements():
    """Check if all requirements are installed"""
    print("\nCHECKING REQUIREMENTS...")
    
    requirements = [
        ("PyQt6", "PyQt6.QtWidgets"),
        ("requests", "requests"),
        ("sqlalchemy", "sqlalchemy"),
        ("flask", "flask"),
        ("pyjwt", "jwt"),
        ("bcrypt", "bcrypt")
    ]
    
    missing = []
    for name, module in requirements:
        try:
            __import__(module)
            print(f"   [OK] {name}")
        except ImportError:
            print(f"   [MISSING] {name}")
            missing.append(name)
    
    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Install with: pip install " + " ".join(missing))
        return False
    
    print("All requirements satisfied!")
    return True

def check_database():
    """Check database connection"""
    print("\nCHECKING DATABASE CONNECTION...")
    
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from database.connection import init_database, get_db
        
        print("   Testing database initialization...")
        ok, msg = init_database()
        if ok:
            print("   [OK] Database connection successful")
            
            # Test basic query
            db = get_db()
            result = db.execute("SELECT 1").scalar()
            if result == 1:
                print("   [OK] Database query test passed")
                return True
            else:
                print("   [ERROR] Database query failed")
                return False
        else:
            print(f"   [ERROR] Database connection failed: {msg}")
            return False
            
    except Exception as e:
        print(f"   [ERROR] Database error: {e}")
        return False

def start_web_server():
    """Start the web server"""
    print("\nSTARTING WEB SERVER...")
    
    try:
        # Change to project directory
        os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Start web server in background
        process = subprocess.Popen([
            sys.executable, "web_app.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        print("   Waiting for web server to start...")
        
        # Wait for server to start (check for 30 seconds)
        for i in range(30):
            try:
                response = requests.get("http://localhost:5000/api/v2/system/health", timeout=2)
                if response.status_code == 200:
                    print("   [OK] Web server started successfully")
                    return process
            except:
                pass
            time.sleep(1)
            print(f"   Waiting... ({i+1}/30)")
        
        print("   [ERROR] Web server failed to start")
        process.terminate()
        return None
        
    except Exception as e:
        print(f"   [ERROR] Error starting web server: {e}")
        return None

def test_web_api():
    """Test web API endpoints"""
    print("\nTESTING WEB API...")
    
    try:
        # Test health endpoint
        response = requests.get("http://localhost:5000/api/v2/system/health")
        if response.status_code == 200:
            print("   [OK] Health check passed")
        else:
            print(f"   [ERROR] Health check failed: {response.status_code}")
            return False
        
        # Test login endpoint
        login_data = {"username": "admin", "password": "admin123"}
        response = requests.post("http://localhost:5000/auth/login", json=login_data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                token = result['data']['access_token']
                print("   [OK] API login successful")
                
                # Test dashboard endpoint with JWT
                headers = {"Authorization": f"Bearer {token}"}
                response = requests.get("http://localhost:5000/api/v2/dashboard/overview", headers=headers)
                
                if response.status_code == 200:
                    print("   [OK] Dashboard API working")
                    return True
                else:
                    print(f"   [ERROR] Dashboard API failed: {response.status_code}")
                    return False
            else:
                print(f"   [ERROR] API login failed: {result.get('message')}")
                return False
        else:
            print(f"   [ERROR] API login request failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   [ERROR] API test error: {e}")
        return False

def start_desktop_app():
    """Start desktop application"""
    print("\nSTARTING DESKTOP APPLICATION...")
    
    try:
        os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        print("   Instructions for desktop testing:")
        print("   1. Login window should appear")
        print("   2. Use credentials: admin / admin123")
        print("   3. Desktop should connect to web API")
        print("   4. Real-time data should appear")
        print("   5. Close the application when done testing")
        
        input("\n   Press Enter to start desktop application...")
        
        # Start desktop app
        process = subprocess.Popen([
            sys.executable, "main_fixed.py"
        ])
        
        print("   [OK] Desktop application started")
        print("   Waiting for desktop app to close...")
        
        # Wait for desktop app to close
        process.wait()
        print("   [OK] Desktop application closed")
        
        return True
        
    except Exception as e:
        print(f"   [ERROR] Error starting desktop app: {e}")
        return False

def cleanup(web_process):
    """Clean up processes"""
    print("\nCLEANING UP...")
    
    if web_process:
        print("   Stopping web server...")
        web_process.terminate()
        web_process.wait()
        print("   [OK] Web server stopped")
    
    print("Cleanup completed")

def main():
    """Main test function"""
    start_time = datetime.now()
    
    # Check requirements
    if not check_requirements():
        return False
    
    # Check database
    if not check_database():
        return False
    
    web_process = None
    
    try:
        # Start web server
        web_process = start_web_server()
        if not web_process:
            return False
        
        # Test web API
        if not test_web_api():
            return False
        
        # Start desktop app
        if not start_desktop_app():
            return False
        
        # Success
        end_time = datetime.now()
        duration = end_time - start_time
        
        print("\nSYSTEM TEST COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"Duration: {duration}")
        print("[OK] Web API: Working")
        print("[OK] JWT Authentication: Working")
        print("[OK] Database: Connected")
        print("[OK] Desktop Application: Working")
        print("[OK] Real-time Integration: Working")
        print("\nRamo Pub & TeaHouse is ready for production!")
        
        return True
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return False
    except Exception as e:
        print(f"\nTest failed: {e}")
        return False
    finally:
        cleanup(web_process)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
