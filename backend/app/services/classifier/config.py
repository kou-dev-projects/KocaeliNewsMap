from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class ClassifierConfig:
    """
    Classifier ayarları.

    semantic_enabled:
      False → sadece keyword classifier çalışır, embedding hesabı yok.
      True → keyword miss durumunda semantic devreye girer.

    semantic_confidence_threshold:
      Bu değerin altındaki semantic sonuçlar UNKNOWN döner.
      0.3 başlangıç için güvenli — çok düşük false positive verir.

    keyword_only_mode:
      Production'da embedding servisi hazır değilse True yap.
      Tüm sınıflandırma keyword ile yapılır.
    """
    semantic_enabled: bool
    semantic_confidence_threshold: float
    keyword_only_mode: bool


def load_classifier_config() -> ClassifierConfig:
    return ClassifierConfig(
        semantic_enabled=os.getenv("CLASSIFIER_SEMANTIC_ENABLED", "false").lower() == "true",
        semantic_confidence_threshold=float(
            os.getenv("CLASSIFIER_SEMANTIC_THRESHOLD", "0.3")
        ),
        keyword_only_mode=os.getenv("CLASSIFIER_KEYWORD_ONLY", "true").lower() == "true",
    )