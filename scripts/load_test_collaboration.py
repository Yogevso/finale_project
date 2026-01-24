"""
Load Testing Script for Real-Time Collaboration

This script simulates multiple concurrent users editing the same document
to test the collaboration server's scalability.

Usage:
    python load_test_collaboration.py --users 10 --duration 60
    python load_test_collaboration.py --users 50 --duration 120 --document-id 1

Requirements:
    pip install aiohttp websockets pyjwt
"""

import asyncio
import argparse
import json
import random
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

try:
    import aiohttp
    import websockets
    import jwt
except ImportError:
    print("Required packages not installed. Run:")
    print("  pip install aiohttp websockets pyjwt")
    exit(1)


@dataclass
class LoadTestConfig:
    """Configuration for load testing"""
    num_users: int = 10
    duration_seconds: int = 60
    document_id: Optional[int] = None
    backend_url: str = "http://localhost:8000"
    collab_server_url: str = "ws://localhost:8002"
    actions_per_second: float = 2.0  # Average actions per user per second
    verbose: bool = False


@dataclass
class LoadTestMetrics:
    """Metrics collected during load testing"""
    total_connections: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    total_messages_sent: int = 0
    total_messages_received: int = 0
    total_errors: int = 0
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    connection_times: list = None
    message_latencies: list = None
    
    def __post_init__(self):
        self.connection_times = []
        self.message_latencies = []


