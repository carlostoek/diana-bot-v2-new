# Diana Bot V2 - Guía de Implementación Práctica con Claude Code

## 🎯 Cómo Aplicar la Planeación en el Mundo Real

Esta guía te muestra **paso a paso** cómo tomar toda la documentación estratégica y convertirla en código funcional usando Claude Code.

---

## 📋 **FASE 0: Preparación del Workspace (Día 1)**

### 1. **Setup del Repositorio**
```bash
# 1. Crear nuevo repositorio
mkdir diana-bot-v2-new
cd diana-bot-v2-new
git init

# 2. Estructura inicial
mkdir -p {src,docs,tests,scripts}
mkdir -p src/{core,modules,infrastructure,bot}
mkdir -p docs/{architecture,planning,api}

# 3. Configuración básica
touch {README.md,.env.example,.gitignore,requirements.txt}
```

### 2. **Documentación en el Workspace**
```bash
# Crear carpeta docs/planning/ con TODA la documentación
docs/planning/
├── 01-PRD.md                          # Product Requirements Document
├── 02-user-stories.md                 # Historias de Usuario Detalladas  
├── 03-technical-use-cases.md          # Casos de Uso Técnicos
├── 04-technical-architecture.md       # Plan de Arquitectura Técnica
├── 05-testing-qa-plan.md             # Plan de Testing y QA
├── 06-implementation-plan.md          # Plan de Implementación Detallado
├── 07-risk-management.md             # Plan de Gestión de Riesgos
├── 08-executive-summary.md           # Resumen Ejecutivo
└── 09-implementation-workflow.md     # Esta guía
```

### 3. **Claude Code Workspace Setup**
```json
// .claude_code/project_context.json
{
  "project_name": "Diana Bot V2",
  "project_type": "telegram_bot_rewrite",
  "architecture": "event_driven_microservices",
  "primary_docs": [
    "docs/planning/01-PRD.md",
    "docs/planning/04-technical-architecture.md",
    "docs/planning/06-implementation-plan.md"
  ],
  "current_phase": "foundation_setup",
  "event_bus_first": true,
  "rewrite_from_scratch": true
}
```

---

## 🤖 **FASE 1: Estrategia de Agentes (Día 1-2)**

### **Agentes Especializados Recomendados**

#### 🏗️ **@architecture-lead**
```
ROLE: Senior Software Architect
SPECIALIZATION: Event-driven microservices, Clean Architecture
RESPONSIBILITIES:
- Implementar Event Bus core desde cero
- Definir interfaces y contratos
- Establecer architectural patterns
- Review architectural decisions

CONTEXT TO PROVIDE:
- docs/planning/04-technical-architecture.md
- Focus en Event Bus como backbone
- Clean Architecture principles
- Python 3.11+ con aiogram 3.x
```

#### 🎲 **@gamification-specialist**  
```
ROLE: Gamification Systems Developer
SPECIALIZATION: Points, achievements, leaderboards
RESPONSIBILITIES:
- Implementar GamificationService desde cero
- Event-driven gamification logic
- Anti-abuse mechanisms
- Achievement system

CONTEXT TO PROVIDE:
- docs/planning/02-user-stories.md (US-005 a US-008)
- docs/planning/03-technical-use-cases.md (UC-004 a UC-006)
- Event Bus interfaces del architecture-lead
```

#### 📚 **@narrative-architect**
```
ROLE: Interactive Narrative Systems Developer  
SPECIALIZATION: Branching narratives, character systems
RESPONSIBILITIES:
- Implementar NarrativeService desde cero
- Story progression engine
- Character relationship system
- Decision consequence tracking

CONTEXT TO PROVIDE:
- docs/planning/02-user-stories.md (US-009 a US-012)  
- docs/planning/03-technical-use-cases.md (UC-007 a UC-008)
- Event Bus interfaces del architecture-lead
```

