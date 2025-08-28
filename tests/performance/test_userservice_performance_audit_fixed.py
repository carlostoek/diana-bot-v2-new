"""
UserService Performance Audit - FIXED Version

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
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import UserService components for testing
from src.modules.user.models import User, UserStats, UserNotFoundError, DuplicateUserError
from src.modules.user.service import UserService
from src.modules.user.interfaces import IUserRepository
from src.core.interfaces import IEventBus

# Configure logging for performance measurements
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class RealisticMockRepository:
    """Mock repository with realistic database behavior and delays."""
    
    def __init__(self):
        self.users_db = {}  # In-memory user storage
        self.operation_count = 0
        
    async def _simulate_db_delay(self, operation_type: str) -> None:
        """Simulate realistic database delays based on operation type."""
        delays = {
            "select": 0.008,   # 8ms for SELECT
            "insert": 0.015,   # 15ms for INSERT
            "update": 0.012,   # 12ms for UPDATE
            "bulk_select": 0.025  # 25ms for bulk operations
        }
        await asyncio.sleep(delays.get(operation_type, 0.010))
        self.operation_count += 1
    
    async def create(self, user: User) -> User:
        """Create user with realistic INSERT delay."""
        await self._simulate_db_delay("insert")
        
        if user.user_id in self.users_db:
            raise DuplicateUserError(f"User {user.user_id} already exists")
        
        # Simulate user creation timestamp
        user.created_at = datetime.now(timezone.utc)
        user.last_active = datetime.now(timezone.utc)
        
        self.users_db[user.user_id] = user
        return user
    
    async def get_by_user_id(self, user_id: int) -> Optional[User]:
        """Get user with realistic SELECT delay."""
        await self._simulate_db_delay("select")
        return self.users_db.get(user_id)
    
    async def update(self, user: User) -> User:
        """Update user with realistic UPDATE delay."""
        await self._simulate_db_delay("update")
        
        if user.user_id not in self.users_db:
            raise UserNotFoundError(f"User {user.user_id} not found")
        
        self.users_db[user.user_id] = user
        return user
    
    async def get_users_for_service(self, user_ids: List[int]) -> List[User]:
        """Get bulk users with realistic bulk SELECT delay."""
        await self._simulate_db_delay("bulk_select")
        
        # Add more delay for larger batches (realistic database behavior)
        if len(user_ids) > 20:
            await asyncio.sleep(0.002 * len(user_ids))  # 2ms per additional user
        
        return [self.users_db[uid] for uid in user_ids if uid in self.users_db]
    
    async def count_users(self) -> int:
        """Count users with minimal delay."""
        await self._simulate_db_delay("select")
        return len(self.users_db)
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check with minimal delay."""
        await self._simulate_db_delay("select")
        return {
            "status": "healthy",
            "users_count": len(self.users_db),
            "operations_executed": self.operation_count
        }


class RealisticMockEventBus:
    """Mock event bus with realistic publishing delays."""
    
    def __init__(self):
        self.events_published = []
        
    async def publish(self, event) -> None:
        """Publish event with realistic Redis pub/sub delay."""
        await asyncio.sleep(0.003)  # 3ms for Redis publish
        self.events_published.append(event)


class PerformanceAuditor:
    """Independent performance measurement and verification."""
    
    def __init__(self):
        self.measurements = {}
        self.mock_repository = RealisticMockRepository()
        self.mock_event_bus = RealisticMockEventBus()
        self.service = None
        
    async def setup_test_environment(self):
        """Set up realistic test environment with proper mocks."""
        # Create UserService with realistic mocks
        self.service = UserService(self.mock_repository, self.mock_event_bus)
        
        # Pre-populate with a test user for retrieval/update tests
        test_user = self._create_test_user(123456789)
        await self.mock_repository.create(test_user)
        
        # Pre-populate with bulk test users
        for i in range(1000, 1100):  # 100 users for bulk testing
            bulk_user = self._create_test_user(i)
            await self.mock_repository.create(bulk_user)
        
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
        errors = 0
        
        for i in range(iterations):
            start_time = time.perf_counter()
            try:
                await operation_func()
            except Exception as e:
                logger.error(f"Operation {operation_name} failed on iteration {i}: {e}")
                errors += 1
                continue
            end_time = time.perf_counter()
            
            timing_ms = (end_time - start_time) * 1000
            timings.append(timing_ms)
        
        if not timings:
            print(f"❌ {operation_name}: ALL OPERATIONS FAILED ({errors} errors)")
            return None
            
        if errors > 0:
            print(f"⚠️  {operation_name}: {errors}/{iterations} operations failed")
            
        # Calculate statistics
        stats = {
            "operation": operation_name,
            "iterations": len(timings),
            "errors": errors,
            "mean_ms": statistics.mean(timings),
            "median_ms": statistics.median(timings),
            "p95_ms": sorted(timings)[int(len(timings) * 0.95)] if timings else 0,
            "p99_ms": sorted(timings)[int(len(timings) * 0.99)] if timings else 0,
            "min_ms": min(timings) if timings else 0,
            "max_ms": max(timings) if timings else 0,
            "std_dev": statistics.stdev(timings) if len(timings) > 1 else 0
        }
        
        self.measurements[operation_name] = stats
        
        # Display results
        print(f"📊 Results ({len(timings)} successful iterations):")
        print(f"   Mean: {stats['mean_ms']:.2f}ms")
        print(f"   P95:  {stats['p95_ms']:.2f}ms")
        print(f"   P99:  {stats['p99_ms']:.2f}ms")
        print(f"   Range: {stats['min_ms']:.2f}ms - {stats['max_ms']:.2f}ms")
        
        return stats


