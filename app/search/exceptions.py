class SearchUnavailableError(RuntimeError):
    """Raised when the search backend cannot serve a request."""