#### 🤖 **@telegram-integration-expert**
```
ROLE: Telegram Bot Integration Specialist
SPECIALIZATION: aiogram 3.x, Telegram APIs
RESPONSIBILITIES:
- TelegramAdapter desde cero
- Handlers y keyboards
- Middleware y filters
- Dynamic UI generation

CONTEXT TO PROVIDE:
- docs/planning/04-technical-architecture.md (Presentation Layer)
- Event Bus interfaces del architecture-lead  
- UI/UX requirements del PRD
```

#### 🧠 **@ai-personalization-engineer**
```
ROLE: AI/ML Engineer
SPECIALIZATION: Personalization, mood detection
RESPONSIBILITIES:
- Diana Master System (rescatar lógica conceptual)
- Adaptive Context Engine
- Mood detection algorithms
- Personalization engine

CONTEXT TO PROVIDE:
- docs/planning/01-PRD.md (Diana Master System section)
- docs/planning/04-technical-architecture.md (AI components)
- Event Bus interfaces del architecture-lead
```

---

## 📝 **FASE 2: Templates de Comunicación con Agentes**

### **Template 1: Inicialización de Agente**

```markdown
# DIANA BOT V2 - AGENT BRIEFING

## 🎯 PROJECT CONTEXT
- **Proyecto**: Diana Bot V2 - Complete rewrite from scratch
- **Tu Rol**: [ROLE_ESPECÍFICO]
- **Fase Actual**: Foundation Setup (Week 1-2)
- **Arquitectura**: Event-driven microservices with Event Bus backbone

## 📚 REQUIRED READING
1. **PRD**: docs/planning/01-PRD.md
2. **Technical Architecture**: docs/planning/04-technical-architecture.md  
3. **Your User Stories**: docs/planning/02-user-stories.md [SECCIÓN_ESPECÍFICA]
4. **Your Use Cases**: docs/planning/03-technical-use-cases.md [CASOS_ESPECÍFICOS]

## 🎯 YOUR IMMEDIATE MISSION
[MISIÓN_ESPECÍFICA_DEL_AGENTE]

## ⚠️ CRITICAL CONSTRAINTS
- ✅ **Event Bus First**: ALL services depend on Event Bus
- ✅ **Rewrite from Scratch**: Don't reference existing code
- ✅ **Python 3.11+**: Modern Python features
- ✅ **Clean Architecture**: Strict separation of concerns
- ✅ **Test-Driven**: 90%+ coverage target

## 🔄 DEPENDENCIES  
- **Depends On**: [DEPENDENCIES]
- **Blocks**: [WHAT_THIS_BLOCKS]
- **Integration Points**: Event Bus + [OTHER_SERVICES]

## 📋 DELIVERABLES
[DELIVERABLES_ESPECÍFICOS]

## 🤝 COLLABORATION
- **Report Progress**: Daily updates on implementation
- **Ask Questions**: Clarify requirements immediately  
- **Share Interfaces**: Coordinate with other agents
- **Code Review**: All code reviewed before integration

Ready to start? Confirm understanding of your mission.
```

### **Template 2: Task Assignment**

```markdown
# TASK: [TASK_NAME] - Sprint [X], Week [Y]

## 🎯 OBJECTIVE
[CLEAR_OBJECTIVE]

## 📋 ACCEPTANCE CRITERIA
- [ ] Criterion 1 with specific metric
- [ ] Criterion 2 with specific metric  
- [ ] Criterion 3 with specific metric
- [ ] Tests written and passing (>90% coverage)
- [ ] Documentation updated
- [ ] Event Bus integration working

## 📐 TECHNICAL REQUIREMENTS
- **Language**: Python 3.11+
- **Framework**: [SPECIFIC_FRAMEWORK]
- **Event Integration**: Must publish/subscribe to specific events
- **Performance**: [SPECIFIC_PERFORMANCE_TARGETS]
- **Security**: [SPECIFIC_SECURITY_REQUIREMENTS]

## 🔗 INTERFACES TO IMPLEMENT
```python
# Expected interfaces (provide actual interfaces)
class IYourService(ABC):
    @abstractmethod
    async def method_name(self, param: Type) -> ReturnType:
        pass
