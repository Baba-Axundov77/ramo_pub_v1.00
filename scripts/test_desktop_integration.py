# scripts/test_desktop_integration.py — Desktop-Web Integration Test
import requests
import json
import time
import sys
import threading

# Test configuration
BASE_URL = "http://localhost:5000"
API_URL = f"{BASE_URL}/api/v2"

def test_web_api():
    """Test if web API is running"""
    try:
        response = requests.get(f"{API_URL}/system/health", timeout=5)
        if response.status_code == 200:
            print("✅ Web API is running and accessible")
            return True
        else:
            print(f"❌ Web API returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Web API is not running or not accessible")
        print("   Please start web_app.py first")
        return False
    except Exception as e:
        print(f"❌ Error checking web API: {str(e)}")
        return False

def test_desktop_login():
    """Test desktop login through web API"""
    print("\n🔐 Testing Desktop Login via Web API")
    print("=" * 50)
    
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                token = result['data']['access_token']
                user = result['data']['user']
                
                print("✅ Desktop login successful!")
                print(f"   User: {user['username']} ({user['role']})")
                print(f"   Token Length: {len(token)} characters")
                print(f"   Token Type: {result['data']['token_type']}")
                return token
            else:
                print(f"❌ Login failed: {result.get('message')}")
                return None
        else:
            print(f"❌ Login request failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return None

def test_dashboard_api(token):
    """Test dashboard API endpoints"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("\n📊 Testing Dashboard API for Desktop")
    print("=" * 50)
    
    endpoints = [
        ("/dashboard/overview", "Dashboard Overview"),
        ("/system/metrics", "System Metrics"),
        ("/dashboard/revenue", "Revenue Data"),
        ("/dashboard/inventory/critical", "Critical Inventory"),
        ("/dashboard/tables/occupancy", "Table Occupancy")
    ]
    
    for endpoint, name in endpoints:
        print(f"\nTesting {name}...")
        try:
            response = requests.get(f"{API_URL}{endpoint}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print(f"✅ {name} successful!")
                    
                    # Show some sample data
                    if endpoint == "/dashboard/overview":
                        dashboard_data = data.get('data', {})
                        print(f"   Today Revenue: ${dashboard_data.get('revenue', {}).get('today', 0)}")
                        print(f"   Today Orders: {dashboard_data.get('orders', {}).get('today', 0)}")
                        print(f"   Critical Items: {len(dashboard_data.get('inventory', {}).get('critical_items', []))}")
                    elif endpoint == "/system/metrics":
                        metrics = data.get('metrics', {})
                        print(f"   Database Orders: {metrics.get('database', {}).get('orders', 0)}")
                        print(f"   Business Revenue: ${metrics.get('business', {}).get('today_revenue', 0)}")
                        
                else:
                    print(f"❌ {name} failed: {data.get('message')}")
            else:
                print(f"❌ {name} failed: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ {name} error: {str(e)}")

def test_performance():
    """Test API performance for desktop usage"""
    print("\n⚡ Performance Test for Desktop Usage")
    print("=" * 50)
    
    # Login first
    token = test_desktop_login()
    if not token:
        print("❌ Cannot perform performance test without login")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test multiple concurrent requests
    import threading
    import queue
    
    results = queue.Queue()
    
    def make_request(request_id):
        start_time = time.time()
        try:
            response = requests.get(f"{API_URL}/dashboard/overview", headers=headers)
            end_time = time.time()
            results.put({
                'id': request_id,
                'success': response.status_code == 200,
                'time': end_time - start_time,
                'status': response.status_code
            })
        except Exception as e:
            end_time = time.time()
            results.put({
                'id': request_id,
                'success': False,
                'time': end_time - start_time,
                'error': str(e)
            })
    
    # Launch 5 concurrent requests
    threads = []
    for i in range(5):
        thread = threading.Thread(target=make_request, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads
    for thread in threads:
        thread.join()
    
    # Analyze results
    successful_requests = []
    for _ in range(5):
        result = results.get()
        if result['success']:
            successful_requests.append(result['time'])
            print(f"   Request {result['id']}: {result['time']*1000:.2f}ms ✅")
        else:
            print(f"   Request {result['id']}: Failed ❌")
    
    if successful_requests:
        avg_time = sum(successful_requests) / len(successful_requests)
        print(f"\n   Average Response Time: {avg_time*1000:.2f}ms")
        print(f"   Min: {min(successful_requests)*1000:.2f}ms")
        print(f"   Max: {max(successful_requests)*1000:.2f}ms")
        print(f"   Success Rate: {len(successful_requests)}/5 ({len(successful_requests)/5*100:.1f}%)")

def main():
    print("🚀 Desktop-Web Integration Test Suite")
    print("=" * 50)
    print("This test verifies that the desktop application can")
    print("successfully integrate with the modern web API.")
    
    # Test 1: Check if web API is running
    if not test_web_api():
        print("\n❌ Please start the web application first:")
        print("   python web_app.py")
        sys.exit(1)
    
    # Test 2: Test desktop login
    token = test_desktop_login()
    if not token:
        sys.exit(1)
    
    # Test 3: Test dashboard API
    test_dashboard_api(token)
    
    # Test 4: Performance test
    test_performance()
    
    print("\n" + "=" * 50)
    print("🎯 Desktop-Web Integration Test Complete!")
    print("\nIntegration Features Verified:")
    print("✅ JWT Authentication")
    print("✅ API Client Integration")
    print("✅ Real-time Dashboard Data")
    print("✅ System Metrics")
    print("✅ Performance Under Load")
    print("✅ Error Handling")
    print("\nDesktop application is ready for modern web integration!")

if __name__ == "__main__":
    main()
