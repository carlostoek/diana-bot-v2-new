# Diana Bot V2 - Casos de Uso Técnicos Detallados

## 📋 Información del Documento

- **Producto**: Diana Bot V2
- **Versión**: 1.0
- **Fecha**: Agosto 2025
- **Basado en**: User Stories v1.0, PRD v1.0
- **Audiencia**: Development Team, QA Team, Technical Architects

---

## 🎯 Metodología de Casos de Uso

### Formato Estándar de Caso de Uso
```
UC-[ID]: [Nombre del Caso de Uso]

Actores: [Primario], [Secundarios]
Precondiciones: [Estados del sistema requeridos]
Trigger: [Evento que inicia el caso de uso]

Flujo Principal:
1. [Paso 1]
2. [Paso 2]
3. [Paso N]

Flujos Alternativos:
A1. [Condición alternativa]
E1. [Manejo de errores]

Postcondiciones: [Estado resultante del sistema]
Criterios Técnicos: [Requirements técnicos específicos]
```

---

## 🚀 MÓDULO: Sistema de Onboarding

### UC-001: Primer Contacto con Usuario Nuevo

**Actores**: Usuario Nuevo, Diana Master System, Database Service  
**Precondiciones**: Usuario nunca ha interactuado con el bot  
**Trigger**: Usuario envía comando `/start`

**Flujo Principal**:
1. TelegramAdapter recibe mensaje `/start` de usuario desconocido
2. Sistema verifica que user_id no existe en database
3. Diana Master System genera contexto inicial para nuevo usuario
4. UserService crea registro básico con timestamp y metadata inicial
5. AdaptiveContextEngine inicializa perfil con estado "newcomer"
6. DianaMasterInterface genera saludo personalizado basado en hora del día
7. Sistema presenta mensaje de bienvenida con 3 opciones iniciales:
   - "✨ Empezar aventura" → UC-002
   - "🎮 Ver qué puedo hacer" → UC-003  
   - "⚙️ Configurar preferencias" → UC-004
8. EventBus publica evento "user_first_contact" para analytics

**Flujos Alternativos**:
A1. Usuario ya existe pero no ha completado onboarding:
   - 4a. Recuperar estado parcial de onboarding
   - 4b. Continuar desde último step completado

A2. Sistema de personalización no disponible:
   - 6a. Usar mensaje de fallback predefinido
   - 6b. Log warning para monitoreo

**Flujos de Error**:
E1. Database no disponible:
   - 4a. Usar storage temporal en memoria
   - 4b. Intentar persist datos cuando DB esté disponible
   - 4c. Notificar a usuario que experiencia puede ser limitada

E2. Timeout en generación de saludo:
   - 6a. Usar template de saludo básico después de 3 segundos
   - 6b. Log error para debugging

**Postcondiciones**:
- Usuario registrado en sistema con estado "onboarding_started"
- Perfil inicial creado con arquetipo "newcomer"
- Analytics event logged para tracking de acquisition
- Sistema preparado para siguiente step del onboarding

**Criterios Técnicos**:
- Response time: <2 segundos desde `/start` hasta primer mensaje
- Fallback graceful si servicios no están disponibles
- All user data persisted para recovery posterior
- Analytics tracking para funnel optimization

---

### UC-002: Detección de Personalidad de Usuario

**Actores**: Usuario, Diana Master System, Personality Detection Engine  
**Precondiciones**: Usuario completó UC-001, estado = "onboarding_started"  
**Trigger**: Usuario selecciona "✨ Empezar aventura"

**Flujo Principal**:
1. Sistema inicializa PersonalityDetectionEngine para el usuario
2. PersonalityEngine selecciona primera pregunta basada en random seed
3. Sistema presenta pregunta con 3-4 opciones como InlineKeyboard
4. Usuario selecciona opción → callback_data contiene "personality:[question_id]:[option_id]"
5. PersonalityEngine procesa respuesta y actualiza scoring interno:
   - Dimensión Exploración: +/- puntos
   - Dimensión Competitividad: +/- puntos  
   - Dimensión Narrativa: +/- puntos
   - Dimensión Social: +/- puntos