```

## 📊 SUCCESS METRICS
- [ ] All acceptance criteria met
- [ ] Tests passing with >90% coverage
- [ ] Performance benchmarks met
- [ ] Integration tests with Event Bus passing
- [ ] Code review approved

## 📅 TIMELINE
- **Start**: [DATE]
- **Daily Check-ins**: [TIME]  
- **Completion Target**: [DATE]
- **Integration Deadline**: [DATE]

## 🚨 BLOCKERS & DEPENDENCIES
- **Blocked By**: [DEPENDENCIES]
- **Blocks**: [WHAT_THIS_BLOCKS]
- **Critical Path**: [YES/NO]

## 🆘 ESCALATION
If stuck >2 hours, escalate immediately to project lead.
```

---

## 🔄 **FASE 3: Flujo de Trabajo Recomendado**

### **Week 1: Event Bus Foundation**

#### **Día 1: Architecture Lead**
```bash
# Task: Implementar Event Bus Core
claude-code --agent architecture-lead --task "event-bus-foundation"

# Prompt específico:
"""
TASK: Implement Diana Event Bus Foundation

CONTEXT: You are the architecture lead for Diana Bot V2 complete rewrite.

MISSION: Implement the core Event Bus system that will be the backbone
of ALL other services. This must be implemented FIRST before any other service.

REQUIREMENTS:
1. Event Bus core with pub/sub pattern
2. Redis integration for distributed events  
3. Event serialization/deserialization
4. Type-safe event definitions
5. Subscription management
6. Error handling and retry logic

DELIVERABLES:
- src/core/event_bus.py
- src/core/events.py  
- src/core/interfaces.py
- tests/unit/core/test_event_bus.py
- Documentation in docs/architecture/event-bus.md

Start with the IEvent interface and IEventBus interface, then implement
concrete EventBus class with Redis backend.
"""
```

#### **Día 2-3: Service Interfaces**
```bash
# Task: Definir interfaces de todos los services
claude-code --agent architecture-lead --task "service-interfaces"

# Una vez que Event Bus esté listo, definir:
# - IGamificationService
# - INarrativeService  
# - IUserService
# - IAdminService
# - IDianaMasterService
```

### **Week 2: Core Services Foundation**

#### **Día 1-2: Gamification Service**
```bash
claude-code --agent gamification-specialist --task "gamification-foundation"

# Prompt específico:
"""
TASK: Implement GamificationService from scratch

CONTEXT: Event Bus is ready. Implement GamificationService that is
100% event-driven.

MISSION: Implement points system, achievements, and leaderboards.

DEPENDENCIES:
- Event Bus (completed)
- IGamificationService interface (completed)

INTEGRATION:
- Subscribe to: UserActionEvent, StoryCompletionEvent
- Publish: PointsAwardedEvent, AchievementUnlockedEvent

Use the User Stories US-005 to US-008 as your guide.
"""
```

#### **Día 3-4: User Service**  
```bash
claude-code --agent user-management-specialist --task "user-service-foundation"
```

#### **Día 5: Service Integration**
```bash
claude-code --agent architecture-lead --task "services-integration"
```

### **Week 3+: Advanced Services**

Continuar con Narrative, Admin, Diana Master System siguiendo el mismo patrón.

---

## 📂 **FASE 4: Organización de Archivos para Claude Code**

