# PRD - User Service

## 1. Resumen Ejecutivo
El User Service es el componente central para la gestión automática de usuarios en el bot de Telegram. Se encarga del registro automático, autenticación silenciosa y gestión de perfiles de usuario sin requerir intervención manual del usuario.

Principio clave: Registro transparente e inmediato sin fricción para el usuario.

## 2. Objetivos del Producto

### 2.1 Objetivo Principal
Proporcionar un sistema de gestión de usuarios completamente automático que registre y autentique usuarios basándose únicamente en su interacción con el bot de Telegram.

### 2.2 Objetivos Específicos
- **Registro Zero-Friction:** Los usuarios son registrados automáticamente en su primera interacción
- **Persistencia de Identidad:** Mantener información consistente del usuario a través de sesiones
- **Gestión de Roles:** Asignar y gestionar roles automáticamente (free, vip, admin)
- **Recuperación Automática:** Recuperar usuarios existentes sin duplicación

## 3. Casos de Uso

### 3.1 Caso de Uso Principal: Registro Automático
- **Actor:** Usuario nuevo
- **Flujo:**
  1. Usuario envía cualquier mensaje/interacción al bot
  2. UserRegistrationMiddleware intercepta la interacción
  3. Sistema extrae información del objeto Telegram User
  4. Sistema crea nuevo registro en BD automáticamente
  5. Usuario queda registrado y autenticado para futuras interacciones
- **Datos capturados automáticamente:**
  - user_id (ID único de Telegram)
  - first_name (nombre de Telegram)
  - last_name (apellido de Telegram, opcional)
  - username (username de Telegram, opcional)
  - role (por defecto: 'free')
  - created_at (timestamp automático)

### 3.2 Caso de Uso: Usuario Existente
- **Actor:** Usuario registrado previamente
- **Flujo:**
  1. Usuario interactúa con el bot
  2. Middleware identifica usuario existente por user_id
  3. Sistema recupera información del usuario desde BD
  4. Información actualizada está disponible para el handler

### 3.3 Caso de Uso: Gestión de Roles
- **Actor:** Sistema automático
- **Flujo:**
  1. Sistema evalúa estado del usuario (suscripciones, permisos)
  2. Determina rol apropiado (free/vip/admin)
  3. Actualiza rol automáticamente si es necesario
  4. Mantiene jerarquía de roles (admin > vip > free)

## 4. Requerimientos Funcionales

### 4.1 Registro de Usuario
- **RF001:** El sistema DEBE registrar automáticamente cualquier usuario que interactúe por primera vez
- **RF002:** El registro DEBE completarse sin requerir información adicional del usuario
- **RF003:** El sistema DEBE usar el ID de Telegram como identificador único primario
- **RF004:** El sistema DEBE asignar rol 'free' por defecto a usuarios nuevos
- **RF005:** El registro DEBE ser idempotente (no crear duplicados)

### 4.2 Autenticación Silenciosa
- **RF006:** El sistema DEBE identificar automáticamente usuarios en cada interacción
- **RF007:** El sistema DEBE recuperar información de usuario existente sin latencia perceptible
- **RF008:** El sistema DEBE manejar múltiples tipos de interacción (mensajes, callbacks, reacciones)

### 4.3 Gestión de Perfiles
- **RF009:** El sistema DEBE almacenar información básica del perfil de Telegram
- **RF010:** El sistema DEBE permitir actualización automática de información de perfil
- **RF011:** El sistema DEBE mantener historial de cambios importantes (cambio de rol)

### 4.4 Gestión de Roles
- **RF012:** El sistema DEBE soportar roles jerárquicos (admin > vip > free)
- **RF013:** El sistema DEBE actualizar roles automáticamente basado en suscripciones/permisos
- **RF014:** El sistema DEBE prevenir degradación accidental de roles superiores
- **RF015:** El sistema DEBE validar permisos de admin mediante lista autorizada

## 5. Requerimientos No Funcionales

### 5.1 Rendimiento
- **RNF001:** El registro de usuario DEBE completarse en < 100ms
- **RNF002:** La recuperación de usuario existente DEBE completarse en < 50ms
- **RNF003:** El middleware DEBE procesar 1000+ usuarios concurrentes sin degradación

