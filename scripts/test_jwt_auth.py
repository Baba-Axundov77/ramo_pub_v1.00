# test_jwt_auth.py — JWT Authentication Testing Script
import requests
import json
import time

# Test configuration
BASE_URL = "http://localhost:5000"
LOGIN_URL = f"{BASE_URL}/auth/login"
API_URL = f"{BASE_URL}/api/v2"

def test_jwt_authentication():
    """Test JWT authentication flow"""
    print("🔐 JWT Authentication Test Suite")
    print("=" * 50)
    
    # 1. Test API Login (JWT)
    print("\n1. Testing API Login with JWT...")
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(LOGIN_URL, json=login_data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            login_result = response.json()
            if login_result.get('success'):
                access_token = login_result['data']['access_token']
                refresh_token = login_result['data']['refresh_token']
                user_info = login_result['data']['user']
                
                print(f"✅ Login successful!")
                print(f"   User: {user_info['username']} ({user_info['role']})")
                print(f"   Token Type: {login_result['data']['token_type']}")
                print(f"   Expires In: {login_result['data']['expires_in']} seconds")
                
                # 2. Test API with JWT Token
                print("\n2. Testing API access with JWT Token...")
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
                
                # Test order history endpoint
                orders_response = requests.get(f"{API_URL}/orders/history", headers=headers)
                print(f"Orders API Status: {orders_response.status_code}")
                
                if orders_response.status_code == 200:
                    print("✅ API access successful with JWT!")
                    orders_data = orders_response.json()
                    print(f"   Response contains: {list(orders_data.keys())}")
                else:
                    print("❌ API access failed!")
                    print(f"   Error: {orders_response.text}")
                
                # 3. Test Token Refresh
                print("\n3. Testing Token Refresh...")
                refresh_data = {"refresh_token": refresh_token}
                refresh_response = requests.post(f"{BASE_URL}/auth/api/refresh", json=refresh_data)
                
                if refresh_response.status_code == 200:
                    refresh_result = refresh_response.json()
                    new_token = refresh_result['data']['access_token']
                    print("✅ Token refresh successful!")
                    print(f"   New token received (length: {len(new_token)})")
                else:
                    print("❌ Token refresh failed!")
                    print(f"   Error: {refresh_response.text}")
                
                # 4. Test Invalid Token
                print("\n4. Testing Invalid Token...")
                invalid_headers = {"Authorization": "Bearer invalid_token_123"}
                invalid_response = requests.get(f"{API_URL}/orders/history", headers=invalid_headers)
                
                if invalid_response.status_code == 401:
                    print("✅ Invalid token properly rejected!")
                    error_data = invalid_response.json()
                    print(f"   Error Code: {error_data.get('error_code')}")
                else:
                    print("❌ Security issue - invalid token accepted!")
                
            else:
                print(f"❌ Login failed: {login_result.get('message')}")
        else:
            print(f"❌ Login request failed: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - make sure the server is running!")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

def test_web_login():
    """Test traditional web login (session-based)"""
    print("\n5. Testing Web Login (Session-based)...")
    
    # Use session for web login
    session = requests.Session()
    
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = session.post(LOGIN_URL, data=login_data)  # Form data, not JSON
        
        if response.status_code == 302:  # Redirect after successful login
            print("✅ Web login successful (redirect to dashboard)!")
        else:
            print(f"❌ Web login failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Web login error: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting JWT Authentication Tests...")
    print("Make sure the web server is running on http://localhost:5000")
    
    test_jwt_authentication()
    test_web_login()
    
    print("\n" + "=" * 50)
    print("🎯 Test Suite Complete!")
    print("\nNext Steps:")
    print("1. Verify JWT tokens work for all API endpoints")
    print("2. Test role-based access control")
    print("3. Implement token blacklisting for logout")
    print("4. Add rate limiting to prevent brute force attacks")
