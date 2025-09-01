# RED DE SEGURIDAD - DIANA BOT V2

## 🚨 ESTADO ACTUAL DEL PROYECTO (Sep 1, 2025)

### Componentes Implementados
- ✅ **Event Bus (Redis)**: Sistema completo de eventos con Redis pub/sub
- ✅ **User Service**: Gestión de usuarios con rate limiting y JWT
- ✅ **User Models**: TelegramUser, User (SQLAlchemy), UserState enum
- ✅ **Gamification Service**: Servicio básico con engines de puntos y logros
- ✅ **Core Events**: UserEvent y sistema de serialización
- ⚠️ **Narrative Service**: Implementación parcial
- ❌ **Database Layer**: Sin conexión real a PostgreSQL
- ❌ **Telegram Bot**: Sin implementación completa

### Puntos Críticos de Fallo Identificados

#### 1. **Database Connection** - CRÍTICO
- **Problema**: No hay conexión real a PostgreSQL
- **Impacto**: Todos los repositorios están mockeados
- **Detección**: `src/core/database.py` no implementado
- **Test de Validación**: Ejecutar cualquier test que requiera DB real

#### 2. **Event Bus Redis Connection** - ALTO
- **Problema**: En test_mode funciona, producción requiere Redis
- **Impacto**: Sin Redis, no hay comunicación entre servicios
- **Detección**: `src/core/event_bus.py:79` - redis_url por defecto
- **Test de Validación**: `tests/test_critical_integration.py::test_event_bus_health_check_responds`

#### 3. **Missing Dependencies** - MEDIO
- **Problema**: requirements.txt básico, faltan dependencias de producción
- **Impacto**: Imports fallarán en producción
- **Detección**: Importar redis, sqlalchemy, aiogram
- **Test de Validación**: `tests/test_safety_net.py::test_basic_dependency_availability`

#### 4. **Incomplete Service Implementations** - MEDIO
- **Problema**: Métodos NotImplementedError en servicios
- **Impacto**: Funcionalidades no disponibles
- **Detección**: Buscar "NotImplementedError" en codebase
- **Test de Validación**: Tests de funcionalidad específica

### Red de Seguridad Implementada

#### Tests Críticos
1. **`test_critical_integration.py`**
   - Validación de Event Bus básico
   - Integración UserService - EventBus
   - Flujo event-driven entre servicios
   - **Ejecución**: `pytest tests/test_critical_integration.py -v`

2. **`test_safety_net.py`**
   - Verificación de importaciones
   - Funcionalidad básica de componentes
   - Salud de Event Bus
   - **Ejecución**: `pytest tests/test_safety_net.py -v`

3. **`test_smoke_tests.py`**
   - Tests rápidos de componentes
   - Verificación de modelos de datos
   - Smoke tests de servicios
   - **Ejecución**: `python tests/test_smoke_tests.py`

4. **`test_regression_suite.py`**
   - Tests de regresión de funcionalidades conocidas
   - Validación de comportamientos esperados
   - **Ejecución**: `pytest tests/test_regression_suite.py -v`

### Comandos de Validación Rápida

#### Validación Completa
```bash
# Ejecutar toda la red de seguridad
pytest tests/test_critical_integration.py tests/test_safety_net.py tests/test_regression_suite.py -v

# Smoke test rápido
python tests/test_smoke_tests.py

# Validación de regresión
python tests/test_regression_suite.py
```

#### Validación por Componentes
```bash
# Solo Event Bus
pytest tests/test_critical_integration.py::TestCriticalSystemIntegration::test_event_bus_basic_functionality -v

# Solo User Service  
pytest tests/test_critical_integration.py::TestCriticalSystemIntegration::test_user_service_basic_operations -v

# Solo Gamification
pytest tests/test_critical_integration.py::TestCriticalSystemIntegration::test_gamification_service_initialization -v
```

### Indicadores de Alerta

#### 🔴 CRÍTICO - Detener Desarrollo
- Tests en `test_critical_integration.py` fallan
- Importaciones básicas fallan
- Event Bus no puede inicializar
- UserService no puede crear usuarios

#### 🟡 ADVERTENCIA - Investigar
- Tests de smoke fallan
- Health checks retornan "unhealthy"  
- Rate limiting no funciona
- Serialización de eventos falla

#### 🟢 OK - Continuar
- Todos los tests de la red de seguridad pasan
- Health checks retornan "healthy" o "degraded"
- Métricas del Event Bus funcionan
- Servicios pueden inicializarse

### Protocolo de Recuperación

#### Si la Red de Seguridad Falla:

1. **Ejecutar Diagnóstico Completo**
   ```bash
   pytest tests/ -v --tb=short
   ```

2. **Identificar Componente Roto**
   - Event Bus: `pytest tests/test_critical_integration.py::TestCriticalSystemIntegration::test_event_bus_basic_functionality`
   - User Service: `pytest tests/test_critical_integration.py::TestCriticalSystemIntegration::test_user_service_basic_operations`  
   - Gamification: `pytest tests/test_critical_integration.py::TestCriticalSystemIntegration::test_gamification_service_initialization`

3. **Rollback a Estado Conocido**
   ```bash
   git status
   git diff
   git checkout -- <archivos_modificados>
   ```

4. **Validar Recuperación**
   ```bash
   python tests/test_smoke_tests.py
   ```

### Archivos Críticos a Monitorear

#### No Modificar Sin Tests
- `src/core/event_bus.py` - Sistema de eventos
- `src/modules/user/service.py` - Lógica de usuarios
- `src/modules/user/models.py` - Modelos de datos
- `src/core/events.py` - Definiciones de eventos

#### Modificar Con Precaución
- `src/services/gamification/service.py` - Lógica de gamificación
- `src/core/interfaces.py` - Contratos de interfaces
- `src/core/exceptions.py` - Sistema de errores

### Métricas de Salud del Sistema

#### Event Bus
- `total_events_published` > 0
- `failed_publishes` = 0
- `circuit_breaker_state` = "closed"
- `status` = "healthy"

#### User Service
- `is_rate_limited()` retorna boolean
- `get_user_by_id()` no lanza excepciones
- `find_or_create_user()` completa sin errores

#### Gamification Service  
- `_initialized` = True después de initialize()
- `health_check()` retorna {"status": "ok"}

---

## 🛡️ CÓMO USAR ESTA RED DE SEGURIDAD

### Antes de Hacer Cambios
```bash
# Validar estado actual
python tests/test_smoke_tests.py
pytest tests/test_critical_integration.py -v
```

### Después de Hacer Cambios
```bash
# Validar que no rompiste nada
pytest tests/test_regression_suite.py -v
python tests/test_smoke_tests.py
```

### Si Algo Se Rompe
```bash
# Diagnóstico completo
pytest tests/ -v --tb=long

# Revisar última modificación
git diff HEAD~1

# Rollback si es necesario
git checkout HEAD~1 -- <archivo_problemático>
```

### Antes de Commit
```bash
# OBLIGATORIO - Ejecutar suite completa
pytest tests/test_critical_integration.py tests/test_safety_net.py tests/test_regression_suite.py -v

# Solo continuar si TODO pasa
```

---

**IMPORTANTE**: Esta red de seguridad debe ejecutarse antes de cualquier modificación significativa al código base. Si estos tests fallan, el sistema tiene problemas fundamentales que deben resolverse antes de continuar.