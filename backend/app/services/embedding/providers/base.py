from typing import Protocol, runtime_checkable
import numpy as np


@runtime_checkable
class TextProvider(Protocol):
    
    @property
    def name(self) -> str:
        """Provider kimliği — log ve metrik için."""
        ...

    @property
    def dimension(self) -> int:
        """Üretilen vektör boyutu."""
        ...

    def embed_text(self, text: str) -> np.ndarray:
       
        ...


@runtime_checkable
class ImageProvider(Protocol):
  

    @property
    def name(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    def embed_image(self, image_url: str) -> np.ndarray | None:
       
        ...