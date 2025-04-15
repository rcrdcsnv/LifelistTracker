# di_container.py
"""
Dependency Injection Container - Manages application dependencies
"""
from typing import Any, Type
import inspect


class DIContainer:
    """
    A simple dependency injection container
    """

    def __init__(self):
        self._instances = {}
        self._registrations = {}

    def register(self, interface_type: Type, implementation_type: Type = None, instance: Any = None):
        """
        Register a type or instance with the container

        Args:
            interface_type: The type to register
            implementation_type: The concrete implementation type (if registering a type)
            instance: The instance to register (if registering an instance)
        """
        if instance is not None:
            self._instances[interface_type] = instance
        else:
            self._registrations[interface_type] = implementation_type or interface_type

    def resolve(self, interface_type: Type) -> Any:
        """
        Resolve a registered type to an instance

        Args:
            interface_type: The type to resolve

        Returns:
            An instance of the requested type
        """
        # Return existing instance if already created
        if interface_type in self._instances:
            return self._instances[interface_type]

        # Get the implementation type
        implementation_type = self._registrations.get(interface_type)
        if not implementation_type:
            raise ValueError(f"No registration found for {interface_type.__name__}")

        # Check constructor parameters
        constructor = implementation_type.__init__
        signature = inspect.signature(constructor)
        parameters = list(signature.parameters.values())[1:]  # Skip 'self'

        # Resolve dependencies
        args = []
        for param in parameters:
            param_type = param.annotation
            if param_type is inspect.Parameter.empty:
                # Check if parameter has a default value
                if param.default is not inspect.Parameter.empty:
                    args.append(param.default)
                    continue
                else:
                    raise ValueError(
                        f"Parameter {param.name} in {implementation_type.__name__} constructor has no type annotation")

            # Try to resolve the dependency, fall back to default if available
            try:
                arg = self.resolve(param_type)
                args.append(arg)
            except Exception as e:
                if param.default is not inspect.Parameter.empty:
                    args.append(param.default)
                else:
                    raise e

        # Create instance
        instance = implementation_type(*args)
        self._instances[interface_type] = instance
        return instance


# Create a global instance
container = DIContainer()