6. Sistema determina si necesita más preguntas (mínimo 3, máximo 5)
7. Si faltan preguntas: repetir pasos 2-6 con siguiente pregunta
8. Si completo: PersonalityEngine calcula arquetipo final
9. Sistema almacena arquetipo en UserProfile
10. AdaptiveContextEngine actualiza contexto con nuevo arquetipo
11. Sistema presenta resultado personalizado: "Eres un [ARQUETIPO]! Esto significa..."
12. EventBus publica "personality_detected" con arquetipo y confidence score

**Flujos Alternativos**:
A1. Usuario responde muy rápido (<5 segundos) 3+ veces consecutivas:
   - 5a. Añadir pregunta extra para validar engagement
   - 5b. Reducir confidence score del resultado

A2. Usuario abandona en medio del proceso:
   - Sistema guarda progreso parcial
   - Al regresar, ofrecer continuar o restart

A3. Empate en scoring de arquetipos:
   - 8a. Seleccionar arquetipo con mayor engagement histórico
   - 8b. Marcar perfil como "hybrid" para future refinement

**Flujos de Error**:
E1. PersonalityEngine falla:
   - 8a. Asignar arquetipo "balanced" como fallback
   - 8b. Schedule re-detection para más tarde

E2. Usuario selecciona opción inválida:
   - 4a. Ignorar input y presentar pregunta nuevamente
   - 4b. Log anomaly para debugging

**Postcondiciones**:
- Usuario tiene arquetipo asignado con confidence score
- Perfil actualizado con personality dimensions
- Estado cambiado a "personality_detected"
- Sistema preparado para personalizar resto de onboarding

**Criterios Técnicos**:
- Personality detection completo en <3 minutos
- Minimum 3 preguntas para statistical validity
- Confidence score >70% para considerar detection successful
- All responses logged para machine learning improvements

---

### UC-003: Tutorial Interactivo Gamificado

**Actores**: Usuario, Tutorial Engine, Gamification Service, Narrative Service  
**Precondiciones**: Usuario completó UC-002 o seleccionó "🎮 Ver qué puedo hacer"  
**Trigger**: Usuario inicia tutorial

**Flujo Principal**:
1. TutorialEngine determina path óptimo basado en arquetipo de usuario
2. Sistema inicializa tutorial state machine con 4 módulos:
   - Gamificación Demo (90s)
   - Narrativa Teaser (120s)  
   - Tienda Preview (90s)
   - Comunidad Intro (60s)
3. **Módulo Gamificación**:
   - 3a. Presenta acción simple: "Dale 'me gusta' a este mensaje"
   - 3b. Usuario hace clic → GamificationService.award_points(user_id, 50, "tutorial_first_action")
   - 3c. Muestra animación de +50 Besitos con counter actualizado
   - 3d. Achievement unlocked: "Primer Paso" (+100 bonus)
   - 3e. Explica brevemente sistema de puntos
4. **Módulo Narrativa**:
   - 4a. NarrativeService presenta excerpt de historia principal
   - 4b. Usuario toma decisión simple entre 2 opciones
   - 4c. Sistema muestra cómo la decisión afecta próximo diálogo
   - 4d. Explica que sus decisiones importan en la historia completa
5. **Módulo Tienda**:
   - 5a. Muestra 3 objetos atractivos con precios
   - 5b. Usuario recibe objeto gratuito: "Lámpara del Genio de Bienvenida"
   - 5c. Explica cómo ganar más Besitos para comprar más objetos
6. **Módulo Comunidad**:
   - 6a. Muestra leaderboard actual (top 5 + posición del usuario)
   - 6b. Explica eventos comunitarios y competencias
   - 6c. Invita a unirse al canal comunitario (opcional)
7. Tutorial completo → GamificationService.award_points(user_id, 200, "tutorial_completed")
8. Sistema actualiza estado a "tutorial_completed"
9. EventBus publica "tutorial_completed" con completion_time y modules_completed

**Flujos Alternativos**:
A1. Usuario quiere skip tutorial:
   - 2a. Confirmar con "¿Estás seguro? Te perderás recompensas"
   - 2b. Si confirma: dar recompensas mínimas y marcar como "tutorial_skipped"

