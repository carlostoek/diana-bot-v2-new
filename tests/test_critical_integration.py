"""
Red de Seguridad - Tests de Integración Críticos
Este archivo contiene tests que validan la funcionalidad básica del sistema.
Si estos tests fallan, el sistema tiene problemas fundamentales.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from src.core.event_bus import EventBus
from src.modules.user.service import UserService
from src.modules.user.models import User, TelegramUser
from src.services.gamification.service import GamificationService
from src.core.events import UserEvent


@pytest.fixture
def mock_user_repository():
    """Mock repository que simula operaciones de base de datos."""
    repo = MagicMock()
    
    # Simula usuario existente
    existing_user = User()
    existing_user.id = 123456789
    existing_user.first_name = "Test"
    existing_user.username = "testuser"
    existing_user.role = "free"
    existing_user.is_admin = False
    
    repo.get_user_by_id.return_value = existing_user
    repo.create_user.return_value = existing_user
    repo.update_user.return_value = existing_user
    
    return repo


@pytest.fixture
def mock_gamification_repository():
    """Mock repository para gamificación."""
    repo = MagicMock()
    repo.get_user_gamification_stats.return_value = None
    repo.create_or_update_user_gamification_stats.return_value = None
    return repo


@pytest.fixture
async def event_bus():
    """Event bus en modo test."""
    bus = EventBus(test_mode=True)
    await bus.initialize()
    yield bus
    await bus.cleanup()


@pytest.fixture
def user_service(mock_user_repository, event_bus):
    """Servicio de usuario configurado."""
    return UserService(mock_user_repository, event_bus)


@pytest.fixture
def gamification_service(mock_gamification_repository, event_bus):
    """Servicio de gamificación configurado."""
    return GamificationService(event_bus, mock_gamification_repository)


class TestCriticalSystemIntegration:
    """Tests críticos que deben pasar siempre."""
    
    async def test_event_bus_basic_functionality(self, event_bus):
        """Test crítico: Event Bus debe funcionar básicamente."""
        # Test 1: Publicar evento simple
        event = UserEvent(
            user_id=123,
            event_type="login",
            user_data={"test": "data"}
        )
        
        # No debe lanzar excepción
        await event_bus.publish(event)
        
        # Test 2: Suscripción básica
        handler_called = False
        
        async def test_handler(event):
            nonlocal handler_called
            handler_called = True
            
        await event_bus.subscribe("test", test_handler)
        await event_bus.publish(event)
        
        # Esperar procesamiento
        await asyncio.sleep(0.01)
        assert handler_called, "Handler no fue llamado"
    
    async def test_user_service_basic_operations(self, user_service):
        """Test crítico: UserService operaciones básicas."""
        # Test 1: Obtener usuario existente
        user = user_service.get_user_by_id(123456789)
        assert user is not None, "No se pudo obtener usuario existente"
        assert user.id == 123456789
        
        # Test 2: Crear o encontrar usuario
        telegram_user = TelegramUser(
            id=987654321,
            first_name="New User",
            last_name="Test",
            username="newuser"
        )
        
        new_user = await user_service.find_or_create_user(
            telegram_user.id,
            telegram_user.first_name,
            telegram_user.last_name,
            telegram_user.username
        )
        
        assert new_user is not None, "No se pudo crear usuario"
        
        # Test 3: Verificar permisos
        is_admin = user_service.is_admin(123456789)
        assert isinstance(is_admin, bool), "is_admin debe retornar boolean"
        
        has_role = user_service.has_role(123456789, "free")
        assert isinstance(has_role, bool), "has_role debe retornar boolean"
    
    async def test_gamification_service_initialization(self, gamification_service):
        """Test crítico: GamificationService debe inicializar correctamente."""
        # Test inicialización
        await gamification_service.initialize()
        assert gamification_service._initialized, "Servicio no se inicializó"
        
        # Test health check
        health = await gamification_service.health_check()
        assert health["status"] == "ok", "Health check falló"
    
    async def test_event_driven_integration(self, event_bus, user_service, gamification_service):
        """Test crítico: Integración event-driven entre servicios."""
        # Inicializar gamificación
        await gamification_service.initialize()
        
        # Simular registro de usuario
        events_received = []
        
        async def event_collector(event):
            events_received.append(event)
        
        await event_bus.subscribe("user.*", event_collector)
        
        # Crear usuario (debe generar evento)
        await user_service.find_or_create_user(
            999888777,
            "Integration Test",
            "User",
            "integrationtest"
        )
        
        # Esperar procesamiento de eventos
        await asyncio.sleep(0.1)
        
        # Verificar que se generó evento
        assert len(events_received) > 0, "No se generaron eventos de usuario"
        
        # Verificar tipo de evento
        user_event = events_received[0]
        assert hasattr(user_event, 'data'), "Evento no tiene data"
        assert 'user_id' in user_event.data, "Evento no tiene user_id"


class TestSystemComponentHealth:
    """Tests de salud de componentes del sistema."""
    
    async def test_event_bus_health_check(self, event_bus):
        """Verificar salud del Event Bus."""
        health = await event_bus.health_check()
        
        # Verificaciones críticas
        assert "status" in health, "Health check debe incluir status"
        assert health["status"] in ["healthy", "degraded", "unhealthy"], "Status inválido"
        assert "subscribers_count" in health, "Debe incluir conteo de suscriptores"
        assert isinstance(health["subscribers_count"], int), "Conteo debe ser entero"
    
    async def test_event_bus_statistics(self, event_bus):
        """Verificar métricas del Event Bus."""
        stats = await event_bus.get_statistics()
        
        # Verificaciones de métricas críticas
        required_metrics = [
            "total_events_published",
            "total_subscribers", 
            "events_by_type",
            "failed_publishes",
            "failed_handlers"
        ]
        
        for metric in required_metrics:
            assert metric in stats, f"Métrica {metric} faltante"
    
    def test_user_service_rate_limiting(self, user_service):
        """Test de rate limiting del UserService."""
        user_id = 123456789
        
        # Verificar que rate limiting funciona
        for _ in range(5):
            is_limited = user_service.is_rate_limited(user_id)
            assert isinstance(is_limited, bool), "Rate limiting debe retornar boolean"


class TestDataIntegrity:
    """Tests de integridad de datos."""
    
    def test_user_model_data_integrity(self):
        """Verificar que los modelos de usuario mantienen integridad."""
        # Test TelegramUser dataclass
        telegram_user = TelegramUser(
            id=123,
            first_name="Test",
            last_name="User", 
            username="testuser"
        )
        
        assert telegram_user.id == 123
        assert telegram_user.first_name == "Test"
        assert telegram_user.last_name == "User"
        assert telegram_user.username == "testuser"
    
    def test_user_event_serialization(self):
        """Verificar que eventos se pueden serializar/deserializar."""
        event = UserEvent(
            user_id=123,
            event_type="registered",
            user_data={"test": "data"}
        )
        
        # Test serialización
        json_data = event.to_json()
        assert isinstance(json_data, str), "Event debe serializar a string"
        assert "user_id" in json_data, "JSON debe contener user_id"
        assert "event_type" in json_data, "JSON debe contener event_type"


@pytest.mark.asyncio
async def test_full_system_smoke_test():
    """Test de humo del sistema completo - Debe ejecutarse sin errores."""
    
    # Setup básico
    event_bus = EventBus(test_mode=True)
    await event_bus.initialize()
    
    try:
        # Test Event Bus
        health = await event_bus.health_check()
        assert health["status"] in ["healthy", "degraded"]
        
        # Test publicación básica
        event = UserEvent(
            user_id=999,
            event_type="login", 
            user_data={"test": True}
        )
        
        await event_bus.publish(event)
        
        # Test estadísticas
        stats = await event_bus.get_statistics()
        assert stats["total_events_published"] >= 1
        
        print("✅ Sistema básico funcionando correctamente")
        
    finally:
        await event_bus.cleanup()


if __name__ == "__main__":
    # Permite ejecutar directamente para validación rápida
    asyncio.run(test_full_system_smoke_test())