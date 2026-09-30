import re
from typing import List, Dict, Any, Optional
from pypdf import PdfReader
from .base import BaseParser
from collections import Counter
from utils.range_helper import parse_page_range

class PdfParser(BaseParser):
    def __init__(self, min_caracteres: int = 100):
        self.min_caracteres = min_caracteres

    def _detectar_cabecalhos_rodapes(self, reader: PdfReader):
        """
        Analisa o documento e identifica linhas de cabeçalho e rodapé recorrentes
        (como títulos do livro repetidos no topo de todas as páginas).
        """
        first_lines = []
        last_lines = []
        for page in reader.pages:
            text = page.extract_text() or ""
            raw_lines = [l.strip() for l in text.split('\n') if l.strip()]
            lines = [l for l in raw_lines if not re.fullmatch(r'\d+', l)]
            if lines:
                first_lines.append(lines[0])
                if len(lines) > 1:
                    first_lines.append(lines[1])
                last_lines.append(lines[-1])
                if len(lines) > 1:
                    last_lines.append(lines[-2])

        min_repeticoes = max(3, int(len(reader.pages) * 0.05))
        cabecalhos = {t for t, cnt in Counter(first_lines).items() if cnt >= min_repeticoes and len(t) > 3}
        rodapes = {t for t, cnt in Counter(last_lines).items() if cnt >= min_repeticoes and len(t) > 3}
        return cabecalhos, rodapes

    def _limpar_texto_pagina(
        self,
        texto: str,
        cabecalhos_repetitivos: Optional[set] = None,
        rodapes_repetitivos: Optional[set] = None
    ) -> str:
        if not texto:
            return ""

        cabecalhos = cabecalhos_repetitivos or set()
        rodapes = rodapes_repetitivos or set()

        # Remove hifenização no final de linhas: "exem- \nplo" -> "exemplo"
        texto = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', texto)

        # Junta linhas quebradas arbitrariamente dentro de um parágrafo
        linhas = texto.split('\n')
        paragrafos = []
        paragrafo_atual = []

        for linha in linhas:
            linha_str = linha.strip()
            if not linha_str:
                if paragrafo_atual:
                    paragrafos.append(" ".join(paragrafo_atual))
                    paragrafo_atual = []
            else:
                # Ignora linhas que são apenas números de página
                if re.fullmatch(r'\d+', linha_str):
                    continue
                # Ignora cabeçalhos ou rodapés repetitivos de topo/fundo de página
                if linha_str in cabecalhos or linha_str in rodapes:
                    continue

                paragrafo_atual.append(linha_str)

        if paragrafo_atual:
            paragrafos.append(" ".join(paragrafo_atual))

        texto_limpo = "\n\n".join(paragrafos)
        texto_limpo = re.sub(r'[ \t]+', ' ', texto_limpo)
        return texto_limpo

    def extrair_capitulos(
        self,
        caminho_arquivo: str,
        range_paginas: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        reader = PdfReader(caminho_arquivo)
        total_paginas = len(reader.pages)
        paginas_selecionadas = parse_page_range(range_paginas, total_paginas=total_paginas)

        # Detecta cabeçalhos e rodapés repetidos para evitar narração duplicada a cada página
        cabecalhos_repetidos, rodapes_repetidos = self._detectar_cabecalhos_rodapes(reader)

        padrao_capitulo = re.compile(
            r'^(?:(?:CAP[ÍI]TULO\s+\d+[:\-\s]*.*)|'
            r'(?:\d+\.\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ\s]{3,})|'
            r'(?:[IVXLCDM]+\.\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ\s]{3,}))',
            re.IGNORECASE
        )

        capitulos = []
        indice = 1

        for num_pagina, pagina in enumerate(reader.pages, start=1):
            if paginas_selecionadas is not None and num_pagina not in paginas_selecionadas:
                continue

            texto_bruto = pagina.extract_text() or ""
            texto = self._limpar_texto_pagina(
                texto_bruto,
                cabecalhos_repetitivos=cabecalhos_repetidos,
                rodapes_repetitivos=rodapes_repetidos
            )

            if len(texto) < self.min_caracteres:
                continue

            # Tenta inferir se a página inicia um capítulo/seção pelo primeiro parágrafo
            primeiro_paragrafo = texto.split("\n\n")[0].strip()
            match_cap = padrao_capitulo.match(primeiro_paragrafo)
            if match_cap and not re.search(r'\.{3,}\s*\d+$', primeiro_paragrafo):
                titulo = match_cap.group(0).strip()
            else:
                titulo = f"Página {num_pagina:02d}"

            capitulos.append({
                "indice": indice,
                "pagina": num_pagina,
                "titulo": titulo,
                "texto": texto
            })
            indice += 1

        return capitulos
