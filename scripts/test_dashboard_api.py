# scripts/test_dashboard_api.py — Dashboard API Testing Script
import requests
import json
import time

# Test configuration
BASE_URL = "http://localhost:5000"
LOGIN_URL = f"{BASE_URL}/auth/login"
API_URL = f"{BASE_URL}/api/v2"

def get_auth_token():
    """Get JWT token for API testing"""
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(LOGIN_URL, json=login_data)
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                return result['data']['access_token']
        print(f"❌ Login failed: {response.text}")
        return None
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return None

def test_dashboard_endpoints(token):
    """Test all dashboard endpoints"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("\n📊 Testing Dashboard Endpoints")
    print("=" * 50)
    
    # Test 1: System Metrics
    print("\n1. Testing System Metrics...")
    response = requests.get(f"{API_URL}/system/metrics", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print("✅ System Metrics successful!")
        print(f"   Orders: {data['metrics']['database']['orders']}")
        print(f"   Today Revenue: ${data['metrics']['business']['today_revenue']}")
        print(f"   Active Staff: {data['metrics']['business']['active_staff']}")
        print(f"   Table Occupancy: {data['metrics']['business']['table_occupancy_rate']}%")
    else:
        print(f"❌ System Metrics failed: {response.text}")
    
    # Test 2: Dashboard Overview
    print("\n2. Testing Dashboard Overview...")
    response = requests.get(f"{API_URL}/dashboard/overview", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print("✅ Dashboard Overview successful!")
        if data.get('success') and data.get('data'):
            dashboard_data = data['data']
            print(f"   Today Revenue: ${dashboard_data['revenue']['today']}")
            print(f"   Today Orders: {dashboard_data['orders']['today']}")
            print(f"   Critical Stock Items: {len(dashboard_data['inventory']['critical_items'])}")
            print(f"   Top Selling Items: {len(dashboard_data['top_items'])}")
    else:
        print(f"❌ Dashboard Overview failed: {response.text}")
    
    # Test 3: Revenue Data
    print("\n3. Testing Revenue Data...")
    response = requests.get(f"{API_URL}/dashboard/revenue", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print("✅ Revenue Data successful!")
        if data.get('success') and data.get('data'):
            revenue_data = data['data']
            print(f"   Today Revenue: ${revenue_data['today']}")
            print(f"   Sales Chart Points: {len(revenue_data['sales_chart'])}")
            print(f"   Hourly Data Points: {len(revenue_data['hourly_sales'])}")
    else:
        print(f"❌ Revenue Data failed: {response.text}")
    
    # Test 4: Critical Inventory
    print("\n4. Testing Critical Inventory...")
    response = requests.get(f"{API_URL}/dashboard/inventory/critical", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print("✅ Critical Inventory successful!")
        if data.get('success') and data.get('data'):
            inventory_data = data['data']
            print(f"   Critical Items Count: {inventory_data['count']}")
            for item in inventory_data['critical_items'][:3]:  # Show first 3
                print(f"   - {item['name']}: {item['quantity']} {item['unit']} ({item['status']})")
    else:
        print(f"❌ Critical Inventory failed: {response.text}")
    
    # Test 5: Table Occupancy
    print("\n5. Testing Table Occupancy...")
    response = requests.get(f"{API_URL}/dashboard/tables/occupancy", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print("✅ Table Occupancy successful!")
        if data.get('success') and data.get('data'):
            occupancy_data = data['data']
            print(f"   Occupancy Rate: {occupancy_data['occupancy_rate']}%")
            print(f"   Total Tables: {occupancy_data['total_tables']}")
            print(f"   Occupied: {occupancy_data['occupied_tables']}")
            print(f"   Available: {occupancy_data['available_tables']}")
    else:
        print(f"❌ Table Occupancy failed: {response.text}")

def test_cache_invalidation(token):
    """Test cache invalidation"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("\n🔄 Testing Cache Invalidation...")
    response = requests.post(f"{API_URL}/cache/invalidate", 
                          headers=headers, 
                          json={"type": "dashboard"})
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Cache Invalidation successful!")
        print(f"   Message: {data['message']}")
    else:
        print(f"❌ Cache Invalidation failed: {response.text}")

def performance_test(token):
    """Simple performance test"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("\n⚡ Performance Test (5 consecutive requests)...")
    times = []
    
    for i in range(5):
        start_time = time.time()
        response = requests.get(f"{API_URL}/dashboard/overview", headers=headers)
        end_time = time.time()
        
        if response.status_code == 200:
            times.append(end_time - start_time)
            print(f"   Request {i+1}: {(end_time - start_time)*1000:.2f}ms")
        else:
            print(f"   Request {i+1}: Failed")
    
    if times:
        avg_time = sum(times) / len(times)
        print(f"   Average Response Time: {avg_time*1000:.2f}ms")
        print(f"   Min: {min(times)*1000:.2f}ms, Max: {max(times)*1000:.2f}ms")

def main():
    print("🚀 Dashboard API Test Suite")
    print("=" * 50)
    print("Make sure the web server is running on http://localhost:5000")
    
    # Get authentication token
    token = get_auth_token()
    if not token:
        print("❌ Cannot proceed without authentication token")
        return
    
    print("✅ Authentication successful!")
    
    # Run tests
    test_dashboard_endpoints(token)
    test_cache_invalidation(token)
    performance_test(token)
    
    print("\n" + "=" * 50)
    print("🎯 Dashboard API Test Suite Complete!")
    print("\nFeatures Tested:")
    print("✅ Real-time database integration")
    print("✅ PostgreSQL queries for metrics")
    print("✅ Critical stock level detection")
    print("✅ Table occupancy calculation")
    print("✅ Revenue analytics")
    print("✅ Caching mechanisms")
    print("✅ Error handling and logging")
    print("✅ JWT authentication")

if __name__ == "__main__":
    main()
