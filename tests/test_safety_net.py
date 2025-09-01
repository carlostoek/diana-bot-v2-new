"""
Red de Seguridad - Tests de Funcionamiento Básico
Estos tests verifican que los componentes críticos del sistema no se rompan.
"""

import pytest
import asyncio
from src.core.event_bus import EventBus
from src.core.events import UserEvent
from src.modules.user.models import User, TelegramUser, UserState


class TestSystemSafetyNet:
    """Red de seguridad para validar que el sistema básico funciona."""
    
    @pytest.mark.asyncio
    async def test_event_bus_can_initialize(self):
        """CRÍTICO: Event Bus debe poder inicializarse."""
        bus = EventBus(test_mode=True)
        try:
            await bus.initialize()
            assert bus._is_connected, "Event Bus no se conectó"
        finally:
            await bus.cleanup()
    
    @pytest.mark.asyncio 
    async def test_event_bus_can_publish_simple_event(self):
        """CRÍTICO: Event Bus debe poder publicar eventos básicos."""
        bus = EventBus(test_mode=True)
        await bus.initialize()
        
        try:
            event = UserEvent(
                user_id=123,
                event_type="login",
                user_data={}
            )
            
            # No debe lanzar excepción
            await bus.publish(event)
            
            # Verificar que se almacenó
            stats = await bus.get_statistics()
            assert stats["total_events_published"] >= 1
            
        finally:
            await bus.cleanup()
    
    def test_user_models_basic_functionality(self):
        """CRÍTICO: Modelos de usuario deben instanciarse correctamente."""
        # Test TelegramUser dataclass
        telegram_user = TelegramUser(
            id=123456789,
            first_name="Test",
            last_name="User",
            username="testuser"
        )
        
        assert telegram_user.id == 123456789
        assert telegram_user.first_name == "Test"
        
        # Test UserState enum
        assert UserState.NEW.value == "new"
        assert UserState.ACTIVE.value == "active"
    
    @pytest.mark.asyncio
    async def test_user_event_serialization_works(self):
        """CRÍTICO: Eventos de usuario deben serializarse correctamente."""
        event = UserEvent(
            user_id=123,
            event_type="registered",
            user_data={"username": "test", "first_name": "Test"}
        )
        
        # Test serialización
        json_str = event.to_json()
        assert isinstance(json_str, str)
        assert "user_id" in json_str
        assert "event_type" in json_str
        assert "registered" in json_str
    
    @pytest.mark.asyncio
    async def test_event_bus_subscription_basic(self):
        """CRÍTICO: Suscripciones básicas deben funcionar."""
        bus = EventBus(test_mode=True)
        await bus.initialize()
        
        try:
            received_events = []
            
            async def handler(event):
                received_events.append(event)
            
            # Suscribir
            await bus.subscribe("test", handler)
            
            # Publicar
            event = UserEvent(
                user_id=123,
                event_type="login",
                user_data={}
            )
            await bus.publish(event)
            
            # Esperar procesamiento
            await asyncio.sleep(0.01)
            
            assert len(received_events) == 1
            assert received_events[0].data["user_id"] == 123
            
        finally:
            await bus.cleanup()
    
    @pytest.mark.asyncio
    async def test_system_imports_work(self):
        """CRÍTICO: Todas las importaciones críticas deben funcionar."""
        try:
            from src.core.event_bus import EventBus
            from src.core.events import UserEvent
            from src.modules.user.service import UserService
            from src.modules.user.models import User, TelegramUser
            from src.services.gamification.service import GamificationService
            
            # Si llegamos aquí, las importaciones funcionan
            assert True
            
        except ImportError as e:
            pytest.fail(f"Error crítico de importación: {e}")
    
    @pytest.mark.asyncio
    async def test_event_bus_health_check_responds(self):
        """CRÍTICO: Health check debe responder."""
        bus = EventBus(test_mode=True)
        await bus.initialize()
        
        try:
            health = await bus.health_check()
            assert isinstance(health, dict)
            assert "status" in health
            
        finally:
            await bus.cleanup()


def test_basic_dependency_availability():
    """CRÍTICO: Dependencias básicas deben estar disponibles."""
    try:
        import asyncio
        import json
        import logging
        import time
        from datetime import datetime
        from typing import Any, Dict, List
        from unittest.mock import MagicMock, AsyncMock
        
        # Si llegamos aquí, las dependencias están disponibles
        assert True
        
    except ImportError as e:
        pytest.fail(f"Dependencia crítica faltante: {e}")


if __name__ == "__main__":
    # Ejecución directa para validación rápida
    print("🔍 Ejecutando tests de red de seguridad...")
    
    # Test básico de importaciones
    test_basic_dependency_availability()
    print("✅ Dependencias básicas OK")
    
    # Test de modelos
    pytest.main([__file__ + "::TestSystemSafetyNet::test_user_models_basic_functionality", "-v"])
    
    print("🛡️ Red de seguridad básica validada")