### **Estructura Recomendada**
```
diana-bot-v2-new/
├── .claude_code/
│   ├── project_context.json          # Contexto general del proyecto
│   ├── current_sprint.json           # Sprint actual y objetivos
│   ├── agent_assignments.json        # Asignaciones por agente
│   └── integration_points.json       # Puntos de integración críticos
├── docs/
│   ├── planning/                      # TODA la planeación estratégica
│   │   ├── 01-PRD.md
│   │   ├── 02-user-stories.md
│   │   ├── 03-technical-use-cases.md
│   │   ├── 04-technical-architecture.md
│   │   ├── 05-testing-qa-plan.md
│   │   ├── 06-implementation-plan.md
│   │   ├──
│   │   └── 08-executive-summary.md
│   ├── architecture/                  # Docs técnicos en evolución
│   │   ├── event-bus.md
│   │   ├── service-interfaces.md
│   │   └── integration-patterns.md
│   └── api/                          # API documentation generada
├── src/
│   ├── core/                         # Event Bus + interfaces
│   ├── modules/                      # Business logic services
│   ├── infrastructure/               # External integrations
│   └── bot/                          # Telegram presentation layer
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

### **Context Files para Claude Code**

#### **.claude_code/project_context.json**
```json
{
  "project": {
    "name": "Diana Bot V2",
    "phase": "foundation_development",
    "week": 1,
    "sprint": 1,
    "architecture": "event_driven_microservices",
    "rewrite_from_scratch": true
  },
  "key_principles": [
    "Event Bus backbone for ALL communication",
    "Clean Architecture with strict layer separation",
    "Test-driven development (>90% coverage)",
    "Python 3.11+ with modern features",
    "Rewrite completely - no legacy code reuse"
  ],
  "priority_documents": [
    "docs/planning/04-technical-architecture.md",
    "docs/planning/06-implementation-plan.md",
    "docs/planning/02-user-stories.md"
  ],
  "current_focus": "Event Bus foundation implementation",
  "critical_success_factors": [
    "Event Bus working before any service implementation",
    "All services 100% event-driven from day 1",
    "Strict interface contracts between components"
  ]
}
```

#### **.claude_code/current_sprint.json**
```json
{
  "sprint": {
    "number": 1,
    "theme": "Event Bus Foundation & Core Architecture",
    "start_date": "2025-08-11",
    "end_date": "2025-08-25",
    "story_points": 40
  },
  "active_stories": [
    {
      "id": "ARCH-001",
      "title": "Implement Event Bus Core",
      "assignee": "architecture-lead",
      "status": "in_progress",
      "story_points": 8
    },
    {
      "id": "ARCH-002",
      "title": "Define Service Interfaces",
      "assignee": "architecture-lead",
      "status": "pending",
      "story_points": 5
    }
  ],
  "dependencies": {
    "ARCH-001": [],
    "ARCH-002": ["ARCH-001"]
  }
}
```

---

## 🎯 **FASE 5: Comandos Prácticos para Empezar HOY**

### **Comando 1: Setup Inicial**
```bash
# Crear estructura y documentación
mkdir diana-bot-v2-new && cd diana-bot-v2-new

# Copiar TODA la planeación a docs/planning/
# (Los 8 documentos que creé)

# Setup git
git init
echo "# Diana Bot V2 - Complete Rewrite" > README.md
```

### **Comando 2: Primer Agent - Event Bus**
```bash
claude-code --project diana-bot-v2-new --agent architecture-lead

# En Claude Code, usar este prompt:
"""
DIANA BOT V2 - EVENT BUS FOUNDATION

I need you to implement the Event Bus foundation for Diana Bot V2 complete rewrite.

CONTEXT:
- Complete rewrite from scratch (don't reference existing code)
- Event-driven microservices architecture  
- Event Bus must be implemented FIRST before any other service
- Python 3.11+ with modern async patterns

MISSION:
Implement the core Event Bus system following these specifications:

1. **IEvent Interface**: Base for all events with timestamp, event_id
2. **IEventBus Interface**: Pub/sub contract  
3. **EventBus Implementation**: Concrete implementation with Redis
4. **Event Types**: Base event classes for different domains
5. **Error Handling**: Robust error handling and retries
6. **Testing**: Unit tests with >90% coverage

TECHNICAL REQUIREMENTS:
- Redis pub/sub for distributed events
- Type hints throughout
- Async/await patterns
- Serialization support (JSON)
- Performance optimized for high throughput

DELIVERABLES:
- src/core/event_bus.py
- src/core/events.py
- src/core/interfaces.py  
- tests/unit/core/test_event_bus.py

Start with the interface definitions and work towards concrete implementation.
Are you ready to begin?
"""
```

### **Comando 3: Validación y Testing**
```bash
# Una vez que architecture-lead complete Event Bus
python -m pytest tests/unit/core/test_event_bus.py -v
python -m pytest --cov=src.core --cov-report=html

