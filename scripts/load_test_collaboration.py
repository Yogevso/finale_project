"""
Load testing entrypoint for collaboration-related runtime paths.

The assignment-update scenario remains Python-native in this file.
The collaboration scenario now delegates to the protocol-faithful Yjs/Hocuspocus
gate under ``frontend/scripts/run-collab-perf-gate.mjs`` so the repo no longer
advertises the old synthetic JSON-websocket harness as the primary collab test.

Usage:
    python load_test_collaboration.py --users 10 --duration 60
    python load_test_collaboration.py --users 50 --duration 120 --document-id 1
    python load_test_collaboration.py --scenario assignments --document-id 1 --assignment-concurrency 50 --assignment-updates 50 --auth-token <TOKEN>

Requirements:
    pip install aiohttp websockets pyjwt
"""

import asyncio
import argparse
import json
import random
import subprocess
import time
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from uuid import uuid4

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
    scenario: str = "collaboration"
    assignment_updates: int = 50
    assignment_concurrency: int = 50
    auth_token: Optional[str] = None
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
    assignment_attempts: int = 0
    assignment_successes: int = 0
    assignment_conflicts: int = 0
    assignment_failures: int = 0
    assignment_latencies_ms: list = None
    
    def __post_init__(self):
        self.connection_times = []
        self.message_latencies = []
        self.assignment_latencies_ms = []


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


