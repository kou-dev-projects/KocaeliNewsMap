class EmbeddingError(Exception):
    pass


class VectorDimensionError(EmbeddingError):
    def __init__(self, expected: int, actual: int) -> None:
        super().__init__(
            f"Vektör boyutu hatalı — beklenen: {expected}, gelen: {actual}"
        )
        self.expected = expected
        self.actual = actual


class ImageFetchError(EmbeddingError):
    pass


class ProviderUnavailableError(EmbeddingError):
    pass
