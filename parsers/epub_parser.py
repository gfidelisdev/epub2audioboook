import os
import re
import warnings
from typing import List, Dict, Any, Optional
from collections import Counter
from ebooklib import epub
from bs4 import BeautifulSoup
from .base import BaseParser
from utils.range_helper import parse_page_range

warnings.filterwarnings("ignore")

class EpubParser(BaseParser):
    def __init__(self, min_caracteres: int = 100):
        self.min_caracteres = min_caracteres

    def _extrair_blocos_item(self, html_content: bytes) -> List[str]:
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove scripts, estilos, imagens
        for tag in soup(["script", "style", "svg", "img"]):
            tag.decompose()

        linhas = []
        for elem in soup.find_all(["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "li"]):
            if elem.name == "div" and elem.find(["p", "div"]):
                continue

            texto = elem.get_text(separator=" ", strip=True)
            if texto:
                texto = re.sub(r"\s+", " ", texto)
                linhas.append(texto)

        if not linhas:
            texto_geral = soup.get_text(separator="\n", strip=True)
            linhas = [re.sub(r"\s+", " ", l) for l in texto_geral.split("\n") if l.strip()]

        return linhas

    def _detectar_cabecalho_rodape_repetitivo(self, todos_paragrafos: List[str]) -> Optional[str]:
        """
        Detecta padrões repetitivos de cabeçalho de página (ex: 'Título - Autor' no final ou início de parágrafos).
        """
        candidatos = []
        for p in todos_paragrafos:
            # Procura por sentenças curtas ou trechos colados que se repetem com frequência
            if len(p) < 80:
                candidatos.append(p.strip())
            # Também verifica se há um sufixo fixo colado em parágrafos normais
            # Ex: "... Fazia-o As Crianças do Milharal - Stephen King"
            partes = re.findall(r'([A-ZÁÉÍÓÚÂÊÔÃÕÇ][\w\s\-,]{5,50}\s*-\s*[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\w\s]{3,30})$', p)
            if partes:
                candidatos.append(partes[0].strip())

        if not candidatos:
            return None

        contagem = Counter(candidatos)
        mais_comum, qtd = contagem.most_common(1)[0]
        # Se aparece mais de 3 vezes em pontos diferentes do livro, é cabeçalho/marcador de página
        if qtd >= 3 and len(mais_comum) >= 10:
            return mais_comum
        return None

    def _dividir_em_paginas_por_cabecalho(self, paragrafos: List[str], marcador: str) -> List[str]:
        """
        Divide um texto contínuo em páginas usando o marcador repetitivo como delimitador,
        limpando o cabeçalho do áudio final.
        """
        paginas = []
        paragrafos_pagina_atual = []

        padrao_re = re.compile(re.escape(marcador) + r'\s*$', re.IGNORECASE)

        for p in paragrafos:
            # Caso 1: o próprio parágrafo é apenas o cabeçalho
            if p.strip().lower() == marcador.lower():
                if paragrafos_pagina_atual:
                    paginas.append("\n\n".join(paragrafos_pagina_atual))
                    paragrafos_pagina_atual = []
                continue

            # Caso 2: o cabeçalho veio colado no final do parágrafo na diagramação do EPUB
            if padrao_re.search(p):
                texto_limpo = padrao_re.sub('', p).strip()
                if texto_limpo:
                    paragrafos_pagina_atual.append(texto_limpo)
                if paragrafos_pagina_atual:
                    paginas.append("\n\n".join(paragrafos_pagina_atual))
                    paragrafos_pagina_atual = []
                continue

            paragrafos_pagina_atual.append(p)

        if paragrafos_pagina_atual:
            paginas.append("\n\n".join(paragrafos_pagina_atual))

        return [pag for pag in paginas if len(pag.strip()) >= 50]

    def _dividir_em_paginas_por_tamanho(self, texto_completo: str, tamanho_pagina: int = 2200) -> List[str]:
        """
        Divide texto contínuo em páginas virtuais com base no tamanho médio de caracteres
        de uma página de livro (~2.000 a 2.500 caracteres), respeitando parágrafos inteiros.
        """
        paragrafos = [p.strip() for p in texto_completo.split("\n\n") if p.strip()]
        paginas = []
        buffer_pagina = []
        chars_acumulados = 0

        for p in paragrafos:
            buffer_pagina.append(p)
            chars_acumulados += len(p)
            if chars_acumulados >= tamanho_pagina:
                paginas.append("\n\n".join(buffer_pagina))
                buffer_pagina = []
                chars_acumulados = 0

        if buffer_pagina:
            paginas.append("\n\n".join(buffer_pagina))

        return paginas

    def extrair_capitulos(
        self,
        caminho_arquivo: str,
        range_paginas: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        livro = epub.read_epub(caminho_arquivo)
        ordem_itens = [item_id for item_id, _ in livro.spine]

        # 1. Coleta os itens na ordem do spine
        itens_conteudo = []
        for item_id in ordem_itens:
            item = livro.get_item_with_id(item_id)
            if not item:
                continue
            linhas = self._extrair_blocos_item(item.get_content())
            texto = "\n\n".join(linhas)
            if len(texto) >= self.min_caracteres:
                itens_conteudo.append({
                    "id": item_id,
                    "linhas": linhas,
                    "texto": texto
                })

        if not itens_conteudo:
            return []

        # 2. Verifica se o EPUB está dividido em múltiplos arquivos (1 por capítulo/seção)
        #    ou se é um arquivo único condensando o livro inteiro.
        paginas_ou_secoes = []

        if len(itens_conteudo) > 1:
            # Caso A: EPUB já multi-arquivos
            for item in itens_conteudo:
                paginas_ou_secoes.append(item["texto"])
        else:
            # Caso B: EPUB em arquivo único (ex: index.html condensado)
            linhas = itens_conteudo[0]["linhas"]
            marcador = self._detectar_cabecalho_rodape_repetitivo(linhas)

            if marcador:
                paginas_detectadas = self._dividir_em_paginas_por_cabecalho(linhas, marcador)
                if len(paginas_detectadas) > 1:
                    paginas_ou_secoes = paginas_detectadas

            # Fallback se não houver marcador de cabeçalho detectável: páginas virtuais por volume de texto
            if not paginas_ou_secoes:
                paginas_ou_secoes = self._dividir_em_paginas_por_tamanho(itens_conteudo[0]["texto"])

        total_paginas = len(paginas_ou_secoes)
        secoes_selecionadas = parse_page_range(range_paginas, total_paginas=total_paginas)

        capitulos = []
        indice = 1

        for num, texto in enumerate(paginas_ou_secoes, start=1):
            if secoes_selecionadas is not None and num not in secoes_selecionadas:
                continue

            primeira_linha = texto.split("\n\n")[0].strip()
            titulo = primeira_linha if len(primeira_linha) < 80 else f"Página / Seção {num:02d}"

            capitulos.append({
                "indice": indice,
                "pagina": num,
                "titulo": titulo,
                "texto": texto
            })
            indice += 1

        return capitulos