A2. Usuario abandona tutorial en módulo específico:
   - Sistema guarda progreso
   - Al regresar, ofrecer continuar desde donde se quedó

A3. Servicio específico no disponible:
   - Skip módulo afectado con mensaje explicativo
   - Continuar con módulos restantes

**Flujos de Error**:
E1. Gamification Service falla durante award_points:
   - 3b. Mostrar UI como si puntos fueran otorgados
   - Queue award para retry cuando servicio esté disponible

E2. Narrative Service no puede cargar contenido:
   - 4a. Usar contenido estático de fallback
   - Log error para investigation

**Postcondiciones**:
- Usuario completó tutorial con recompensas otorgadas
- Estado actualizado a "tutorial_completed"
- Usuario familiar con 4 funcionalidades core
- Analytics data captured para tutorial optimization

**Criterios Técnicos**:
- Cada módulo debe completarse en tiempo target (±30 segundos)
- Tutorial debe ser pausable y resumible
- Todos los servicios deben tener fallbacks graceful
- Progress tracking debe ser persistent across sessions

---

## 🎲 MÓDULO: Gamificación Core

### UC-004: Otorgamiento de Puntos "Besitos"

**Actores**: Usuario, Gamification Service, Event Bus, Anti-Abuse System  
**Precondiciones**: Usuario registrado, GamificationService disponible  
**Trigger**: Usuario realiza acción que otorga puntos

**Flujo Principal**:
1. Evento trigger detectado (ej: "user_completed_trivia", "user_daily_login")
2. Event Bus route evento a GamificationService
3. GamificationService.process_point_award(user_id, action_type, context)
4. Anti-Abuse System valida legitimidad de la acción:
   - Chequea rate limits para el tipo de acción
   - Verifica que user no ha hecho gaming del sistema
   - Valida que context data es consistente
5. Si válido: PointsEngine calcula cantidad de puntos:
   - Base points para la acción
   - Multipliers activos (VIP bonus, streak bonus, event bonus)
   - User-specific modifiers (nivel, logros especiales)
6. Database transaction inicia:
   - Update user_balance con nueva cantidad
   - Insert transaction_log entry
   - Update user_statistics
7. Sistema chequea si balance update triggers achievements:
   - "Primer Millar": 1,000 Besitos totales
   - "Rico en Amor": 10,000 Besitos totales
   - "Millonario del Corazón": 100,000 Besitos totales
8. Si achievement unlocked: trigger UC-007 (Achievement Unlock)
9. Sistema envía notification al usuario:
   - "¡+[cantidad] Besitos! [motivo]"
   - Muestra balance actualizado
   - Incluye achievement notification si aplicable
10. EventBus publica "points_awarded" para analytics

**Flujos Alternativos**:
A1. Usuario tiene VIP subscription activa:
   - 5a. Aplicar 50% bonus a todos los puntos base
   - 5b. Add special VIP visual indicator en notification

A2. Usuario tiene streak activa:
   - 5a. Aplicar bonus basado en streak length
   - 5b. Mencionar streak en notification

A3. Evento especial activo:
   - 5a. Aplicar event multiplier (ej: "Semana del Amor" = 2x points)
   - 5b. Incluir themed visual elements en notification

**Flujos de Error**:
E1. Anti-Abuse System detecta comportamiento sospechoso:
   - 4a. Log incident para review
   - 4b. Aplicar penalty temporal (reduced points rate)
   - 4c. Notificar a admin system para manual review

E2. Database transaction falla:
   - 6a. Queue transaction para retry
   - 6b. Mostrar mensaje de "procesando..." al usuario
   - 6c. Auto-retry hasta 3 veces con exponential backoff

E3. Achievement system no disponible:
   - 7a. Skip achievement checks
   - 7b. Queue achievement evaluation para más tarde

**Postcondiciones**:
- Balance de usuario actualizado correctamente
- Transaction logged para audit trail
- Achievements evaluados y unlocked si aplicable
- Analytics event generado para business intelligence

