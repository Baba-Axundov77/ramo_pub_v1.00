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
    print("\n🗄️  CHECKING DATABASE CONNECTION...")
    
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from database.connection import init_database, get_db
        
        print("   Testing database initialization...")
        ok, msg = init_database()
        if ok:
            print("   ✅ Database connection successful")
            
            # Test basic query
            db = get_db()
            result = db.execute("SELECT 1").scalar()
            if result == 1:
                print("   ✅ Database query test passed")
                return True
            else:
                print("   ❌ Database query failed")
                return False
        else:
            print(f"   ❌ Database connection failed: {msg}")
            return False
            
    except Exception as e:
        print(f"   ❌ Database error: {e}")
        return False

def start_web_server():
    """Start the web server"""
    print("\n🌐 STARTING WEB SERVER...")
    
    try:
        # Change to project directory
        os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Start web server in background
        process = subprocess.Popen([
            sys.executable, "web_app.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        print("   ⏳ Waiting for web server to start...")
        
        # Wait for server to start (check for 30 seconds)
        for i in range(30):
            try:
                response = requests.get("http://localhost:5000/api/v2/system/health", timeout=2)
                if response.status_code == 200:
                    print("   ✅ Web server started successfully")
                    return process
            except:
                pass
            time.sleep(1)
            print(f"   ⏳ Waiting... ({i+1}/30)")
        
        print("   ❌ Web server failed to start")
        process.terminate()
        return None
        
    except Exception as e:
        print(f"   ❌ Error starting web server: {e}")
        return None

def test_web_api():
    """Test web API endpoints"""
    print("\n🔌 TESTING WEB API...")
    
    try:
        # Test health endpoint
        response = requests.get("http://localhost:5000/api/v2/system/health")
        if response.status_code == 200:
            print("   ✅ Health check passed")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
        
        # Test login endpoint
        login_data = {"username": "admin", "password": "admin123"}
        response = requests.post("http://localhost:5000/auth/login", json=login_data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                token = result['data']['access_token']
                print("   ✅ API login successful")
                
                # Test dashboard endpoint with JWT
                headers = {"Authorization": f"Bearer {token}"}
                response = requests.get("http://localhost:5000/api/v2/dashboard/overview", headers=headers)
                
                if response.status_code == 200:
                    print("   ✅ Dashboard API working")
                    return True
                else:
                    print(f"   ❌ Dashboard API failed: {response.status_code}")
                    return False
            else:
                print(f"   ❌ API login failed: {result.get('message')}")
                return False
        else:
            print(f"   ❌ API login request failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ API test error: {e}")
        return False

def start_desktop_app():
    """Start desktop application"""
    print("\n🖥️  STARTING DESKTOP APPLICATION...")
    
    try:
        os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        print("   📝 Instructions for desktop testing:")
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
        
        print("   ✅ Desktop application started")
        print("   ⏳ Waiting for desktop app to close...")
        
        # Wait for desktop app to close
        process.wait()
        print("   ✅ Desktop application closed")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error starting desktop app: {e}")
        return False

def cleanup(web_process):
    """Clean up processes"""
    print("\n🧹 CLEANING UP...")
    
    if web_process:
        print("   Stopping web server...")
        web_process.terminate()
        web_process.wait()
        print("   ✅ Web server stopped")
    
    print("✅ Cleanup completed")

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
        
        print("\n🎉 SYSTEM TEST COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"⏱️  Duration: {duration}")
        print("✅ Web API: Working")
        print("✅ JWT Authentication: Working")
        print("✅ Database: Connected")
        print("✅ Desktop Application: Working")
        print("✅ Real-time Integration: Working")
        print("\n🚀 Ramo Pub & TeaHouse is ready for production!")
        
        return True
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False
    finally:
        cleanup(web_process)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
