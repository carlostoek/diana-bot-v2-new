from src.core.container import Container
from src.modules.user.handlers import user_registered_handler
from dependency_injector.wiring import inject, Provide
from src.modules.user.service import UserService

# This is a placeholder for where you might have your application logic,
# for example, your bot's command handlers or your web server endpoints.

@inject
def handle_new_user(user_service: UserService = Provide[Container.user_service]):
    """
    Example function that uses an injected service.
    """
    print("Handling new user... (example usage of injected service)")
    # In a real scenario, you would call the service's methods.
    # For example: user_service.find_or_create_user(...)
    pass

def main():
    """
    Main entry point for the application.
    Initializes the container and wires up dependencies.
    """
    # Initialize the dependency injection container
    container = Container()

    # Wire the container to the modules that need it.
    # This injects the container's providers into the functions/classes
    # that are decorated with @inject.
    # You would list all modules where you use @inject here.
    container.wire(modules=[__name__, "src.modules.user.handlers"])

    print("Application container initialized and wired.")

    # Example of how to use the container to get a service explicitly
    user_service_instance = container.user_service()
    print(f"Successfully retrieved UserService instance: {user_service_instance}")

    # Example of using an injected function
    handle_new_user()

    # Register event handlers
    # In a real application, the event bus would be started and managed
    # as part of the application's lifecycle.
    event_bus = container.event_bus()
    # await event_bus.initialize() # This would be needed in an async context

    # For now, we'll just show the subscription.
    # In a real app, you might have a list of handlers to subscribe at startup.
    # event_bus.subscribe("user.registered", user_registered_handler)
    print("User onboarding handler is ready to be subscribed to the event bus.")

    print("Application setup is complete. This script would now start the bot or server.")


if __name__ == "__main__":
    main()