**Criterios Técnicos**:
- Toda award transaction debe ser atómica
- Anti-abuse checks deben completarse en <500ms
- Rate limiting debe prevenir gaming sin impactar uso legítimo
- System debe handle 1000+ concurrent point awards

---

### UC-005: Sistema de Logros Multinivel

**Actores**: Usuario, Achievement Engine, Gamification Service, Notification Service  
**Precondiciones**: Usuario activo, Achievement system inicializado  
**Trigger**: Usuario realiza acción que puede unlock achievement

**Flujo Principal**:
1. EventBus recibe evento de progreso del usuario (ej: "story_chapter_completed")
2. Achievement Engine procesa evento:
   - Identifica achievements relacionados con el evento
   - Calcula nuevo progress para cada achievement relevante
3. Para cada achievement, sistema evalúa conditions:
   - Chequea current progress vs requirements
   - Verifica prerequisitos (otros achievements, user level, etc.)
   - Confirma que achievement no está ya unlocked
4. Si achievement requirements met:
   - AchievementEngine.unlock_achievement(user_id, achievement_id)
   - Determina nivel del achievement (Bronze/Silver/Gold)
   - Calcula rewards asociadas (Besitos, objetos especiales, títulos)
5. Database transaction:
   - Update user_achievements table
   - Update user_balance con reward Besitos
   - Insert achievement_log entry
6. NotificationService genera celebración:
   - Visual: Achievement badge con animación
   - Text: "🏆 ¡Logro Desbloqueado! [Nombre] - [Descripción]"
   - Reward summary: "+[Besitos] +[Objeto] +[Título]"
7. Sistema actualiza achievement gallery del usuario
8. Si es achievement especial: trigger additional effects:
   - Social sharing option
   - Leaderboard highlight
   - Exclusive content unlock
9. EventBus publica "achievement_unlocked" para analytics

**Flujos Alternativos**:
A1. Achievement tiene múltiples niveles:
   - 4a. Unlock appropriate level (Bronze → Silver → Gold)
   - 4b. Show progress toward next level
   - 4c. Compound rewards para higher levels

A2. Achievement es secreto/hidden:
   - 7a. Reveal achievement en gallery solo después de unlock
   - 7b. Add mystery element en notification
   - 7c. Bonus discovery reward para secret achievements

A3. Achievement requires multiple conditions:
   - 3a. Evaluar todas las conditions simultáneamente
   - 3b. Show partial progress si algunas conditions met
   - 3c. Highlight next required action para user guidance

**Flujos de Error**:
E1. Achievement data corrupted o missing:
   - 3a. Log error y skip evaluation para ese achievement
   - 3b. Schedule data repair task
   - 3c. Notify admin system de data integrity issue

E2. Notification Service unavailable:
   - 6a. Store pending notification para delivery posterior
   - 6b. Achievement still unlocked, solo falta la celebración
   - 6c. Retry notification hasta 3 veces

E3. Concurrent unlock attempts para mismo achievement:
   - 4a. Use database locks para prevenir duplicate unlocks
   - 4b. Second attempt gracefully ignored
   - 4c. Log incident para monitoring

**Postcondiciones**:
- Achievement permanently unlocked para el usuario
- Rewards otorgadas y aplicadas al perfil
- Achievement visible en gallery
- Progress hacia related achievements actualizado

**Criterios Técnicos**:
- Achievement evaluation debe ser idempotent
- Complex achievements con múltiples conditions deben ser performant
- Achievement gallery debe load rápidamente even con 100+ achievements
- System debe handle achievement unlocks durante high traffic

---

### UC-006: Leaderboards Dinámicos

**Actores**: Usuario, Leaderboard Service, Cache System, Privacy Service  
**Precondiciones**: Usuario activo, datos suficientes para ranking  
**Trigger**: Usuario accede a leaderboards o data se actualiza

**Flujo Principal**:
1. Usuario selecciona "🏆 Leaderboards" desde menú principal
2. LeaderboardService.get_leaderboards(user_id, requested_timeframe)
3. Sistema determina qué leaderboards mostrar basado en user preferences
4. Cache System chequea si data está fresh (< 5 minutos):
   - Si cached: retrieve cached data
   - Si stale: trigger refresh process
