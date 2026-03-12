# scripts/simple_test.py — Simple System Test
import os
import sys
import time
import subprocess
import requests

print("RAMO PUB - SIMPLE SYSTEM TEST")
print("=" * 40)

def test_database():
    """Test database connection"""
    print("\n1. Testing Database...")
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from src.core.database.connection import init_database, get_db
        from sqlalchemy import text
        
        ok, msg = init_database()
        if ok:
            print("   [OK] Database connected")
            
            # Simple test
            db = get_db()
            result = db.execute(text("SELECT 1")).scalar()
            print("   [OK] Database query works")
            return True
        else:
            print(f"   [ERROR] {msg}")
            return False
    except Exception as e:
        print(f"   [ERROR] {e}")
        return False

def start_web_server():
    """Start web server"""
    print("\n2. Starting Web Server...")
    try:
        os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Start web server
        process = subprocess.Popen([
            sys.executable, "web_app.py"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait for startup
        print("   Waiting for server...")
        for i in range(15):
            try:
                response = requests.get("http://localhost:5000/api/v2/system/health", timeout=1)
                if response.status_code == 200:
                    print("   [OK] Web server running")
                    return process
            except:
                pass
            time.sleep(1)
        
        print("   [ERROR] Web server failed")
        process.terminate()
        return None
    except Exception as e:
        print(f"   [ERROR] {e}")
        return None

def test_api():
    """Test API endpoints"""
    print("\n3. Testing API...")
    try:
        # Health check
        response = requests.get("http://localhost:5000/api/v2/system/health")
        if response.status_code == 200:
            print("   [OK] Health check")
        else:
            print(f"   [ERROR] Health: {response.status_code}")
            return False
        
        # Login
        login_data = {"username": "admin", "password": "admin123"}
        response = requests.post("http://localhost:5000/auth/login", json=login_data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                token = result['data']['access_token']
                print("   [OK] Login successful")
                
                # Test dashboard
                headers = {"Authorization": f"Bearer {token}"}
                response = requests.get("http://localhost:5000/api/v2/dashboard/overview", headers=headers)
                
                if response.status_code == 200:
                    print("   [OK] Dashboard API")
                    return True
                else:
                    print(f"   [ERROR] Dashboard: {response.status_code}")
                    return False
            else:
                print(f"   [ERROR] Login: {result.get('message')}")
                return False
        else:
            print(f"   [ERROR] Login request: {response.status_code}")
            return False
    except Exception as e:
        print(f"   [ERROR] {e}")
        return False

def main():
    """Main test"""
    print("Starting simple system test...")
    
    # Test database
    if not test_database():
        print("\nDatabase test failed!")
        return False
    
    # Start web server
    web_process = start_web_server()
    if not web_process:
        print("\nWeb server failed!")
        return False
    
    try:
        # Test API
        if not test_api():
            print("\nAPI test failed!")
            return False
        
        print("\n" + "=" * 40)
        print("SUCCESS! All tests passed!")
        print("\nNow you can:")
        print("1. Open browser: http://localhost:5000")
        print("2. Run desktop: python main_fixed.py")
        print("3. Test full integration")
        
        return True
        
    finally:
        # Cleanup
        if web_process:
            web_process.terminate()
            print("\nWeb server stopped")

if __name__ == "__main__":
    success = main()
    input("\nPress Enter to exit...")
    sys.exit(0 if success else 1)
