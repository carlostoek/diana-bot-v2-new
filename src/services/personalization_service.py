from src.domain.models import UserProfile


class PersonalizationService:
    """
    Service for content personalization (AI-002).
    This is a mock implementation to satisfy the initial DoD.
    """

    async def get_content_recommendations(self, profile: UserProfile) -> list[str]:
        """
        Mock implementation for getting content recommendations.
        In a real implementation, this would use the user's archetype, mood, etc.
        """
        if profile.archetype.value == "explorer":
            return [
                "Recomendación: Explora el jardín secreto.",
                "Recomendación: Busca el mapa estelar.",
            ]
        elif profile.archetype.value == "achiever":
            return [
                "Recomendación: Completa el desafío del guardián.",
                "Recomendación: Consigue la medalla de valor.",
            ]
        else:
            return [
                "Recomendación: Habla con el mercader de sueños.",
                "Recomendación: Visita la biblioteca de los susurros.",
            ]

    async def generate_adaptive_message(self, profile: UserProfile) -> str:
        """
        Generates a personalized greeting based on the user's mood and archetype.
        """
        mood_greeting = {
            "neutral": "Hola.",
            "happy": "¡Qué bueno verte tan alegre!",
            "sad": "Espero que te animes pronto. A veces, un pequeño paso es un gran comienzo.",
            "angry": "Respira hondo. La calma es una aliada poderosa.",
            "curious": "Veo que la curiosidad te guía hoy...",
            "reflective": "Un momento de calma para pensar es un tesoro.",
        }.get(profile.mood.value, "Hola.")

        archetype_greeting = {
            "explorer": "El mundo tiene nuevos caminos para que los descubras.",
            "achiever": "Un nuevo reto te espera para que demuestres tu valía.",
            "socializer": "¿Listo para conectar con otros y compartir historias?",
            "philosopher": "Una pregunta interesante flota en el aire, ¿la atrapas?",
            "creator": "La inspiración te rodea, solo tienes que darle forma.",
        }.get(profile.archetype.value, "")

        return f"{mood_greeting} {archetype_greeting}".strip()