### 5.2 Disponibilidad
- **RNF004:** El servicio DEBE tener 99.9% de uptime
- **RNF005:** El sistema DEBE continuar operando aunque el registro falle (degradación elegante)
- **RNF006:** Errores de BD NO DEBEN interrumpir el flujo del middleware

### 5.3 Seguridad
- **RNF007:** Solo usuarios con ID válido de Telegram pueden ser registrados
- **RNF008:** Información sensible DEBE ser loggeada apropiadamente (sin PII en logs)
- **RNF009:** Cambios de rol DEBEN ser auditados y loggeados

### 5.4 Confiabilidad
- **RNF010:** El sistema DEBE manejar gracefully errores de conexión a BD
- **RNF011:** El middleware DEBE continuar funcionando aunque UserService falle
- **RNF012:** Recovery automático de usuarios inconsistentes

## 6. Arquitectura Técnica

### 6.1 Componentes Principales
UserRegistrationMiddleware ↓ UserService ↓ User Model (SQLAlchemy) ↓ PostgreSQL Database

### 6.2 Flujo de Datos
1. **Intercepción:** Middleware intercepta todas las interacciones
2. **Extracción:** Extrae información del objeto Telegram User
3. **Validación:** Verifica si usuario existe en BD
4. **Procesamiento:** Crea nuevo usuario o recupera existente
5. **Enriquecimiento:** Añade objeto User al contexto del handler

### 6.3 Integraciones
- Telegram API: Fuente primaria de información de usuario
- Base de Datos: Persistencia de información de usuario
- Sistema de Roles: Integración con gestión de permisos
- Event Bus: Publicación de eventos de registro/actualización

## 7. Modelo de Datos

### 7.1 Entidad Principal: User
```
users:
- id (BIGINT, PRIMARY KEY) -- Telegram User ID
- first_name (VARCHAR, NOT NULL)
- last_name (VARCHAR, NULLABLE)
- username (VARCHAR, NULLABLE)
- role (VARCHAR, DEFAULT 'free')
- is_admin (BOOLEAN, DEFAULT false)
- created_at (TIMESTAMP, DEFAULT NOW())
- updated_at (TIMESTAMP, DEFAULT NOW())
```

### 7.2 Restricciones
- id debe ser único (Telegram garantiza unicidad)
- role debe estar en ['free', 'vip', 'admin']
- first_name es obligatorio (Telegram lo garantiza)

## 8. Casos Límite y Manejo de Errores

### 8.1 Escenarios de Error
- Sin conexión a BD: Middleware continúa sin añadir usuario al contexto
- Usuario con datos incompletos: Usa valores por defecto para campos opcionales
- Conflicto de rol: Mantiene rol superior existente
- Timeout de BD: Log error y continúa sin registrar

### 8.2 Estrategias de Recuperación
- Retry automático: Para errores temporales de conexión
- Logging detallado: Para debugging y monitoreo
- Degradación elegante: Sistema funciona aunque registro falle
- Reconciliación: Proceso background corrige inconsistencias

## 9. Métricas y Monitoreo

### 9.1 Métricas Clave
- Tasa de registro: Usuarios nuevos por día/hora
- Latencia de registro: Tiempo promedio de registro
- Tasa de error: Porcentaje de registros fallidos
- Usuarios activos: Usuarios únicos por período

### 9.2 Alertas
- Alta latencia: > 200ms promedio en 5 minutos
- Tasa de error alta: > 5% errores en 10 minutos
- Falla de BD: Imposibilidad de conectar por > 1 minuto

## 10. Plan de Implementación

### 10.1 Fases
- Fase 1: Middleware básico de registro ✅
- Fase 2: Gestión de roles automática ✅
- Fase 3: Auditoría y logging mejorado
- Fase 4: Reconciliación y monitoreo avanzado

### 10.2 Criterios de Éxito
- Registro automático funcionando: 100% de usuarios registrados en primera interacción
- Zero downtime: Ninguna interrupción del servicio durante implementación
- Performance mantenido: Latencia < 100ms para 95% de registros
- Datos íntegros: 0 duplicados, 0 usuarios con roles inconsistentes

## 11. Consideraciones de Escalabilidad
- Particionamiento: Preparado para sharding por rango de user_id
- Caching: Redis para usuarios frecuentemente accedidos
- Batch processing: Para operaciones masivas de actualización de roles
- Connection pooling: Para optimizar conexiones a BD bajo carga