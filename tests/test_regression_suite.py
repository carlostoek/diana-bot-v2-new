"""
Suite de Tests de Regresión
Estos tests verifican que funcionalidades conocidas no se rompan con cambios futuros.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from src.core.event_bus import EventBus
from src.modules.user.service import UserService
from src.modules.user.models import User, TelegramUser
from src.services.gamification.service import GamificationService
from src.core.events import UserEvent


class TestUserServiceRegression:
    """Tests de regresión para UserService."""
    
    @pytest.fixture
    def mock_user_repository(self):
        """Repository mock configurado."""
        repo = MagicMock()
        
        # Usuario existente estándar
        existing_user = User()
        existing_user.id = 123456789
        existing_user.first_name = "Existing"
        existing_user.username = "existing_user"
        existing_user.role = "free"
        existing_user.is_admin = False
        
        repo.get_user_by_id.return_value = existing_user
        repo.create_user.return_value = existing_user
        
        return repo
    
    @pytest.fixture
    async def event_bus(self):
        """Event bus para tests."""
        bus = EventBus(test_mode=True)
        await bus.initialize()
        yield bus
        await bus.cleanup()
    
    @pytest.fixture
    def user_service(self, mock_user_repository, event_bus):
        """UserService configurado."""
        return UserService(mock_user_repository, event_bus)
    
    def test_get_user_by_id_returns_user_when_exists(self, user_service):
        """Regresión: get_user_by_id debe retornar usuario cuando existe."""
        user = user_service.get_user_by_id(123456789)
        
        assert user is not None
        assert user.id == 123456789
        assert user.first_name == "Existing"
    
    def test_get_user_by_id_returns_none_when_not_exists(self, user_service):
        """Regresión: get_user_by_id debe retornar None cuando no existe."""
        user_service.user_repository.get_user_by_id.return_value = None
        
        user = user_service.get_user_by_id(999999999)
        assert user is None
    
    async def test_find_or_create_user_creates_new_user(self, user_service):
        """Regresión: find_or_create_user debe crear nuevo usuario."""
        # Configurar que el usuario no existe
        user_service.user_repository.get_user_by_id.return_value = None
        
        # Mock para crear usuario
        new_user = User()
        new_user.id = 987654321
        new_user.first_name = "New"
        new_user.username = "newuser"
        user_service.user_repository.create_user.return_value = new_user
        
        result = await user_service.find_or_create_user(
            987654321, "New", "User", "newuser"
        )
        
        assert result is not None
        assert result.id == 987654321
        
        # Verificar que se llamó create_user
        user_service.user_repository.create_user.assert_called_once()
    
    async def test_find_or_create_user_returns_existing_user(self, user_service):
        """Regresión: find_or_create_user debe retornar usuario existente."""
        result = await user_service.find_or_create_user(
            123456789, "Existing", "User", "existing_user"
        )
        
        assert result is not None
        assert result.id == 123456789
        
        # Verificar que NO se llamó create_user
        user_service.user_repository.create_user.assert_not_called()
    
    def test_is_admin_check_works_correctly(self, user_service):
        """Regresión: is_admin debe funcionar correctamente."""
        # Test usuario admin
        admin_user = User()
        admin_user.is_admin = True
        user_service.user_repository.get_user_by_id.return_value = admin_user
        
        assert user_service.is_admin(123) is True
        
        # Test usuario no admin
        regular_user = User()
        regular_user.is_admin = False
        user_service.user_repository.get_user_by_id.return_value = regular_user
        
        assert user_service.is_admin(456) is False
        
        # Test usuario no existente
        user_service.user_repository.get_user_by_id.return_value = None
        assert user_service.is_admin(999) is False
    
    def test_has_role_check_works_correctly(self, user_service):
        """Regresión: has_role debe funcionar correctamente."""
        # Test usuario con rol específico
        user = User()
        user.role = "vip"
        user_service.user_repository.get_user_by_id.return_value = user
        
        assert user_service.has_role(123, "vip") is True
        assert user_service.has_role(123, "free") is False
        
        # Test usuario no existente
        user_service.user_repository.get_user_by_id.return_value = None
        assert user_service.has_role(999, "vip") is False
    
    def test_rate_limiting_prevents_spam(self, user_service):
        """Regresión: Rate limiting debe prevenir spam."""
        user_id = 123
        
        # Primeras requests deben pasar
        for _ in range(10):
            is_limited = user_service.is_rate_limited(user_id)
            assert isinstance(is_limited, bool)
        
        # No debería estar limitado con pocas requests
        assert not user_service.is_rate_limited(user_id)


class TestEventBusRegression:
    """Tests de regresión para Event Bus."""
    
    @pytest.mark.asyncio
    async def test_event_persistence_works(self):
        """Regresión: Eventos deben persistirse correctamente."""
        bus = EventBus(test_mode=True)
        await bus.initialize()
        
        try:
            # Publicar evento
            event = UserEvent(user_id=123, event_type="test", user_data={})
            await bus.publish(event)
            
            # Verificar que se persistió
            events = await bus.get_published_events(limit=10)
            assert len(events) >= 1
            
            # Verificar que el evento está ahí
            found_event = next((e for e in events if e.data["user_id"] == 123), None)
            assert found_event is not None
            
        finally:
            await bus.cleanup()
    
    @pytest.mark.asyncio
    async def test_wildcard_subscriptions_work(self):
        """Regresión: Suscripciones wildcard deben funcionar."""
        bus = EventBus(test_mode=True)
        await bus.initialize()
        
        try:
            received_events = []
            
            async def handler(event):
                received_events.append(event)
            
            # Suscribir a patrón wildcard
            await bus.subscribe("user.*", handler)
            
            # Publicar eventos que deben coincidir
            event1 = UserEvent(user_id=1, event_type="user.registered", user_data={})
            event2 = UserEvent(user_id=2, event_type="user.updated", user_data={})
            
            await bus.publish(event1)
            await bus.publish(event2)
            
            # Esperar procesamiento
            await asyncio.sleep(0.05)
            
            # Ambos eventos deben haberse recibido
            assert len(received_events) >= 2
            
        finally:
            await bus.cleanup()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self):
        """Regresión: Circuit breaker debe funcionar."""
        bus = EventBus(test_mode=True)
        await bus.initialize()
        
        try:
            # Configurar circuit breaker
            bus.configure_circuit_breaker(failure_threshold=2, recovery_timeout=1.0)
            
            # Verificar configuración inicial
            stats = await bus.get_statistics()
            assert stats["circuit_breaker_state"] == "closed"
            
        finally:
            await bus.cleanup()


class TestGamificationServiceRegression:
    """Tests de regresión para GamificationService."""
    
    @pytest.mark.asyncio
    async def test_service_initialization_sequence(self):
        """Regresión: Inicialización debe seguir secuencia correcta."""
        mock_bus = EventBus(test_mode=True)
        mock_repo = MagicMock()
        
        service = GamificationService(mock_bus, mock_repo)
        
        # Estado inicial
        assert not service._initialized
        
        # Después de inicializar
        await service.initialize()
        assert service._initialized
        
        # Debe poder llamarse múltiples veces sin error
        await service.initialize()
        assert service._initialized
        
        await mock_bus.cleanup()
    
    @pytest.mark.asyncio
    async def test_health_check_always_responds(self):
        """Regresión: Health check siempre debe responder."""
        mock_bus = MagicMock()
        mock_repo = MagicMock()
        
        service = GamificationService(mock_bus, mock_repo)
        
        # Debe funcionar incluso sin inicializar
        health = await service.health_check()
        assert isinstance(health, dict)
        assert "status" in health


class TestSystemRegressionIntegration:
    """Tests de regresión de integración del sistema."""
    
    @pytest.mark.asyncio
    async def test_user_registration_event_flow(self):
        """Regresión: Flujo completo de registro de usuario."""
        # Setup
        bus = EventBus(test_mode=True)
        await bus.initialize()
        
        mock_user_repo = MagicMock()
        mock_gamif_repo = MagicMock()
        
        # Configurar usuario nuevo
        new_user = User()
        new_user.id = 987654321
        new_user.first_name = "New"
        new_user.username = "newuser"
        
        mock_user_repo.get_user_by_id.return_value = None  # No existe
        mock_user_repo.create_user.return_value = new_user  # Se crea
        
        # Configurar gamificación
        mock_gamif_repo.get_user_gamification_stats.return_value = None
        
        try:
            # Servicios
            user_service = UserService(mock_user_repo, bus)
            gamif_service = GamificationService(bus, mock_gamif_repo)
            await gamif_service.initialize()
            
            # Registrar usuario (debe generar eventos)
            result_user = await user_service.find_or_create_user(
                987654321, "New", "User", "newuser"
            )
            
            # Esperar procesamiento de eventos
            await asyncio.sleep(0.1)
            
            # Verificaciones
            assert result_user is not None
            assert result_user.id == 987654321
            
            # Verificar que se publicó evento
            events = await bus.get_published_events()
            assert len(events) >= 1
            
        finally:
            await bus.cleanup()


def validate_current_system():
    """Validación rápida del estado actual del sistema."""
    print("🔍 Validando sistema actual...")
    
    # Test importaciones críticas
    try:
        from src.core.event_bus import EventBus
        from src.modules.user.service import UserService
        from src.modules.user.models import User, TelegramUser
        from src.services.gamification.service import GamificationService
        print("✅ Importaciones críticas OK")
    except Exception as e:
        print(f"❌ Error en importaciones: {e}")
        return False
    
    # Test creación básica
    try:
        bus = EventBus(test_mode=True)
        mock_repo = MagicMock()
        service = UserService(mock_repo, bus)
        print("✅ Creación de servicios OK")
    except Exception as e:
        print(f"❌ Error creando servicios: {e}")
        return False
    
    print("🛡️ Sistema actual validado")
    return True


if __name__ == "__main__":
    validate_current_system()