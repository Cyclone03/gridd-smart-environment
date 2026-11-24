class CollectionError(Exception):
    """Erreur explicite pendant la collecte des données."""


class HttpRequestError(CollectionError):
    def __init__(self, message, *, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class OpenMeteoError(CollectionError):
    pass


class IncompleteWeatherResponse(OpenMeteoError):
    pass


class GriddApiError(CollectionError):
    pass


class InvalidGriddResponse(GriddApiError):
    pass


class UnknownZoneError(GriddApiError):
    pass


class IncompleteObservationsError(GriddApiError):
    pass


class TimestampFormatError(ValueError):
    pass