5. LeaderboardEngine calcula rankings:
   - **Besitos Semanales**: TOP usuarios por puntos esta semana
   - **Racha Actual**: Usuarios con longest active streaks
   - **Narrativa Master**: Progress en historia principal
   - **Trivia Champion**: Respuestas correctas consecutivas
6. Para cada leaderboard:
   - Query relevant data con optimized queries
   - Apply privacy filters (usuarios que opted out)
   - Calculate rankings con tie-breaking rules
   - Identify user's position even si no está en TOP 10
7. Sistema genera UI response:
   - Top 10 para cada category con usernames y scores
   - User's rank y score claramente highlighted
   - Progress indicators y change desde última semana
8. Cache updated data para future requests
9. EventBus publica "leaderboard_viewed" para engagement analytics

**Flujos Alternativos**:
A1. Usuario está en TOP 10:
   - 7a. Highlight user's entry con color especial
   - 7b. Show celebration badge/icon
   - 7c. Offer social sharing option

A2. Usuario nunca ha participado en category:
   - 7a. Show encouraging message: "¡Participa para aparecer aquí!"
   - 7b. Provide direct action button para start participating

A3. Tie en scores:
   - 6a. Use secondary criteria (account age, total activity)
   - 6b. Show tied users con same rank
   - 6c. Next user gets next available rank number

**Flujos de Error**:
E1. Database query timeout:
   - 5a. Return cached data aunque sea stale
   - 5b. Show warning message about data freshness
   - 5c. Schedule background refresh

E2. User data inconsistent:
   - 6a. Exclude problematic entries from ranking
   - 6b. Log data issues para investigation
   - 6c. Show leaderboard con available clean data

E3. Cache system unavailable:
   - 4a. Skip caching layer
   - 4b. Generate rankings en real-time
   - 4c. Expect slower response time

**Postcondiciones**:
- Usuario ve current rankings para todas las categories
- User's position es accurate y clearly displayed
- Cache updated para improve future performance
- User engagement con competitive features tracked

**Criterios Técnicos**:
- Leaderboard queries deben execute en <3 segundos
- Cache invalidation debe be intelligent (no unnecessary rebuilds)
- Privacy settings deben be respected en todo momento
- System debe scale para rankings de 100K+ usuarios

---

## 📚 MÓDULO: Narrativa Interactiva

### UC-007: Progresión en Historia Principal

**Actores**: Usuario, Narrative Service, Decision Engine, Character System  
**Precondiciones**: Usuario unlocked narrativa, previous chapter completed  
**Trigger**: Usuario selecciona "📖 Continuar Historia"

**Flujo Principal**:
1. NarrativeService.get_user_story_state(user_id) retrieves:
   - Current chapter y scene
   - Previous decisions made
   - Character relationship states
   - Unlocked story branches
2. ContentEngine selecciona appropriate story content:
   - Base content para el capítulo
   - Personalized elements basado en decisions pasadas
   - Character dialogue adaptado a relationship levels
3. Sistema aplica narrative personalization:
   - Reference previous user choices en dialogue
   - Adjust character reactions basado en relationship history
   - Include easter eggs para observant users
4. Content delivery:
   - Present story text en installments (no wall of text)
   - Include atmospheric elements (emojis, spacing, timing)
   - Build tension con strategic pauses entre messages
5. Decision point reached:
   - Present 2-4 meaningful choices como inline buttons
   - Each option hints at potential consequences
   - Timer opcional para time-pressured decisions
6. Usuario selecciona option → callback contains "decision:[chapter]:[choice_id]"
7. DecisionEngine procesa choice:
   - Update narrative flags y variables
   - Calculate impact en character relationships
   - Determine immediate y future story consequences
8. Sistema provides immediate feedback:
   - Character reactions to the decision
   - Immediate consequences revealed
   - Hints about long-term implications
9. Progress tracking:
   - Update user's story progress
   - Unlock next chapter/scene
   - Check si new content branches available
10. Reward calculation:
    - Award Besitos for story progression
    - Check for narrative achievements
    - Update narrative statistics
11. EventBus publica "chapter_completed" con decision data