async def run_assignment_update_load_test(config: LoadTestConfig) -> LoadTestMetrics:
    """
    Simulate concurrent company-assignment updates for one document.

    This scenario targets /api/v1/documents/{id}/companies/batch and uses
    optimistic concurrency headers to exercise conflict handling.
    """
    metrics = LoadTestMetrics()
    if not config.document_id:
        raise ValueError("Assignment update scenario requires --document-id")
    if not config.auth_token:
        raise ValueError(
            "Assignment update scenario requires --auth-token or LOAD_TEST_AUTH_TOKEN env var"
        )

    common_headers = {
        "Authorization": f"Bearer {config.auth_token}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        doc_url = f"{config.backend_url}/api/v1/documents/{config.document_id}"
        async with session.get(doc_url, headers=common_headers) as doc_response:
            if doc_response.status != 200:
                text = await doc_response.text()
                raise RuntimeError(
                    f"Unable to fetch document {config.document_id} for load test "
                    f"(status={doc_response.status} body={text[:200]})"
                )
            etag = doc_response.headers.get("ETag")
            if not etag:
                raise RuntimeError("Document detail response is missing ETag header")

        companies_url = f"{config.backend_url}/api/v1/companies?page=1&per_page=100&is_active=true"
        async with session.get(companies_url, headers=common_headers) as companies_response:
            if companies_response.status != 200:
                text = await companies_response.text()
                raise RuntimeError(
                    "Unable to list companies for assignment load test "
                    f"(status={companies_response.status} body={text[:200]})"
                )
            company_payload = await companies_response.json()
            company_ids = [int(item["id"]) for item in company_payload.get("items", [])]
            if not company_ids:
                raise RuntimeError("No active companies found for assignment load test")

        total_updates = max(config.assignment_updates, config.assignment_concurrency)
        semaphore = asyncio.Semaphore(max(1, config.assignment_concurrency))
        etag_lock = asyncio.Lock()
        shared_state = {"etag": etag}

        async def _run_update(update_index: int) -> None:
            async with semaphore:
                selected_count = min(len(company_ids), random.randint(1, min(3, len(company_ids))))
                selected_ids = random.sample(company_ids, k=selected_count)
                payload = {"company_ids": selected_ids}
                update_headers = {
                    **common_headers,
                    "Idempotency-Key": f"assignment-load-{uuid4().hex}",
                }
                async with etag_lock:
                    update_headers["If-Match"] = str(shared_state["etag"])

                started_at = time.perf_counter()
                endpoint = (
                    f"{config.backend_url}/api/v1/documents/"
                    f"{config.document_id}/companies/batch"
                )
                async with session.put(
                    endpoint,
                    headers=update_headers,
                    json=payload,
                ) as update_response:
                    elapsed_ms = (time.perf_counter() - started_at) * 1000.0
                    metrics.assignment_attempts += 1
                    metrics.assignment_latencies_ms.append(elapsed_ms)

                    if update_response.status == 200:
                        metrics.assignment_successes += 1
                        next_etag = update_response.headers.get("ETag")
                        if next_etag:
                            async with etag_lock:
                                shared_state["etag"] = next_etag
                        return

                    if update_response.status == 409:
                        metrics.assignment_conflicts += 1
                        return

                    metrics.assignment_failures += 1
                    if config.verbose:
                        text = await update_response.text()
                        print(
                            f"[Assignment {update_index}] status={update_response.status} "
                            f"body={text[:180]}"
                        )

        print("\n" + "=" * 60)
        print("ASSIGNMENT UPDATE LOAD TEST")
        print("=" * 60)
        print(f"Document ID: {config.document_id}")
        print(f"Concurrent workers: {config.assignment_concurrency}")
        print(f"Total updates: {total_updates}")
        print(f"Backend: {config.backend_url}")
        print("=" * 60 + "\n")

        started_at = time.perf_counter()
        await asyncio.gather(*(_run_update(index) for index in range(total_updates)))
        duration = time.perf_counter() - started_at

    latencies = sorted(metrics.assignment_latencies_ms)
    p50 = latencies[len(latencies) // 2] if latencies else 0.0
    p95 = latencies[max(0, min(len(latencies) - 1, int(len(latencies) * 0.95) - 1))] if latencies else 0.0

    print("\n" + "=" * 60)
    print("ASSIGNMENT LOAD TEST RESULTS")
    print("=" * 60)
    print(f"Attempts: {metrics.assignment_attempts}")
    print(f"Successes: {metrics.assignment_successes}")
    print(f"Conflicts: {metrics.assignment_conflicts}")
    print(f"Failures: {metrics.assignment_failures}")
    print(f"Duration: {duration:.2f}s")
    print(f"Latency p50: {p50:.2f}ms")
    print(f"Latency p95: {p95:.2f}ms")
    print("=" * 60 + "\n")
    return metrics


async def main():
    parser = argparse.ArgumentParser(description="Load test collaboration and assignment paths")
    parser.add_argument(
        "--scenario",
        choices=["collaboration", "assignments"],
        default="collaboration",
        help="Which scenario to run",
    )
    parser.add_argument("--users", type=int, default=10, help="Number of simulated users")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--document-id", type=int, default=1, help="Document ID to collaborate on")
    parser.add_argument("--backend-url", default="http://localhost:8000", help="Backend API URL")
    parser.add_argument("--collab-url", default="ws://localhost:8002", help="Collaboration server WebSocket URL")
    parser.add_argument("--actions-per-second", type=float, default=2.0, help="Average actions per user per second")
    parser.add_argument(
        "--assignment-updates",
        type=int,
        default=50,
        help="Total assignment update requests for --scenario assignments",
    )
    parser.add_argument(
        "--assignment-concurrency",
        type=int,
        default=50,
        help="Concurrent assignment update workers for --scenario assignments",
    )
    parser.add_argument(
        "--auth-token",
        default=None,
        help="Bearer token for assignment scenario (or set LOAD_TEST_AUTH_TOKEN)",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    config = LoadTestConfig(
        num_users=args.users,
        duration_seconds=args.duration,
        document_id=args.document_id,
        backend_url=args.backend_url,
        collab_server_url=args.collab_url,
        actions_per_second=args.actions_per_second,
        scenario=args.scenario,
        assignment_updates=args.assignment_updates,
        assignment_concurrency=args.assignment_concurrency,
        auth_token=args.auth_token,
        verbose=args.verbose,
    )

    if not config.auth_token:
        config.auth_token = None
        try:
            import os

            config.auth_token = os.environ.get("LOAD_TEST_AUTH_TOKEN")
        except Exception:
            config.auth_token = None

    if config.scenario == "assignments":
        await run_assignment_update_load_test(config)
    else:
        repo_root = Path(__file__).resolve().parent.parent
        collab_gate = repo_root / "frontend" / "scripts" / "run-collab-perf-gate.mjs"
        rounds = max(1, min(10, config.duration_seconds // 10 or 1))
        command = [
            "node",
            str(collab_gate),
            "--backend-url",
            config.backend_url,
            "--collab-url",
            config.collab_server_url,
            "--users",
            str(config.num_users),
            "--rounds",
            str(rounds),
        ]
        if config.document_id:
            command.extend(["--document-id", str(config.document_id)])
        if config.verbose:
            command.append("--verbose")

        print(
            "Delegating collaboration scenario to the protocol-faithful provider harness:"
        )
        print("  " + " ".join(command))
        completed = await asyncio.to_thread(subprocess.run, command, check=False)
        raise SystemExit(completed.returncode)


if __name__ == "__main__":
    asyncio.run(main())
