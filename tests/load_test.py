"""
Load Testing Script - Validate performance under concurrent load
Tests WebSocket connections, API endpoints, and database performance
"""

import asyncio
import aiohttp
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict
import json

class LoadTester:
    """Load testing for Ramo Pub application"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.results = []
        
    async def test_api_endpoints(self, concurrent_users: int = 50, duration: int = 60):
        """Test API endpoints under load"""
        print(f"Starting API load test: {concurrent_users} users for {duration}s")
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(concurrent_users):
                task = asyncio.create_task(
                    self._simulate_user_session(session, i, duration)
                )
                tasks.append(task)
                
            start_time = time.time()
            await asyncio.gather(*tasks)
            end_time = time.time()
            
        total_time = end_time - start_time
        print(f"API load test completed in {total_time:.2f}s")
        
    async def _simulate_user_session(self, session: aiohttp.ClientSession, user_id: int, duration: int):
        """Simulate a user session"""
        start_time = time.time()
        request_times = []
        
        while time.time() - start_time < duration:
            try:
                # Test menu endpoint
                req_start = time.time()
                async with session.get(f"{self.base_url}/api/menu") as resp:
                    await resp.text()
                    request_times.append(time.time() - req_start)
                    
                # Test orders endpoint
                req_start = time.time()
                async with session.get(f"{self.base_url}/api/orders") as resp:
                    await resp.text()
                    request_times.append(time.time() - req_start)
                    
                await asyncio.sleep(1)  # 1 second between requests
                
            except Exception as e:
                print(f"User {user_id} error: {e}")
                
        if request_times:
            avg_time = statistics.mean(request_times)
            self.results.append({
                'user_id': user_id,
                'avg_response_time': avg_time,
                'total_requests': len(request_times),
                'duration': time.time() - start_time
            })
            
    async def test_websocket_connections(self, concurrent_connections: int = 100, duration: int = 60):
        """Test WebSocket connections under load"""
        print(f"Starting WebSocket load test: {concurrent_connections} connections for {duration}s")
        
        import socketio
        sio = socketio.AsyncClient()
        
        connection_tasks = []
        for i in range(concurrent_connections):
            task = asyncio.create_task(
                self._simulate_websocket_client(sio, i, duration)
            )
            connection_tasks.append(task)
            
        start_time = time.time()
        await asyncio.gather(*connection_tasks, return_exceptions=True)
        end_time = time.time()
        
        total_time = end_time - start_time
        print(f"WebSocket load test completed in {total_time:.2f}s")
        
    async def _simulate_websocket_client(self, sio, client_id: int, duration: int):
        """Simulate a WebSocket client"""
        start_time = time.time()
        connection_time = None
        disconnection_time = None
        
        try:
            connection_time = time.time()
            await sio.connect(self.base_url)
            
            while time.time() - start_time < duration:
                await asyncio.sleep(5)  # Send heartbeat every 5 seconds
                
        except Exception as e:
            print(f"WebSocket client {client_id} error: {e}")
        finally:
            disconnection_time = time.time()
            
        self.results.append({
            'client_id': client_id,
            'connection_time': connection_time,
            'disconnection_time': disconnection_time,
            'duration': (disconnection_time or time.time()) - start_time if connection_time else 0
        })
        
    def generate_report(self) -> Dict:
        """Generate load test report"""
        if not self.results:
            return {"error": "No test results available"}
            
        api_results = [r for r in self.results if 'avg_response_time' in r]
        ws_results = [r for r in self.results if 'connection_time' in r]
        
        report = {
            'summary': {
                'total_tests': len(self.results),
                'api_tests': len(api_results),
                'websocket_tests': len(ws_results)
            }
        }
        
        if api_results:
            response_times = [r['avg_response_time'] for r in api_results]
            report['api_performance'] = {
                'avg_response_time': statistics.mean(response_times),
                'min_response_time': min(response_times),
                'max_response_time': max(response_times),
                'median_response_time': statistics.median(response_times)
            }
            
        if ws_results:
            durations = [r['duration'] for r in ws_results if r['duration'] > 0]
            report['websocket_performance'] = {
                'avg_connection_duration': statistics.mean(durations) if durations else 0,
                'successful_connections': len([r for r in ws_results if r['duration'] > 0])
            }
            
        return report

async def main():
    """Main load testing function"""
    tester = LoadTester()
    
    # Run API load test
    await tester.test_api_endpoints(concurrent_users=50, duration=30)
    
    # Run WebSocket load test
    await tester.test_websocket_connections(concurrent_connections=100, duration=30)
    
    # Generate report
    report = tester.generate_report()
    print("\n" + "="*50)
    print("LOAD TEST REPORT")
    print("="*50)
    print(json.dumps(report, indent=2))
    print("="*50)

if __name__ == '__main__':
    asyncio.run(main())