**Flujos Alternativos**:
A1. Usuario es VIP subscriber:
   - 2a. Include exclusive content segments
   - 2b. Offer additional decision branches
   - 2c. Early access to next chapter

A2. Decision has time limit:
   - 5a. Start countdown timer
   - 6a. Auto-select default option si timer expires
   - 7a. Note time pressure impact en decision consequences

A3. Chapter has multiple paths:
   - 2a. Determine which path based on previous choices
   - 9a. Unlock different next chapters based on current decision

**Flujos de Error**:
E1. Story content missing o corrupted:
   - 2a. Load backup/generic content
   - 2b. Log content issue para admin attention
   - 2c. Allow user to continue con minimal disruption

E2. Decision processing falla:
   - 7a. Record decision locally
   - 7b. Allow story to continue
   - 7c. Queue decision processing para retry

E3. Character relationship calculation error:
   - 7a. Use previous relationship values
   - 7b. Apply minimal safe updates
   - 7c. Schedule full relationship recalculation

**Postcondiciones**:
- User's story progress actualizado correctamente
- Decision recorded con all implications
- Character relationships updated
- Next content unlocked y available

**Criterios Técnicos**:
- Story content debe load en <2 segundos
- Decision consequences deben be internally consistent
- Character relationship calculations must be deterministic
- Progress debe be recoverable en case of interruption

---

### UC-008: Interacción con NPCs Memorables

**Actores**: Usuario, Character System, Relationship Engine, Dialogue Manager  
**Precondiciones**: Usuario has met character, character relationship initialized  
**Trigger**: Usuario inicia conversación con NPC específico

**Flujo Principal**:
1. Usuario selecciona character interaction (ej: "💬 Hablar con Diana")
2. CharacterSystem.load_character_state(user_id, character_id):
   - Relationship level y type (friend, rival, romantic interest)
   - Conversation history y important topics discussed
   - Character's current mood y state
   - Available conversation topics basado en story progress
3. RelationshipEngine evalúa context:
   - Recent story events que afectan relationship
   - User's past behavior hacia este character
   - Character's personality response patterns
4. DialogueManager genera conversation options:
   - Personalized greeting basado en relationship level
   - 3-4 conversation topics appropriate para current context
   - Options reflect history (ej: "Sobre lo que discutimos antes...")
5. Usuario selecciona conversation topic
6. Character responds basado en:
   - Their established personality traits
   - Current relationship state
   - Relevant story context y user's past choices
7. Conversation flow continues:
   - User has options para different response types
   - Character remembers user's communication style
   - Relationship meters pueden increase/decrease subtly
8. Conversation conclusion:
   - Character provides memorable closing line
   - Relationship changes saved
   - New conversation topics may unlock
9. Sistema updates character memory:
   - Topics discussed en esta session
   - User's general attitude during conversation
   - Important revelations o relationship developments
10. EventBus publica "character_interaction" para relationship analytics

**Flujos Alternativos**:
A1. High relationship level unlocks special content:
   - 4a. Include intimate/personal conversation options
   - 4b. Character shares secrets o special information
   - 4c. Unlock exclusive story branches

A2. Conflicted relationship (user hurt character before):
   - 4a. Character is initially cold o guarded
   - 6a. Responses are shorter, less warm
   - 7a. User must work to repair relationship

A3. Character has plot-relevant information:
   - 6a. Character drops hints about upcoming story events
   - 6b. Information unlocked based on trust level
   - 6c. Some info only revealed in specific emotional states

**Flujos de Error**:
E1. Character personality data corrupted:
   - 6a. Use default personality traits
   - 6b. Character acts slightly generic but consistent
   - 6c. Log issue para character data repair

E2. Relationship calculation error:
   - 8a. Preserve previous relationship state
   - 8b. Conversation proceeds normally
   - 8c. Schedule relationship data verification

E3. Dialogue content missing:
   - 4a. Generate conversation usando character's basic templates
   - 4b. Focus en relationship-building rather than plot
   - 4c. Log missing content para creation team

**Postcondiciones**:
- Character relationship updated basado en interaction
- Conversation history recorded para future reference
- Character's memory includes new information about user
- Potential new content unlocked based on relationship changes

