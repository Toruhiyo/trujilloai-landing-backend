class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class DynamicSingleton(type):
    """A class that creates a new instance when input parameters change,\
        but returns the same instance when the same input parameters are used."""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        # Serialize the kwargs dictionary into a hashable format
        key = (cls, str(args), str(kwargs.items()))

        if key not in cls._instances:
            cls._instances[key] = super().__call__(*args, **kwargs)

        return cls._instances[key]
