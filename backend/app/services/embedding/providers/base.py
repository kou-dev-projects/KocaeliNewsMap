from typing import Protocol, runtime_checkable
import numpy as np


@runtime_checkable
class TextProvider(Protocol):
    
    @property
    def name(self) -> str:
        ...

    @property
    def dimension(self) -> int:
        ...

    def embed_text(self, text: str) -> np.ndarray:
       
        ...