**Criterios Técnicos**:
- Character responses must feel authentic y consistent
- Relationship changes should be gradual y believable
- Conversation history debe be searchable para debugging
- System debe handle hundreds of character interaction variables

---

## 👑 MÓDULO: Panel de Administración

### UC-009: Monitoreo de Métricas en Tiempo Real

**Actores**: Administrator, Analytics Service, Alert System, Dashboard Engine  
**Precondiciones**: Admin authenticated, analytics system running  
**Trigger**: Administrator accede al dashboard admin

**Flujo Principal**:
1. Admin envía comando `/admin` + provides authentication
2. AdminService.verify_permissions(user_id) confirms admin role
3. DashboardEngine.generate_realtime_metrics() compiles data:
   - Current active users (last 5 minutes)
   - Today's key performance indicators
   - Critical alerts y system health status
   - Revenue metrics (if configured)
4. Analytics Service provides data sources:
   - User engagement metrics from EventBus
   - System performance from monitoring services
   - Business metrics from GamificationService
   - Error rates from logging aggregation
5. Dashboard UI generation:
   - Key metrics displayed con visual indicators (🟢🟡🔴)
   - Trend arrows (↗️↘️→) para quick insight
   - Quick action buttons para common admin tasks
   - Drill-down options para detailed analysis
6. Real-time updates establecidas:
   - WebSocket o polling connection para live data
   - Auto-refresh every 30 seconds para critical metrics
   - Push notifications para urgent alerts
7. Alert evaluation:
   - Check current metrics contra defined thresholds
   - Generate alerts for anomalies
   - Show alert status en dashboard
8. Sistema provides navigation options:
   - Detailed reports button
   - User management interface
   - Content management tools
   - System configuration access

**Flujos Alternativos**:
A1. Critical alert active:
   - 3a. Highlight alert prominently en dashboard
   - 5a. Use urgent visual indicators
   - 7a. Provide immediate action options

A2. System performance degraded:
   - 4a. Show performance warning
   - 5a. Include system health details
   - 6a. Increase monitoring frequency

A3. Business metric threshold exceeded:
   - 7a. Show celebration indicator para positive thresholds
   - 7b. Highlight concern para negative thresholds
   - 8a. Provide recommendation actions

**Flujos de Error**:
E1. Analytics Service unavailable:
   - 3a. Show cached/stale data con timestamp
   - 3b. Display service unavailable warning
   - 4a. Use fallback data sources

E2. Authentication service failure:
   - 2a. Use backup authentication method
   - 2b. Require additional verification
   - 2c. Log security incident

E3. Dashboard generation timeout:
   - 5a. Show simplified dashboard con critical metrics only
   - 5b. Provide manual refresh option
   - 6a. Disable auto-refresh temporarily

**Postcondiciones**:
- Admin tiene comprehensive view del system status
- Real-time monitoring established para session duration
- Alerts evaluated y displayed appropriately
- Quick access to detailed admin functions available

**Criterios Técnicos**:
- Dashboard debe load en <5 segundos
- Real-time updates no deben impact system performance
- All sensitive data debe be properly secured
- Dashboard debe be responsive para mobile admin access

---

### UC-010: Gestión Avanzada de Usuarios

**Actores**: Administrator, User Management Service, Audit Logger, Communication Service  
**Precondiciones**: Admin authenticated, user management permissions  
**Trigger**: Admin selecciona "👥 Gestión de Usuarios"

**Flujo Principal**:
1. UserManagementService.load_user_interface() presenta:
   - Search bar para find specific users
   - Filter options (role, activity, subscription status)
   - Recent users list con key information
   - Bulk action tools
2. Admin searches/filters para encontrar target user(s)
3. UserManagementService.get_user_details(user_id) provides:
   - Complete user profile y statistics
   - Recent activity log y interaction patterns
   - Subscription history y payment information
   - Moderation history (warnings, restrictions, etc.)
4. Admin selecciona action to perform:
   - Modify user balance o rewards
   - Change subscription level o permissions
   - Apply moderation actions
   - Send direct communication
   - View detailed analytics
