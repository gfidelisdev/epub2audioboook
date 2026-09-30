import os
import re
from typing import List, Dict, Any, Optional
from .base import BaseParser
from utils.range_helper import parse_page_range

class TextParser(BaseParser):
    def extrair_capitulos(
        self,
        caminho_arquivo: str,
        range_paginas: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        with open(caminho_arquivo, "r", encoding="utf-8", errors="replace") as f:
            conteudo = f.read()

        # Tenta quebrar por padrões comuns de capítulos (ex: # Capítulo, Capítulo 1, Cap. 1)
        partes = re.split(r'\n(?=(?:#+\s+|[Cc]ap[ií]tulo\s+\d+|[Cc]hapter\s+\d+))', conteudo)
        
        blocos_validos = []
        for parte in partes:
            texto = parte.strip()
            if texto:
                blocos_validos.append(texto)

        # Se não houver divisões claras de capítulos, trata como capítulo único
        if not blocos_validos and conteudo.strip():
            blocos_validos.append(conteudo.strip())

        total_blocos = len(blocos_validos)
        blocos_selecionados = parse_page_range(range_paginas, total_paginas=total_blocos)

        capitulos = []
        indice = 1

        for num_bloco, texto in enumerate(blocos_validos, start=1):
            if blocos_selecionados is not None and num_bloco not in blocos_selecionados:
                continue

            primeira_linha = texto.split("\n")[0].strip("# ").strip()
            titulo = primeira_linha if len(primeira_linha) < 80 else f"Capítulo {num_bloco:02d}"

            capitulos.append({
                "indice": indice,
                "pagina": num_bloco,
                "titulo": titulo,
                "texto": texto
            })
            indice += 1

        return capitulos
