from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseParser(ABC):
    """Classe base para extração de capítulos e texto de diferentes formatos."""

    @abstractmethod
    def extrair_capitulos(
        self,
        caminho_arquivo: str,
        range_paginas: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Extrai capítulos ou páginas do arquivo.
        range_paginas: string opcional com intervalo (ex: '1-10', '5', '10-20').
        Retorna uma lista de dicionários no formato:
        [
            {
                "indice": 1,
                "titulo": "Capítulo 1",
                "texto": "Conteúdo...",
                "pagina": 1 # opcional, quando aplicável
            },
            ...
        ]
        """
        pass
