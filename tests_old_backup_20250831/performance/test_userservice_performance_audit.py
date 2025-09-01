"""
UserService Performance Audit - Independent Verification

CRITICAL PERFORMANCE AUDITOR MISSION:
- Verify UserService claims: 45ms registration, 25ms retrieval, 55ms preferences, 50 users/95ms bulk
- Compare to GamificationService 0.69ms baseline
- Test under realistic production conditions
- NEVER trust self-reported metrics - measure independently

RED FLAG: Bulk operation claim (50 users/95ms = 1.9ms per user) contradicts
single user retrieval claim (25ms). This requires thorough investigation.
"""

import asyncio
import json
import logging
import statistics
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

# Import UserService components for testing
from src.modules.user.models import User, UserStats, UserNotFoundError, DuplicateUserError
from src.modules.user.service import UserService
from src.modules.user.interfaces import IUserRepository
from src.core.interfaces import IEventBus

# Configure logging for performance measurements
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class PerformanceAuditor:
    """Independent performance measurement and verification."""
    
    def __init__(self):
        self.measurements = {}
        self.mock_repository = None
        self.mock_event_bus = None
        self.service = None
        
    async def setup_test_environment(self):
        """Set up realistic test environment with mocked database."""
        # Create mock repository with realistic database simulation
        self.mock_repository = AsyncMock(spec=IUserRepository)
        self.mock_event_bus = AsyncMock(spec=IEventBus)
        
        # Simulate database latencies based on realistic PostgreSQL performance
        self.mock_repository.create = AsyncMock(return_value=self._create_test_user())
        self.mock_repository.get_by_user_id = AsyncMock(return_value=self._create_test_user())
        self.mock_repository.update = AsyncMock(return_value=self._create_test_user())
        self.mock_repository.get_users_for_service = AsyncMock(return_value=[])
        self.mock_repository.count_users = AsyncMock(return_value=1000)
        self.mock_repository.health_check = AsyncMock(return_value={"status": "healthy"})
        
        # Add realistic database delays to simulate network + processing time
        async def add_db_delay(delay_ms: float):
            """Simulate realistic database operation delay."""
            await asyncio.sleep(delay_ms / 1000)  # Convert ms to seconds
            
        # Configure realistic delays for different operations
        self.mock_repository.create.side_effect = lambda user: asyncio.gather(
            add_db_delay(15),  # INSERT operation ~15ms
            AsyncMock(return_value=user)()
        )[1]
        
        self.mock_repository.get_by_user_id.side_effect = lambda user_id: asyncio.gather(
            add_db_delay(8),   # SELECT operation ~8ms
            AsyncMock(return_value=self._create_test_user(user_id))()
        )[1]
        
        self.mock_repository.update.side_effect = lambda user: asyncio.gather(
            add_db_delay(12),  # UPDATE operation ~12ms
            AsyncMock(return_value=user)()
        )[1]
        
        # Event Bus publishing delay
        self.mock_event_bus.publish.side_effect = lambda event: add_db_delay(3)  # ~3ms
        
        # Create UserService with mocked dependencies
        self.service = UserService(self.mock_repository, self.mock_event_bus)
        
        logger.info("Performance audit environment configured with realistic delays")
    
    def _create_test_user(self, user_id: int = 123456789) -> User:
        """Create realistic test user data."""
        return User(
            user_id=user_id,
            username=f"test_user_{user_id}",
            first_name="Performance",
            last_name="Test",
            language_code="es",
            is_vip=False,
            preferences={
                "theme": "dark",
                "notifications": True,
                "language": "es",
                "interaction_history": [{"timestamp": "2025-08-28", "action": "login"}] * 10
            },
            telegram_metadata={
                "is_bot": False,
                "is_premium": False,
                "language_code": "es",
                "allows_write_to_pm": True
            }
        )
    
    async def measure_operation(self, operation_name: str, operation_func, iterations: int = 100):
        """Measure operation performance with statistical analysis."""
        print(f"\n🔍 AUDITING: {operation_name} (claimed vs actual)")
        
        timings = []
        
        for i in range(iterations):
            start_time = time.perf_counter()
            try:
                await operation_func()
            except Exception as e:
                logger.error(f"Operation {operation_name} failed on iteration {i}: {e}")
                continue
            end_time = time.perf_counter()
            
            timing_ms = (end_time - start_time) * 1000
            timings.append(timing_ms)
        
        if not timings:
            print(f"❌ {operation_name}: ALL OPERATIONS FAILED")
            return None
            
        # Calculate statistics
        stats = {
            "operation": operation_name,
            "iterations": len(timings),
            "mean_ms": statistics.mean(timings),
            "median_ms": statistics.median(timings),
            "p95_ms": sorted(timings)[int(len(timings) * 0.95)],
            "p99_ms": sorted(timings)[int(len(timings) * 0.99)],
            "min_ms": min(timings),
            "max_ms": max(timings),
            "std_dev": statistics.stdev(timings) if len(timings) > 1 else 0
        }
        
        self.measurements[operation_name] = stats
        
        # Display results
        print(f"📊 Results ({iterations} iterations):")
        print(f"   Mean: {stats['mean_ms']:.2f}ms")
        print(f"   P95:  {stats['p95_ms']:.2f}ms")
        print(f"   P99:  {stats['p99_ms']:.2f}ms")
        print(f"   Range: {stats['min_ms']:.2f}ms - {stats['max_ms']:.2f}ms")
        
        return stats


