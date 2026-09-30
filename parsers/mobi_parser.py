import os
import re
import tempfile
import warnings
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from .base import BaseParser
from utils.range_helper import parse_page_range

warnings.filterwarnings("ignore")

class MobiParser(BaseParser):
    """
    Parser para livros digitais no formato .mobi (Mobipocket / Kindle antigo).
    Extrai HTML e texto contínuo utilizando descompressão limpa PalmDOC/MOBI
    e segmenta em capítulos e seções.
    """

    def __init__(self, min_caracteres: int = 100):
        self.min_caracteres = min_caracteres

    def _extrair_blocos_html(self, html_content: str) -> List[str]:
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove elementos não textuais
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

    def _dividir_em_capitulos(self, linhas: List[str]) -> List[Dict[str, Any]]:
        """
        Divide o fluxo de parágrafos em capítulos através de tags de cabeçalho
        ou títulos padronizados (ex: 'Capítulo 1', '1. Introdução').
        """
        padrao_capitulo = re.compile(
            r'^(?:(?:CAP[ÍI]TULO\s+\d+[:\-\s]*.*)|'
            r'(?:\d+\.\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ\s]{3,})|'
            r'(?:[IVXLCDM]+\.\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ\s]{3,}))',
            re.IGNORECASE
        )

        capitulos = []
        buffer_atual = []
        titulo_atual = "Início / Prefácio"
        indice = 1

        for p in linhas:
            # Se encontrar um parágrafo que seja título de capítulo e já tenhamos conteúdo acumulado
            if padrao_capitulo.match(p) and len(p) < 100:
                if buffer_atual:
                    texto_secao = "\n\n".join(buffer_atual)
                    if len(texto_secao) >= self.min_caracteres:
                        capitulos.append({
                            "indice": indice,
                            "titulo": titulo_atual,
                            "texto": texto_secao
                        })
                        indice += 1
                    buffer_atual = []
                titulo_atual = p
            else:
                buffer_atual.append(p)

        if buffer_atual:
            texto_secao = "\n\n".join(buffer_atual)
            if len(texto_secao) >= self.min_caracteres:
                capitulos.append({
                    "indice": indice,
                    "titulo": titulo_atual,
                    "texto": texto_secao
                })

        # Fallback: Se não encontrou cabeçalhos explícitos de capítulo, divide por blocos de ~2.500 caracteres
        if len(capitulos) <= 1:
            texto_completo = "\n\n".join(linhas)
            if len(texto_completo) >= self.min_caracteres:
                capitulos = []
                secoes = []
                acumulado = []
                chars = 0
                for l in linhas:
                    acumulado.append(l)
                    chars += len(l)
                    if chars >= 2500:
                        secoes.append("\n\n".join(acumulado))
                        acumulado = []
                        chars = 0
                if acumulado:
                    secoes.append("\n\n".join(acumulado))

                for i, sec in enumerate(secoes, start=1):
                    primeira_l = sec.split("\n\n")[0].strip()
                    tit = primeira_l[:60] if len(primeira_l) < 60 else f"Seção {i:02d}"
                    capitulos.append({
                        "indice": i,
                        "titulo": tit,
                        "texto": sec
                    })

        return capitulos

    def extrair_capitulos(
        self,
        caminho_arquivo: str,
        range_paginas: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        import mobi

        with tempfile.TemporaryDirectory() as tempdir:
            temp_dir_extraido, filepath_extraido = mobi.extract(caminho_arquivo)
            html_path = None

            # Localiza o arquivo HTML extraído do MOBI
            for raiz, _, arquivos in os.walk(temp_dir_extraido):
                for arq in arquivos:
                    if arq.lower().endswith(('.html', '.htm', '.xhtml')):
                        html_path = os.path.join(raiz, arq)
                        break
                if html_path:
                    break

            if not html_path or not os.path.exists(html_path):
                raise ValueError(f"Não foi possível extrair o conteúdo legível do arquivo MOBI: '{caminho_arquivo}'")

            with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
                html_content = f.read()

        linhas = self._extrair_blocos_html(html_content)
        capitulos_brutos = self._dividir_em_capitulos(linhas)

        total_capitulos = len(capitulos_brutos)
        indices_selecionados = parse_page_range(range_paginas, total_paginas=total_capitulos)

        capitulos = []
        for cap in capitulos_brutos:
            if indices_selecionados is not None and cap["indice"] not in indices_selecionados:
                continue
            capitulos.append(cap)

        return capitulos