5. Sistema presents action-specific interface:
   - Form con relevant fields y options
   - Warnings para irreversible actions
   - Preview of action consequences
   - Confirmation requirements
6. Admin confirms action execution
7. UserManagementService.execute_action() performs:
   - Validation of admin permissions para specific action
   - Business logic validation (ej: balance changes)
   - Database updates con transaction safety
   - User notification si appropriate
8. AuditLogger records admin action:
   - Timestamp y admin ID
   - Action performed y target user
   - Before/after states
   - Reason/notes if provided
9. Sistema confirms successful action:
   - Show updated user information
   - Confirmation message con action summary
   - Option to perform additional actions
10. Communication Service notifies user si applicable:
    - Account changes notification
    - Moderation action explanation
    - Support contact information

**Flujos Alternativos**:
A1. Bulk action en multiple users:
   - 2a. Allow selection of multiple users via checkboxes
   - 5a. Show batch action confirmation con user count
   - 7a. Execute actions secuencialmente con progress indicator

A2. High-value user (VIP, high spender):
   - 3a. Display special indicators y warnings
   - 5a. Require additional confirmation para actions
   - 8a. Flag audit log entry como high-sensitivity

A3. User currently online:
   - 3a. Show real-time activity indicator
   - 7a. Consider immediate impact en user experience
   - 10a. Use in-app notification además de standard communication

**Flujos de Error**:
E1. User data inconsistency detected:
   - 3a. Display data integrity warning
   - 7a. Prevent actions hasta data validation
   - 8a. Log data issue para technical team

E2. Action validation fails:
   - 7a. Show specific error message
   - 7b. Suggest alternative actions
   - 8a. Log failed attempt para security monitoring

E3. Communication service failure:
   - 10a. Queue notification para retry
   - 10b. Log communication failure
   - 9a. Warn admin that user notification pending

**Postcondiciones**:
- User account updated según admin action
- All changes properly logged para audit trail
- User notified appropriately si required
- Admin interface ready para next action

**Criterios Técnicos**:
- All admin actions must be reversible when possible
- Audit trail debe be tamper-proof y comprehensive
- User data changes must be atomic y consistent
- Security logging debe capture all access attempts

---

## 📊 Métricas de Calidad para Casos de Uso

### Performance Requirements
- **Response Time**: 95% de UC deben completarse en <3 segundos
- **Throughput**: Sistema debe handle 100 concurrent UC executions
- **Availability**: 99.9% uptime durante business hours
- **Scalability**: UC deben scale linearly hasta 10x current load

### Error Handling Requirements
- **Graceful Degradation**: Todos los UC deben tener fallback behavior
- **Error Recovery**: Sistema debe auto-recover from transient failures
- **User Communication**: Clear error messages sin technical details
- **Monitoring**: All errors logged con sufficient detail para debugging

### Security Requirements
- **Authentication**: Admin UC require strong authentication
- **Authorization**: Role-based access strictly enforced
- **Audit Trail**: All sensitive actions logged immutably
- **Data Protection**: User data encrypted en transit y at rest

### Usability Requirements
- **Intuitive Flow**: UC steps deben be logical y easy to follow
- **Progress Indication**: Long-running UC show progress to users
- **Help/Documentation**: Context-sensitive help available
- **Accessibility**: UC deben work en mobile devices

---

## 🔄 Dependencias entre Casos de Uso

### Initialization Dependencies
```
UC-001 (Primer Contacto) → UC-002 (Detección Personalidad) → UC-003 (Tutorial)
UC-004 (Otorgamiento Puntos) ← Most other UC depend on this
UC-005 (Sistema Logros) depends on → UC-004
```

### Service Dependencies
```
Gamification UC → GamificationService, EventBus
Narrative UC → NarrativeService, CharacterSystem
Admin UC → AdminService, AnalyticsService, AuditLogger
```

### Data Dependencies
```
All UC require → Database connectivity
Real-time UC require → Cache system
Analytics UC require → Event streaming
```

---

**Documento Técnico Vivo**: Estos casos de uso serán refinados iterativamente durante development, basado en technical discoveries y performance optimization needs.

**Próxima Revisión**: Cada sprint completion o cuando architectural changes impacten UC flows