# Validar que Event Bus funciona antes de continuar
```

### **Comando 4: Siguiente Agent - Gamification**
```bash
claude-code --agent gamification-specialist

# Prompt para gamification specialist:
"""
DIANA BOT V2 - GAMIFICATION SERVICE

The Event Bus foundation is complete. Now implement GamificationService.

CONTEXT:
- Event Bus is working and tested
- Implement GamificationService from scratch  
- 100% event-driven architecture
- Reference User Stories US-005 to US-008

MISSION:
Implement complete gamification system:
1. Points system (Besitos)
2. Achievement system  
3. Leaderboards
4. Streak system

EVENT INTEGRATION:
- Subscribe to: UserActionEvent, StoryCompletionEvent
- Publish to: PointsAwardedEvent, AchievementUnlockedEvent

Use the Event Bus interfaces from architecture-lead.
Ready to implement?
"""
```

---

## 📊 **FASE 6: Métricas de Progreso**

### **Daily Standups con Agentes**
```bash
# Daily check con cada agente activo
claude-code --agent architecture-lead --task "daily-standup"

# Template de standup:
"""
DAILY STANDUP - [DATE]

YESTERDAY: What did you complete?
TODAY: What are you working on?  
BLOCKERS: Any impediments?
INTEGRATION: Any interfaces ready for other agents?
RISKS: Any concerns or risks identified?
"""
```

### **Integration Checkpoints**
```bash
# Weekly integration validation
python scripts/validate_integration.py

# Check:
# - All interfaces implemented correctly
# - Event Bus integration working
# - Tests passing  
# - Performance benchmarks met
```

### **Quality Gates**
```bash
# Before any merge to main
python -m pytest --cov=src --cov-report=html --cov-fail-under=90
python -m pylint src/
python -m mypy src/
python -m black src/ --check
```

---

## 🚀 **RESUMEN: Cómo Empezar MAÑANA**

### **Día 1 (Mañana):**
1. ✅ **Setup workspace** con la estructura recomendada
2. ✅ **Copiar documentación** a docs/planning/
3. ✅ **Configurar Claude Code** con project context
4. ✅ **Iniciar @architecture-lead** con Event Bus task

### **Día 2-3:**
1. ✅ **Completar Event Bus** y validar con tests
2. ✅ **Definir service interfaces** con @architecture-lead  
3. ✅ **Preparar** para @gamification-specialist

### **Día 4-5:**
1. ✅ **Iniciar @gamification-specialist** con Event Bus listo
2. ✅ **Implementar** GamificationService event-driven
3. ✅ **Validar integración** Event Bus + Gamification

### **Week 2:**
1. ✅ **Escalar** a más agentes (narrative, telegram, admin)
2. ✅ **Integration testing** entre services
3. ✅ **Foundation complete** para advanced features

---

## 💡 **Tips de Productividad con Claude Code**

### **1. Context Management**
- Mantén **project_context.json** actualizado
- **Documenta decisiones** arquitectónicas inmediatamente
- **Share interfaces** entre agentes ASAP

### **2. Agent Coordination**
- **Daily standups** con cada agente activo
- **Clear dependencies** - nunca duplicar trabajo
- **Integration points** coordinados explícitamente

### **3. Quality Maintenance**
- **Tests first** - implementar interfaces, luego tests, luego lógica
- **Performance budget** - benchmarks desde día 1
- **Code review** - todos los PRs revisados

### **4. Risk Mitigation**
- **Weekly integration** - nunca >1 semana sin integrar
- **Fallback plans** - si agente se atora, backup ready
- **Documentation** - toda decisión documentada

¿Listo para empezar? ¡El Event Bus te está esperando! 🚀