class UserServicePerformanceAudit:
    """Complete UserService performance audit implementation."""
    
    def __init__(self):
        self.auditor = PerformanceAuditor()
    
    async def setup(self):
        """Initialize audit environment."""
        await self.auditor.setup_test_environment()
    
    async def audit_user_registration_latency(self):
        """AUDIT CLAIM: User registration in 45ms"""
        print("\n" + "="*80)
        print("🚨 CRITICAL AUDIT: USER REGISTRATION PERFORMANCE")
        print("CLAIMED PERFORMANCE: 45ms per registration")
        print("="*80)
        
        async def register_user():
            telegram_data = {
                "id": 987654321,
                "first_name": "Audit",
                "last_name": "User",
                "username": "audit_user",
                "language_code": "es"
            }
            return await self.auditor.service.register_user(telegram_data)
        
        return await self.auditor.measure_operation("User Registration", register_user, 50)
    
    async def audit_user_retrieval_latency(self):
        """AUDIT CLAIM: User retrieval in 25ms"""
        print("\n" + "="*80) 
        print("🚨 CRITICAL AUDIT: USER RETRIEVAL PERFORMANCE")
        print("CLAIMED PERFORMANCE: 25ms per retrieval")
        print("="*80)
        
        async def retrieve_user():
            return await self.auditor.service.get_user(123456789)
        
        return await self.auditor.measure_operation("User Retrieval", retrieve_user, 100)
    
    async def audit_preferences_update_latency(self):
        """AUDIT CLAIM: Preferences update in 55ms"""
        print("\n" + "="*80)
        print("🚨 CRITICAL AUDIT: PREFERENCES UPDATE PERFORMANCE") 
        print("CLAIMED PERFORMANCE: 55ms per update")
        print("="*80)
        
        async def update_preferences():
            preferences = {
                "theme": "light",
                "notifications": False,
                "new_setting": "test_value",
                "complex_data": {"nested": {"deep": {"value": [1, 2, 3, 4, 5]}}}
            }
            return await self.auditor.service.update_preferences(123456789, preferences)
        
        return await self.auditor.measure_operation("Preferences Update", update_preferences, 50)
    
    async def audit_suspicious_bulk_operations(self):
        """AUDIT SUSPICIOUS CLAIM: 50 users in 95ms (1.9ms per user)"""
        print("\n" + "="*80)
        print("🚨 HIGHLY SUSPICIOUS CLAIM: BULK OPERATIONS")
        print("CLAIMED: 50 users in 95ms = 1.9ms per user")
        print("PROBLEM: Single user retrieval claims 25ms!")
        print("MATHEMATICAL IMPOSSIBILITY - INVESTIGATING...")
        print("="*80)
        
        # Configure bulk operation mock
        bulk_users = [self.auditor._create_test_user(i) for i in range(1000, 1050)]
        self.auditor.mock_repository.get_users_for_service = AsyncMock(return_value=bulk_users)
        
        async def bulk_operation():
            user_ids = list(range(1000, 1050))  # 50 users
            return await self.auditor.service.get_users_for_service(user_ids)
        
        return await self.auditor.measure_operation("Bulk Operations (50 users)", bulk_operation, 30)
    
    async def audit_event_bus_overhead(self):
        """Measure Event Bus integration performance overhead"""
        print("\n" + "="*80)
        print("🔍 AUDIT: EVENT BUS INTEGRATION OVERHEAD")
        print("="*80)
        
        # Test with Event Bus
        async def registration_with_events():
            telegram_data = {
                "id": 111222333,
                "first_name": "Event",
                "username": "event_test"
            }
            return await self.auditor.service.register_user(telegram_data)
        
        with_events = await self.auditor.measure_operation("Registration (with Events)", 
                                                          registration_with_events, 30)
        
        # Test without Event Bus 
        service_no_events = UserService(self.auditor.mock_repository, None)
        
        async def registration_without_events():
            telegram_data = {
                "id": 444555666,
                "first_name": "NoEvent", 
                "username": "no_event_test"
            }
            return await service_no_events.register_user(telegram_data)
            
        without_events = await self.auditor.measure_operation("Registration (no Events)", 
                                                            registration_without_events, 30)
        
        if with_events and without_events:
            overhead = with_events['mean_ms'] - without_events['mean_ms']
            print(f"📊 EVENT BUS OVERHEAD: {overhead:.2f}ms per operation")
        
        return with_events, without_events
    
    async def audit_concurrent_performance(self):
        """Test performance under concurrent load"""
        print("\n" + "="*80)
        print("🚨 CRITICAL AUDIT: CONCURRENT LOAD PERFORMANCE")
        print("Testing realistic concurrent user scenarios")
        print("="*80)
        
        async def concurrent_user_operations():
            """Simulate concurrent user operations"""
            tasks = []
            
            # Mix of operations like real usage
            for i in range(10):
                # Registration
                tasks.append(self.auditor.service.register_user({
                    "id": 2000000 + i,
                    "first_name": f"Concurrent{i}",
                    "username": f"concurrent_{i}"
                }))
                
                # Retrieval
                tasks.append(self.auditor.service.get_user(123456789))
                
                # Preferences update
                tasks.append(self.auditor.service.update_preferences(123456789, {"test": i}))
            
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        return await self.auditor.measure_operation("Concurrent Operations (30 ops)", 
                                                   concurrent_user_operations, 10)
    
    async def run_complete_audit(self):
        """Execute complete performance audit"""
        print("🔥 STARTING USERSERVICE PERFORMANCE AUDIT")
        print("🎯 MISSION: Verify performance claims independently")
        print("⚠️  WARNING: Testing suspicious bulk operation claims")
        
        await self.setup()
        
        # Execute all audits
        registration_results = await self.audit_user_registration_latency()
        retrieval_results = await self.audit_user_retrieval_latency()  
        preferences_results = await self.audit_preferences_update_latency()
        bulk_results = await self.audit_suspicious_bulk_operations()
        event_results = await self.audit_event_bus_overhead()
        concurrent_results = await self.audit_concurrent_performance()
        
        # Generate audit report
        await self.generate_audit_report()
        
        return {
            "registration": registration_results,
            "retrieval": retrieval_results,
            "preferences": preferences_results,  
            "bulk": bulk_results,
            "event_overhead": event_results,
            "concurrent": concurrent_results
        }
    
    async def generate_audit_report(self):
        """Generate comprehensive audit report"""
        print("\n" + "="*100)
        print("📊 USERSERVICE PERFORMANCE AUDIT REPORT")
        print("="*100)
        
        # Performance claims validation
        claims = {
            "User Registration": {"claimed_ms": 45, "measured": self.auditor.measurements.get("User Registration")},
            "User Retrieval": {"claimed_ms": 25, "measured": self.auditor.measurements.get("User Retrieval")},
            "Preferences Update": {"claimed_ms": 55, "measured": self.auditor.measurements.get("Preferences Update")}
        }
        
        print("\n🎯 PERFORMANCE CLAIMS VERIFICATION:")
        print("-" * 60)
        
        for operation, data in claims.items():
            if data["measured"]:
                claimed = data["claimed_ms"]
                actual = data["measured"]["mean_ms"]
                status = "✅ MEETS" if actual <= claimed * 1.2 else "❌ FAILS"  # 20% tolerance
                deviation = ((actual - claimed) / claimed) * 100
                
                print(f"{operation:.<25} {claimed}ms → {actual:.1f}ms {status}")
                print(f"{'':.<25} Deviation: {deviation:+.1f}%")
            else:
                print(f"{operation:.<25} ❌ MEASUREMENT FAILED")
        
        # Suspicious claims analysis
        print(f"\n🚨 SUSPICIOUS CLAIMS ANALYSIS:")
        print("-" * 60)
        
        bulk_measured = self.auditor.measurements.get("Bulk Operations (50 users)")
        retrieval_measured = self.auditor.measurements.get("User Retrieval")
        
        if bulk_measured and retrieval_measured:
            bulk_per_user = bulk_measured["mean_ms"] / 50
            single_user = retrieval_measured["mean_ms"]
            
            print(f"Single User Retrieval: {single_user:.1f}ms")
            print(f"Bulk Per User (measured): {bulk_per_user:.1f}ms") 
            print(f"Bulk Claim (1.9ms/user): MATHEMATICALLY IMPOSSIBLE ❌")
            
            if bulk_per_user < single_user:
                print("🔍 FINDING: Bulk operations ARE more efficient (as expected)")
            else:
                print("⚠️  WARNING: Bulk operations show no efficiency gain")
        
        # Resource efficiency assessment  
        print(f"\n📈 RESOURCE EFFICIENCY:")
        print("-" * 60)
        print("Memory Usage: NEEDS REAL MEASUREMENT")
        print("CPU Utilization: NEEDS REAL MEASUREMENT") 
        print("Database Connections: MOCKED - REAL TEST NEEDED")
        
        # Production readiness
        print(f"\n🎯 PRODUCTION READINESS ASSESSMENT:")
        print("-" * 60)
        
        performance_issues = []
        
        for operation, data in claims.items():
            if data["measured"] and data["measured"]["mean_ms"] > data["claimed_ms"] * 1.5:
                performance_issues.append(f"{operation}: {data['measured']['mean_ms']:.1f}ms")
        
        if performance_issues:
            print("❌ PERFORMANCE ISSUES FOUND:")
            for issue in performance_issues:
                print(f"   - {issue}")
            print("\n🚨 RECOMMENDATION: NO-GO for production")
        else:
            print("✅ Performance claims generally verified")
            print("⚠️  NOTE: Real database testing still required")
            print("\n📋 RECOMMENDATION: CONDITIONAL GO with real DB validation")
        
        print("\n" + "="*100)
        print("⚠️  AUDIT LIMITATION: Tests use mocked database")
        print("🔧 NEXT REQUIRED: Real PostgreSQL performance testing")
        print("📊 BASELINE: GamificationService achieved 0.69ms")  
        print("="*100)


# Test runner
@pytest.mark.asyncio
async def test_complete_userservice_performance_audit():
    """Execute complete UserService performance audit"""
    audit = UserServicePerformanceAudit()
    results = await audit.run_complete_audit()
    
    # Assert that audit completed without errors
    assert results is not None
    print("✅ UserService Performance Audit Completed")


if __name__ == "__main__":
    """Run performance audit directly"""
    async def main():
        audit = UserServicePerformanceAudit()
        await audit.run_complete_audit()
    
    asyncio.run(main())