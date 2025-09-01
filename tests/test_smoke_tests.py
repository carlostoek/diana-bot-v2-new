"""
Smoke Tests - Verificación Rápida de Funcionalidad
Estos tests verifican que las funcionalidades principales no están rotas.
Deben ejecutarse rápidamente y detectar problemas obvios.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch
from src.core.event_bus import EventBus
from src.modules.user.service import UserService
from src.modules.user.models import User, TelegramUser, UserState
from src.core.events import UserEvent


class TestEventBusSmoke:
    """Smoke tests para Event Bus."""
    
    @pytest.mark.asyncio
    async def test_can_create_and_initialize(self):
        """Event Bus se puede crear e inicializar."""
        bus = EventBus(test_mode=True)
        await bus.initialize()
        assert bus._is_connected
        await bus.cleanup()
    
    @pytest.mark.asyncio
    async def test_can_publish_without_subscribers(self):
        """Publicar evento sin suscriptores no debe fallar."""
        bus = EventBus(test_mode=True)
        await bus.initialize()
        
        try:
            event = UserEvent(user_id=1, event_type="test", user_data={})
            await bus.publish(event)  # No debe lanzar excepción
            
        finally:
            await bus.cleanup()
    
    @pytest.mark.asyncio
    async def test_statistics_are_available(self):
        """Estadísticas deben estar disponibles."""
        bus = EventBus(test_mode=True)
        await bus.initialize()
        
        try:
            stats = await bus.get_statistics()
            assert isinstance(stats, dict)
            assert "total_events_published" in stats
            
        finally:
            await bus.cleanup()


class TestUserServiceSmoke:
    """Smoke tests para UserService."""
    
    def test_can_create_user_service(self):
        """UserService se puede instanciar."""
        mock_repo = MagicMock()
        mock_bus = MagicMock()
        
        service = UserService(mock_repo, mock_bus)
        assert service is not None
        assert service.user_repository is mock_repo
        assert service.event_bus is mock_bus
    
    def test_rate_limiting_logic_works(self):
        """Rate limiting básico funciona."""
        mock_repo = MagicMock()
        mock_bus = MagicMock()
        service = UserService(mock_repo, mock_bus)
        
        # Test que no explote
        is_limited = service.is_rate_limited(123)
        assert isinstance(is_limited, bool)
    
    def test_admin_check_with_mock_user(self):
        """Verificación de admin funciona con usuario mock."""
        mock_repo = MagicMock()
        mock_bus = MagicMock()
        
        # Configurar usuario mock
        mock_user = MagicMock()
        mock_user.is_admin = True
        mock_repo.get_user_by_id.return_value = mock_user
        
        service = UserService(mock_repo, mock_bus)
        
        is_admin = service.is_admin(123)
        assert is_admin is True
        
        # Test usuario no existente
        mock_repo.get_user_by_id.return_value = None
        is_admin = service.is_admin(999)
        assert is_admin is False


class TestDataModelsSmoke:
    """Smoke tests para modelos de datos."""
    
    def test_telegram_user_creation(self):
        """TelegramUser se puede crear correctamente."""
        user = TelegramUser(
            id=123456789,
            first_name="Test",
            last_name="User",
            username="testuser"
        )
        
        assert user.id == 123456789
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.username == "testuser"
    
    def test_telegram_user_optional_fields(self):
        """TelegramUser funciona con campos opcionales."""
        # Solo campos requeridos
        user = TelegramUser(
            id=123456789,
            first_name="Test",
            last_name=None,
            username=None
        )
        
        assert user.id == 123456789
        assert user.first_name == "Test"
        assert user.last_name is None
        assert user.username is None
    
    def test_user_state_enum_values(self):
        """UserState enum tiene valores correctos."""
        assert UserState.NEW.value == "new"
        assert UserState.ONBOARDING.value == "onboarding" 
        assert UserState.ACTIVE.value == "active"
        assert UserState.INACTIVE.value == "inactive"


class TestEventModelsSmoke:
    """Smoke tests para modelos de eventos."""
    
    def test_user_event_creation(self):
        """UserEvent se puede crear correctamente."""
        event = UserEvent(
            user_id=123,
            event_type="registered",
            user_data={"test": "data"}
        )
        
        assert event.data["user_id"] == 123
        assert event.data["event_type"] == "registered"
        assert event.data["user_data"]["test"] == "data"
    
    def test_user_event_has_required_attributes(self):
        """UserEvent tiene atributos requeridos."""
        event = UserEvent(
            user_id=123,
            event_type="test",
            user_data={}
        )
        
        # Verificar que tiene los atributos básicos de IEvent
        assert hasattr(event, 'id')
        assert hasattr(event, 'type')
        assert hasattr(event, 'timestamp')
        assert hasattr(event, 'data')


class TestGamificationSmoke:
    """Smoke tests para servicio de gamificación."""
    
    @pytest.mark.asyncio
    async def test_can_create_gamification_service(self):
        """GamificationService se puede crear."""
        mock_bus = MagicMock()
        mock_repo = MagicMock()
        
        from src.services.gamification.service import GamificationService
        
        service = GamificationService(mock_bus, mock_repo)
        assert service is not None
        assert service.event_bus is mock_bus
        assert service.repository is mock_repo
    
    @pytest.mark.asyncio
    async def test_gamification_health_check_works(self):
        """Health check de gamificación funciona."""
        mock_bus = MagicMock()
        mock_repo = MagicMock()
        
        from src.services.gamification.service import GamificationService
        
        service = GamificationService(mock_bus, mock_repo)
        health = await service.health_check()
        
        assert isinstance(health, dict)
        assert "status" in health


def run_smoke_tests():
    """Ejecutar todos los smoke tests rápidamente."""
    print("🚀 Ejecutando smoke tests...")
    
    # Ejecutar tests sincrónicos
    test_models = TestDataModelsSmoke()
    test_models.test_telegram_user_creation()
    test_models.test_user_state_enum_values()
    print("✅ Modelos de datos OK")
    
    test_events = TestEventModelsSmoke()
    test_events.test_user_event_creation()
    test_events.test_user_event_has_required_attributes()
    print("✅ Modelos de eventos OK")
    
    print("🛡️ Smoke tests completados")


if __name__ == "__main__":
    run_smoke_tests()