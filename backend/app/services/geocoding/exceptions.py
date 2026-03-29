
class GeocodingError(Exception):
    pass

class ProviderError(GeocodingError):
    pass


class ProviderRateLimitError(ProviderError):

    def __init__(self, provider: str, retry_after: float = 1.0) -> None:
        super().__init__(f"{provider} rate limit — {retry_after}s sonra dene")
        self.provider = provider
        self.retry_after = retry_after


class ProviderUnavailableError(ProviderError):
    pass


class OutOfBoundsError(GeocodingError):

    def __init__(self, address: str, lat: float, lng: float, display: str) -> None:
        super().__init__(
            f"Kocaeli dışı koordinat: '{address}' → ({lat:.4f}, {lng:.4f}) — {display[:60]}"
        )
        self.address = address
        self.lat = lat
        self.lng = lng
        self.display = display


class LowConfidenceError(GeocodingError):

    def __init__(self, address: str, confidence: float, minimum: float) -> None:
        super().__init__(
            f"Düşük confidence: '{address}' → {confidence:.3f} < {minimum:.3f}"
        )
        self.address = address
        self.confidence = confidence
        self.minimum = minimum