class UserServicePerformanceAudit:
    """Complete UserService performance audit implementation."""
    
    def __init__(self):
        self.auditor = PerformanceAuditor()
        self.audit_results = {}
    
    async def setup(self):
        """Initialize audit environment."""
        await self.auditor.setup_test_environment()
    
    async def audit_user_registration_latency(self):
        """AUDIT CLAIM: User registration in 45ms"""
        print("\n" + "="*80)
        print("🚨 CRITICAL AUDIT: USER REGISTRATION PERFORMANCE")
        print("CLAIMED PERFORMANCE: 45ms per registration")
        print("="*80)
        
        registration_counter = 2000000  # Start from high number to avoid conflicts
        
        async def register_user():
            nonlocal registration_counter
            telegram_data = {
                "id": registration_counter,
                "first_name": "Audit",
                "last_name": "User",
                "username": f"audit_user_{registration_counter}",
                "language_code": "es"
            }
            registration_counter += 1
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
        
        update_counter = 0
        
        async def update_preferences():
            nonlocal update_counter
            preferences = {
                "theme": "light" if update_counter % 2 == 0 else "dark",
                "notifications": update_counter % 2 == 0,
                "update_id": update_counter,
                "complex_data": {"nested": {"deep": {"value": [1, 2, 3, 4, 5]}}}
            }
            update_counter += 1
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
        
        async def bulk_operation():
            user_ids = list(range(1000, 1050))  # 50 users that exist in our mock DB
            return await self.auditor.service.get_users_for_service(user_ids)
        
        return await self.auditor.measure_operation("Bulk Operations (50 users)", bulk_operation, 30)
    
    async def audit_event_bus_overhead(self):
        """Measure Event Bus integration performance overhead"""
        print("\n" + "="*80)
        print("🔍 AUDIT: EVENT BUS INTEGRATION OVERHEAD")
        print("="*80)
        
        event_registration_counter = 3000000
        
        # Test with Event Bus
        async def registration_with_events():
            nonlocal event_registration_counter
            telegram_data = {
                "id": event_registration_counter,
                "first_name": "Event",
                "username": f"event_test_{event_registration_counter}"
            }
            event_registration_counter += 1
            return await self.auditor.service.register_user(telegram_data)
        
        with_events = await self.auditor.measure_operation("Registration (with Events)", 
                                                          registration_with_events, 30)
        
        # Test without Event Bus 
        service_no_events = UserService(self.auditor.mock_repository, None)
        no_event_registration_counter = 4000000
        
        async def registration_without_events():
            nonlocal no_event_registration_counter
            telegram_data = {
                "id": no_event_registration_counter,
                "first_name": "NoEvent", 
                "username": f"no_event_test_{no_event_registration_counter}"
            }
            no_event_registration_counter += 1
            return await service_no_events.register_user(telegram_data)
            
        without_events = await self.auditor.measure_operation("Registration (no Events)", 
                                                            registration_without_events, 30)
        
        if with_events and without_events:
            overhead = with_events['mean_ms'] - without_events['mean_ms']
            print(f"📊 EVENT BUS OVERHEAD: {overhead:.2f}ms per operation")
            print(f"   With Events: {with_events['mean_ms']:.2f}ms")
            print(f"   Without Events: {without_events['mean_ms']:.2f}ms")
            
            overhead_percentage = (overhead / without_events['mean_ms']) * 100
            print(f"   Overhead: {overhead_percentage:.1f}%")
        
        return with_events, without_events
    
    async def audit_concurrent_performance(self):
        """Test performance under concurrent load"""
        print("\n" + "="*80)
        print("🚨 CRITICAL AUDIT: CONCURRENT LOAD PERFORMANCE")
        print("Testing realistic concurrent user scenarios")
        print("="*80)
        
        concurrent_counter = 5000000
        
        async def concurrent_user_operations():
            """Simulate concurrent user operations"""
            nonlocal concurrent_counter
            tasks = []
            
            # Mix of operations like real usage
            for i in range(10):
                # Registration
                tasks.append(self.auditor.service.register_user({
                    "id": concurrent_counter + i,
                    "first_name": f"Concurrent{i}",
                    "username": f"concurrent_{concurrent_counter}_{i}"
                }))
                
                # Retrieval (use existing user)
                tasks.append(self.auditor.service.get_user(123456789))
                
                # Preferences update
                tasks.append(self.auditor.service.update_preferences(123456789, {"test": i}))
            
            concurrent_counter += 100  # Increment for next iteration
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        return await self.auditor.measure_operation("Concurrent Operations (30 ops)", 
                                                   concurrent_user_operations, 10)
    
    async def run_complete_audit(self):
        """Execute complete performance audit"""
        print("🔥 STARTING USERSERVICE PERFORMANCE AUDIT - FIXED VERSION")
        print("🎯 MISSION: Verify performance claims independently")
        print("⚠️  WARNING: Testing suspicious bulk operation claims")
        print("🔧 REALISTIC MOCK: Database delays simulated accurately")
        
        await self.setup()
        
        # Execute all audits
        self.audit_results = {
            "registration": await self.audit_user_registration_latency(),
            "retrieval": await self.audit_user_retrieval_latency(),  
            "preferences": await self.audit_preferences_update_latency(),
            "bulk": await self.audit_suspicious_bulk_operations(),
            "event_overhead": await self.audit_event_bus_overhead(),
            "concurrent": await self.audit_concurrent_performance()
        }
        
        # Generate audit report
        await self.generate_audit_report()
        
        return self.audit_results
    
    async def generate_audit_report(self):
        """Generate comprehensive audit report"""
        print("\n" + "="*100)
        print("📊 USERSERVICE PERFORMANCE AUDIT REPORT - VERIFIED MEASUREMENTS")
        print("="*100)
        
        # Performance claims validation
        claims = {
            "User Registration": {"claimed_ms": 45, "measured": self.auditor.measurements.get("User Registration")},
            "User Retrieval": {"claimed_ms": 25, "measured": self.auditor.measurements.get("User Retrieval")},
            "Preferences Update": {"claimed_ms": 55, "measured": self.auditor.measurements.get("Preferences Update")}
        }
        
        print("\n🎯 PERFORMANCE CLAIMS VERIFICATION:")
        print("-" * 60)
        
        performance_verdict = "MEETS"
        critical_issues = []
        
        for operation, data in claims.items():
            if data["measured"]:
                claimed = data["claimed_ms"]
                actual_mean = data["measured"]["mean_ms"]
                actual_p95 = data["measured"]["p95_ms"]
                
                # Use P95 for production readiness (more realistic than mean)
                status = "✅ MEETS" if actual_p95 <= claimed * 1.2 else "❌ FAILS"  # 20% tolerance
                if actual_p95 > claimed * 1.2:
                    performance_verdict = "FAILS"
                    critical_issues.append(f"{operation}: P95 {actual_p95:.1f}ms > {claimed * 1.2:.1f}ms")
                
                deviation_mean = ((actual_mean - claimed) / claimed) * 100
                deviation_p95 = ((actual_p95 - claimed) / claimed) * 100
                
                print(f"{operation:.<25} {claimed}ms")
                print(f"{'Mean':>25}: {actual_mean:.1f}ms ({deviation_mean:+.1f}%)")
                print(f"{'P95':>25}: {actual_p95:.1f}ms ({deviation_p95:+.1f}%) {status}")
                print()
            else:
                print(f"{operation:.<25} ❌ MEASUREMENT FAILED")
                performance_verdict = "FAILS"
                critical_issues.append(f"{operation}: Measurement completely failed")
        
        # Suspicious claims analysis
        print(f"\n🚨 SUSPICIOUS CLAIMS ANALYSIS:")
        print("-" * 60)
        
        bulk_measured = self.auditor.measurements.get("Bulk Operations (50 users)")
        retrieval_measured = self.auditor.measurements.get("User Retrieval")
        
        mathematical_issue = False
        if bulk_measured and retrieval_measured:
            bulk_per_user = bulk_measured["mean_ms"] / 50
            single_user = retrieval_measured["mean_ms"]
            
            print(f"Single User Retrieval: {single_user:.2f}ms")
            print(f"Bulk Per User (measured): {bulk_per_user:.2f}ms") 
            print(f"Bulk Claim (1.9ms/user): {'VERIFIED' if bulk_per_user <= 1.9 * 1.5 else 'SUSPICIOUS'}")
            
            if bulk_per_user >= single_user * 0.8:  # Bulk should be much more efficient
                print("⚠️  WARNING: Bulk operations show minimal efficiency gain")
                mathematical_issue = True
            else:
                print("🔍 FINDING: Bulk operations ARE more efficient (as expected)")
                
            # Check the mathematical impossibility claim
            if single_user > 20 and bulk_per_user < 5:  # Reasonable efficiency expectations
                print("✅ BULK EFFICIENCY: Mathematically reasonable")
            else:
                print("❌ BULK EFFICIENCY: Claims don't align with single-user performance")
                mathematical_issue = True
        
        # Event Bus overhead analysis
        print(f"\n🔗 EVENT BUS INTEGRATION ANALYSIS:")
        print("-" * 60)
        
        with_events = self.auditor.measurements.get("Registration (with Events)")
        without_events = self.auditor.measurements.get("Registration (no Events)")
        
        if with_events and without_events:
            overhead = with_events['mean_ms'] - without_events['mean_ms']
            overhead_percentage = (overhead / without_events['mean_ms']) * 100
            
            print(f"Event Bus Overhead: {overhead:.2f}ms ({overhead_percentage:.1f}%)")
            if overhead_percentage > 20:
                print("⚠️  WARNING: High Event Bus overhead detected")
                critical_issues.append(f"Event Bus adds {overhead:.1f}ms ({overhead_percentage:.1f}%) overhead")
            else:
                print("✅ Event Bus overhead within acceptable limits")
        
        # Production readiness assessment
        print(f"\n🎯 PRODUCTION READINESS ASSESSMENT:")
        print("-" * 60)
        
        if critical_issues:
            print("❌ CRITICAL ISSUES FOUND:")
            for issue in critical_issues:
                print(f"   - {issue}")
        
        if mathematical_issue:
            print("❌ MATHEMATICAL INCONSISTENCIES in bulk operation claims")
        
        # Compare to GamificationService baseline
        gamification_baseline = 0.69  # ms
        print(f"\n📊 BASELINE COMPARISON (GamificationService: {gamification_baseline}ms):")
        print("-" * 60)
        
        for operation, data in claims.items():
            if data["measured"]:
                mean_ms = data["measured"]["mean_ms"]
                multiplier = mean_ms / gamification_baseline
                print(f"{operation:.<25} {multiplier:.1f}x slower than baseline")
        
        # Final verdict
        print(f"\n🎯 FINAL PERFORMANCE VERDICT:")
        print("=" * 60)
        
        if performance_verdict == "MEETS" and not critical_issues and not mathematical_issue:
            print("✅ PERFORMANCE CLAIMS VERIFIED")
            print("📋 RECOMMENDATION: GO for production with real DB testing")
            verdict = "CONDITIONAL GO"
        else:
            print("❌ PERFORMANCE CLAIMS HAVE ISSUES")
            print("🚨 RECOMMENDATION: NO-GO - Address issues before production")
            verdict = "NO-GO"
        
        print(f"\n🔧 AUDIT METHODOLOGY: Realistic database delays simulated")
        print(f"⚠️  LIMITATION: Real PostgreSQL testing still required for final validation")
        print(f"📊 CONFIDENCE LEVEL: High for relative performance, Medium for absolute values")
        
        print("\n" + "="*100)
        print(f"FINAL AUDIT VERDICT: {verdict}")
        print("="*100)
        
        return verdict


# Test runner
@pytest.mark.asyncio
async def test_complete_userservice_performance_audit():
    """Execute complete UserService performance audit with fixed environment"""
    audit = UserServicePerformanceAudit()
    results = await audit.run_complete_audit()
    
    # Assert that audit completed and returned results
    assert results is not None
    assert isinstance(results, dict)
    
    # Verify that key audits were performed
    expected_audits = ["registration", "retrieval", "preferences", "bulk", "concurrent"]
    for audit_name in expected_audits:
        assert audit_name in results, f"Missing audit: {audit_name}"
    
    print("✅ UserService Performance Audit Completed Successfully")


if __name__ == "__main__":
    """Run performance audit directly"""
    async def main():
        audit = UserServicePerformanceAudit()
        await audit.run_complete_audit()
    
    asyncio.run(main())