class SimulatedUser:
    """Simulates a single user in the load test"""
    
    def __init__(
        self,
        user_id: int,
        config: LoadTestConfig,
        metrics: LoadTestMetrics
    ):
        self.user_id = user_id
        self.config = config
        self.metrics = metrics
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.messages_sent = 0
        self.messages_received = 0
        
    async def get_collab_token(self) -> Optional[str]:
        """Get a collaboration token from the backend"""
        # For load testing, we create a mock token
        # In production, you'd authenticate with the backend
        token_payload = {
            "sub": str(self.user_id),
            "username": f"loadtest_user_{self.user_id}",
            "email": f"user{self.user_id}@loadtest.com",
            "role": "editor",
            "document_id": str(self.config.document_id or 1),
            "permissions": ["read", "write"],
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        
        # Use a known secret for testing
        secret = "your-secret-key-change-in-production"
        return jwt.encode(token_payload, secret, algorithm="HS256")
    
    async def connect(self) -> bool:
        """Connect to the collaboration server"""
        try:
            start_time = time.time()
            
            token = await self.get_collab_token()
            if not token:
                self.metrics.failed_connections += 1
                return False
            
            doc_id = self.config.document_id or 1
            url = f"{self.config.collab_server_url}/document/{doc_id}?token={token}"
            
            self.ws = await websockets.connect(
                url,
                ping_interval=30,
                ping_timeout=10,
            )
            
            connection_time = (time.time() - start_time) * 1000
            self.metrics.connection_times.append(connection_time)
            self.metrics.successful_connections += 1
            self.is_connected = True
            
            if self.config.verbose:
                print(f"[User {self.user_id}] Connected in {connection_time:.2f}ms")
            
            return True
            
        except Exception as e:
            self.metrics.failed_connections += 1
            self.metrics.total_errors += 1
            if self.config.verbose:
                print(f"[User {self.user_id}] Connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the collaboration server"""
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.is_connected = False
    
    async def send_edit_action(self):
        """Send a simulated edit action"""
        if not self.is_connected or not self.ws:
            return
        
        try:
            start_time = time.time()
            
            # Simulate a Yjs update message
            # In a real scenario, this would be actual Yjs binary data
            message = {
                "type": "sync",
                "data": {
                    "user_id": self.user_id,
                    "action": "edit",
                    "position": random.randint(0, 1000),
                    "content": f"text_{random.randint(1000, 9999)}",
                    "timestamp": int(time.time() * 1000),
                }
            }
            
            await self.ws.send(json.dumps(message))
            self.messages_sent += 1
            self.metrics.total_messages_sent += 1
            
            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
                latency = (time.time() - start_time) * 1000
                self.metrics.message_latencies.append(latency)
                self.messages_received += 1
                self.metrics.total_messages_received += 1
                
                if latency < self.metrics.min_latency_ms:
                    self.metrics.min_latency_ms = latency
                if latency > self.metrics.max_latency_ms:
                    self.metrics.max_latency_ms = latency
                    
            except asyncio.TimeoutError:
                # No response expected for all messages
                pass
                
        except Exception as e:
            self.metrics.total_errors += 1
            if self.config.verbose:
                print(f"[User {self.user_id}] Send error: {e}")
    
    async def send_cursor_update(self):
        """Send a cursor position update"""
        if not self.is_connected or not self.ws:
            return
        
        try:
            message = {
                "type": "awareness",
                "data": {
                    "user_id": self.user_id,
                    "cursor": {
                        "anchor": random.randint(0, 1000),
                        "head": random.randint(0, 1000),
                    }
                }
            }
            
            await self.ws.send(json.dumps(message))
            self.messages_sent += 1
            self.metrics.total_messages_sent += 1
            
        except Exception as e:
            self.metrics.total_errors += 1
    
    async def run(self, duration_seconds: int):
        """Run the simulated user for a duration"""
        if not await self.connect():
            return
        
        end_time = time.time() + duration_seconds
        
        try:
            while time.time() < end_time:
                # Random delay between actions
                delay = random.expovariate(self.config.actions_per_second)
                await asyncio.sleep(min(delay, 2.0))
                
                # Random action
                action = random.choice(["edit", "edit", "cursor"])  # 2:1 ratio
                
                if action == "edit":
                    await self.send_edit_action()
                else:
                    await self.send_cursor_update()
                    
        except asyncio.CancelledError:
            pass
        finally:
            await self.disconnect()


class LoadTester:
    """Orchestrates the load test"""
    
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.metrics = LoadTestMetrics()
        
    async def run(self):
        """Run the load test"""
        print(f"\n{'='*60}")
        print("COLLABORATION LOAD TEST")
        print(f"{'='*60}")
        print(f"Users: {self.config.num_users}")
        print(f"Duration: {self.config.duration_seconds} seconds")
        print(f"Document ID: {self.config.document_id or 1}")
        print(f"Backend: {self.config.backend_url}")
        print(f"Collab Server: {self.config.collab_server_url}")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        
        # Create simulated users
        users = [
            SimulatedUser(i + 1, self.config, self.metrics)
            for i in range(self.config.num_users)
        ]
        
        # Run all users concurrently
        print(f"Starting {len(users)} simulated users...")
        
        tasks = [user.run(self.config.duration_seconds) for user in users]
        
        # Progress indicator
        async def progress_indicator():
            elapsed = 0
            while elapsed < self.config.duration_seconds:
                await asyncio.sleep(10)
                elapsed = int(time.time() - start_time)
                print(f"  Progress: {elapsed}s / {self.config.duration_seconds}s "
                      f"| Messages: {self.metrics.total_messages_sent} sent, "
                      f"{self.metrics.total_messages_received} received")
        
        # Run everything
        await asyncio.gather(
            *tasks,
            progress_indicator(),
            return_exceptions=True
        )
        
        total_time = time.time() - start_time
        
        # Calculate final metrics
        if self.metrics.message_latencies:
            self.metrics.avg_latency_ms = sum(self.metrics.message_latencies) / len(self.metrics.message_latencies)
        
        if self.metrics.min_latency_ms == float('inf'):
            self.metrics.min_latency_ms = 0
        
        # Print results
        self.print_results(total_time)
        
        return self.metrics
    
    def print_results(self, total_time: float):
        """Print load test results"""
        m = self.metrics
        
        print(f"\n{'='*60}")
        print("LOAD TEST RESULTS")
        print(f"{'='*60}")
        print(f"\nConnection Metrics:")
        print(f"  Total Connections Attempted: {m.total_connections or self.config.num_users}")
        print(f"  Successful Connections:      {m.successful_connections}")
        print(f"  Failed Connections:          {m.failed_connections}")
        success_rate = (m.successful_connections / self.config.num_users * 100) if self.config.num_users > 0 else 0
        print(f"  Success Rate:                {success_rate:.1f}%")
        
        if m.connection_times:
            avg_conn = sum(m.connection_times) / len(m.connection_times)
            print(f"  Avg Connection Time:         {avg_conn:.2f}ms")
        
        print(f"\nMessage Metrics:")
        print(f"  Total Messages Sent:         {m.total_messages_sent}")
        print(f"  Total Messages Received:     {m.total_messages_received}")
        print(f"  Total Errors:                {m.total_errors}")
        
        if total_time > 0:
            msg_per_sec = m.total_messages_sent / total_time
            print(f"  Messages/Second:             {msg_per_sec:.2f}")
        
        print(f"\nLatency Metrics:")
        print(f"  Average Latency:             {m.avg_latency_ms:.2f}ms")
        print(f"  Min Latency:                 {m.min_latency_ms:.2f}ms")
        print(f"  Max Latency:                 {m.max_latency_ms:.2f}ms")
        
        print(f"\nTest Duration: {total_time:.1f} seconds")
        print(f"{'='*60}\n")
        
        # Assessment
        print("ASSESSMENT:")
        if m.failed_connections == 0 and m.total_errors == 0:
            print("  ✅ All connections successful, no errors")
        elif m.failed_connections / self.config.num_users < 0.05:
            print("  ⚠️  Minor issues detected (< 5% failure rate)")
        else:
            print("  ❌ Significant failures detected")
        
        if m.avg_latency_ms < 100:
            print("  ✅ Excellent latency (< 100ms)")
        elif m.avg_latency_ms < 500:
            print("  ⚠️  Acceptable latency (< 500ms)")
        else:
            print("  ❌ High latency detected (> 500ms)")
        
        print()


async def main():
    parser = argparse.ArgumentParser(description="Load test the collaboration server")
    parser.add_argument("--users", type=int, default=10, help="Number of simulated users")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--document-id", type=int, default=1, help="Document ID to collaborate on")
    parser.add_argument("--backend-url", default="http://localhost:8000", help="Backend API URL")
    parser.add_argument("--collab-url", default="ws://localhost:8002", help="Collaboration server WebSocket URL")
    parser.add_argument("--actions-per-second", type=float, default=2.0, help="Average actions per user per second")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    config = LoadTestConfig(
        num_users=args.users,
        duration_seconds=args.duration,
        document_id=args.document_id,
        backend_url=args.backend_url,
        collab_server_url=args.collab_url,
        actions_per_second=args.actions_per_second,
        verbose=args.verbose,
    )
    
    tester = LoadTester(config)
    await tester.run()


if __name__ == "__main__":
    asyncio.run(main())
