class EmbeddingError(Exception):
    """Tüm embedding hataları buradan türer."""


class VectorDimensionError(EmbeddingError):
    def __init__(self, expected: int, actual: int) -> None:
        super().__init__(
            f"Vektör boyutu hatalı — beklenen: {expected}, gelen: {actual}"
        )
        self.expected = expected
        self.actual = actual


class ImageFetchError(EmbeddingError):
    """Görsel indirilemedi. Non-fatal — metin embedding devam eder."""


class ProviderUnavailableError(EmbeddingError):
    """Model yüklenemedi veya yanıt vermedi."""