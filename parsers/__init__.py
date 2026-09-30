import os
from .base import BaseParser
from .epub_parser import EpubParser
from .pdf_parser import PdfParser
from .text_parser import TextParser
from .mobi_parser import MobiParser

def get_parser(caminho_arquivo: str) -> BaseParser:
    ext = os.path.splitext(caminho_arquivo)[1].lower()
    if ext == ".epub":
        return EpubParser()
    elif ext == ".pdf":
        return PdfParser()
    elif ext == ".mobi":
        return MobiParser()
    elif ext in [".txt", ".md", ".text"]:
        return TextParser()
    else:
        raise ValueError(f"Formato não suportado: '{ext}'. Suportados: .epub, .pdf, .mobi, .txt, .md")

__all__ = ["BaseParser", "EpubParser", "PdfParser", "TextParser", "MobiParser", "get_parser"]
