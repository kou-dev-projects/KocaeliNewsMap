class NERError(Exception):
    """Tüm NER hataları buradan türer."""


class ProviderUnavailableError(NERError):
    """Model yüklenemedi veya yanıt vermedi."""


class NormalizationError(NERError):
    """Metin normalizasyonu başarısız."""