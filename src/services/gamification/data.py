from .models import Achievement
from .interfaces import AchievementCategory

DEFAULT_ACHIEVEMENTS = [
    Achievement(
        id="first_steps",
        name="Primeros Pasos",
        description="Realiza tu primera interacción con Diana",
        category=AchievementCategory.PROGRESS.value,
        conditions={"total_interactions": 1},
        rewards={"base": {"points": 100, "title": "Recién Llegado"}},
        max_level=3,
    ),
    Achievement(
        id="faithful_visitor",
        name="Visitante Fiel",
        description="Mantén una racha de días consecutivos",
        category=AchievementCategory.ENGAGEMENT.value,
        conditions={
            "level_1": {"current_streak": 7},
            "level_2": {"current_streak": 30},
            "level_3": {"current_streak": 100},
        },
        rewards={
            "level_1": {"points": 500, "title": "Fiel"},
            "level_2": {"points": 2000, "title": "Muy Fiel"},
            "level_3": {"points": 10000, "title": "Ultra Fiel"},
        },
        max_level=3,
    ),
    Achievement(
        id="point_collector",
        name="Coleccionista de Besitos",
        description="Acumula una gran cantidad de Besitos",
        category=AchievementCategory.PROGRESS.value,
        conditions={
            "level_1": {"total_points": 1000},
            "level_2": {"total_points": 10000},
            "level_3": {"total_points": 100000},
        },
        rewards={
            "level_1": {"points": 200, "title": "Ahorrador"},
            "level_2": {"points": 1000, "title": "Rico"},
            "level_3": {"points": 5000, "title": "Millonario del Corazón"},
        },
        max_level=3,
    ),
    Achievement(
        id="story_reader",
        name="Lector Ávido",
        description="Completa capítulos de la historia principal",
        category=AchievementCategory.NARRATIVE.value,
        conditions={
            "level_1": {"chapters_completed": 5},
            "level_2": {"chapters_completed": 15},
            "level_3": {"chapters_completed": 30},
        },
        rewards={
            "level_1": {"points": 300, "title": "Lector"},
            "level_2": {"points": 1500, "title": "Bookworm"},
            "level_3": {"points": 5000, "title": "Maestro Narrador"},
        },
        max_level=3,
    ),
    Achievement(
        id="social_butterfly",
        name="Mariposa Social",
        description="Interactúa activamente con la comunidad",
        category=AchievementCategory.SOCIAL.value,
        conditions={
            "level_1": {"community_interactions": 10},
            "level_2": {"community_interactions": 50},
            "level_3": {"community_interactions": 200},
        },
        rewards={
            "level_1": {"points": 250, "title": "Sociable"},
            "level_2": {"points": 1200, "title": "Popular"},
            "level_3": {"points": 4000, "title": "Influencer"},
        },
        max_level=3,
    ),
]
