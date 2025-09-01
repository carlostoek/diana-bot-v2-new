#!/usr/bin/env python3
"""
Validador de Red de Seguridad - Diana Bot V2
Script de validación rápida que no requiere todas las dependencias.
"""

import sys
import os
import asyncio
from pathlib import Path

# Configurar PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_basic_imports():
    """Test 1: Importaciones básicas deben funcionar."""
    print("🔍 Validando importaciones básicas...")
    
    try:
        from src.core.event_bus import EventBus
        print("  ✅ EventBus importado")
        
        from src.modules.user.models import User, TelegramUser, UserState
        print("  ✅ Modelos de usuario importados")
        
        from src.core.events import UserEvent
        print("  ✅ Eventos importados")
        
        from src.modules.user.service import UserService
        print("  ✅ UserService importado")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error en importaciones: {e}")
        return False

def test_model_creation():
    """Test 2: Modelos se pueden crear correctamente."""
    print("🔍 Validando creación de modelos...")
    
    try:
        from src.modules.user.models import TelegramUser, UserState
        
        # Test TelegramUser
        user = TelegramUser(
            id=123456789,
            first_name="Test",
            last_name="User",
            username="testuser"
        )
        assert user.id == 123456789
        assert user.first_name == "Test"
        print("  ✅ TelegramUser creado correctamente")
        
        # Test UserState enum
        assert UserState.NEW.value == "new"
        assert UserState.ACTIVE.value == "active"
        print("  ✅ UserState enum funcionando")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error creando modelos: {e}")
        return False

async def test_event_bus_basic():
    """Test 3: Event Bus básico funciona."""
    print("🔍 Validando Event Bus básico...")
    
    try:
        from src.core.event_bus import EventBus
        from src.core.events import UserEvent
        
        # Crear y inicializar
        bus = EventBus(test_mode=True)
        await bus.initialize()
        print("  ✅ EventBus inicializado")
        
        # Test health check
        health = await bus.health_check()
        assert isinstance(health, dict)
        assert "status" in health
        print("  ✅ Health check responde")
        
        # Test publicación
        event = UserEvent(
            user_id=123,
            event_type="registered",
            user_data={"test": "data"}
        )
        await bus.publish(event)
        print("  ✅ Evento publicado")
        
        # Test estadísticas
        stats = await bus.get_statistics()
        assert stats["total_events_published"] >= 1
        print("  ✅ Estadísticas funcionando")
        
        await bus.cleanup()
        print("  ✅ Cleanup exitoso")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error en Event Bus: {e}")
        return False

def test_event_serialization():
    """Test 4: Serialización de eventos funciona."""
    print("🔍 Validando serialización de eventos...")
    
    try:
        from src.core.events import UserEvent
        
        event = UserEvent(
            user_id=123456789,
            event_type="registered",
            user_data={"username": "test", "first_name": "Test"}
        )
        
        # Test serialización
        json_str = event.to_json()
        assert isinstance(json_str, str)
        assert "user_id" in json_str
        assert "registered" in json_str
        print("  ✅ Serialización JSON OK")
        
        # Test que el evento tiene atributos requeridos
        assert hasattr(event, 'id')
        assert hasattr(event, 'type')
        assert hasattr(event, 'timestamp')
        assert hasattr(event, 'data')
        print("  ✅ Atributos de evento OK")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error en serialización: {e}")
        return False

async def test_service_basic_creation():
    """Test 5: Servicios se pueden crear sin errores."""
    print("🔍 Validando creación básica de servicios...")
    
    try:
        from unittest.mock import MagicMock
        from src.modules.user.service import UserService
        from src.core.event_bus import EventBus
        
        # Mock dependencies
        mock_repo = MagicMock()
        bus = EventBus(test_mode=True)
        
        # Crear UserService
        user_service = UserService(mock_repo, bus)
        assert user_service is not None
        assert user_service.user_repository is mock_repo
        print("  ✅ UserService creado")
        
        # Test rate limiting básico
        is_limited = user_service.is_rate_limited(123)
        assert isinstance(is_limited, bool)
        print("  ✅ Rate limiting funciona")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error creando servicios: {e}")
        return False

async def run_safety_validation():
    """Ejecutar validación completa de la red de seguridad."""
    print("🛡️ INICIANDO VALIDACIÓN DE RED DE SEGURIDAD")
    print("=" * 50)
    
    all_passed = True
    
    # Test 1: Importaciones
    if not test_basic_imports():
        all_passed = False
    
    # Test 2: Modelos
    if not test_model_creation():
        all_passed = False
    
    # Test 3: Event Bus
    if not await test_event_bus_basic():
        all_passed = False
    
    # Test 4: Serialización
    if not test_event_serialization():
        all_passed = False
    
    # Test 5: Servicios
    if not await test_service_basic_creation():
        all_passed = False
    
    print("=" * 50)
    
    if all_passed:
        print("🟢 RED DE SEGURIDAD: TODOS LOS TESTS PASARON")
        print("✅ Sistema básico funcionando correctamente")
        print("✅ Es seguro continuar con el desarrollo")
    else:
        print("🔴 RED DE SEGURIDAD: ALGUNOS TESTS FALLARON")
        print("❌ Hay problemas fundamentales en el sistema")
        print("❌ NO ES SEGURO continuar sin resolver estos problemas")
    
    return all_passed

def create_quick_validation_script():
    """Crear script de validación rápida."""
    script_content = '''#!/bin/bash
# Validación rápida de red de seguridad
cd "$(dirname "$0")/.."
source venv/bin/activate
export PYTHONPATH="$(pwd)"
python tests/validate_safety_net.py
'''
    
    script_path = project_root / "validate_system.sh"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    os.chmod(script_path, 0o755)
    print(f"📝 Script de validación creado: {script_path}")

if __name__ == "__main__":
    # Crear script de validación
    create_quick_validation_script()
    
    # Ejecutar validación
    result = asyncio.run(run_safety_validation())
    
    if result:
        print("\n🎯 PRÓXIMOS PASOS:")
        print("1. Ejecutar: ./validate_system.sh antes de hacer cambios")
        print("2. Si falla, investigar el componente específico")
        print("3. Usar tests de regresión después de modificaciones")
    else:
        print("\n🚨 ACCIÓN REQUERIDA:")
        print("1. Resolver los errores mostrados arriba")
        print("2. Instalar dependencias faltantes")
        print("3. Volver a ejecutar validación")
    
    sys.exit(0 if result else 1)