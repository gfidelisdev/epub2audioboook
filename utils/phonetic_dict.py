import json
import os
import re
from typing import Dict, Optional

class PronunciationDictionary:
    """
    Gerenciador e aplicador de dicionário de pronúncia persistente.
    Permite que o aplicativo aprenda a pronúncia correta de siglas,
    termos em inglês, jargões técnicos e nomes próprios.
    """

    ARQUIVO_PADRAO = os.path.join(os.path.dirname(__file__), "..", "dicionario_pronuncia.json")

    # Vocabulário padrão inicial para termos comuns de TI e leitura em PT-BR
    VOCABULARIO_INICIAL = {
        "ETL": "E T L",
        "SQL": "Esse-Qu-Éle",
        "NoSQL": "Nô Esse-Qu-Éle",
        "DW": "Data Warehouse",
        "BD": "banco de dados",
        "API": "A P I",
        "APIs": "A P Is",
        "OpenSource": "Open Source",
        "Open Source": "ôpen source",
        "Big Data": "Big Data",
        "Dataset": "Data sét",
        "Pipeline": "Páipilaine",
        "Machine Learning": "Machíne Lérning",
        "Deep Learning": "Díp Lérning",
        "Framework": "Frêimiuork",
        "Software": "Sóftuer",
        "Hardware": "Rárduer",
        "Bug": "Bág",
        "Bugs": "Bágs",
        "Deploy": "Deplói",
        "Backend": "Béquiend",
        "Frontend": "Fróntend",
        "XML": "X M L",
        "JSON": "Jêison",
        "CSV": "C S V",
        "HTML": "H T M L",
        "HTTP": "H T T P",
        "HTTPS": "H T T P S",
        "URL": "U R L",
        "PDF": "P D F",
        "EPUB": "E-Púb",
        "GHz": "giga-hertz",
        "MHz": "mega-hertz",
        "GB": "gigabytes",
        "TB": "terabytes",
        "MB": "megabytes",
        "KB": "quilobytes"
    }

    def __init__(self, caminho_arquivo: Optional[str] = None):
        self.caminho_arquivo = os.path.abspath(caminho_arquivo or self.ARQUIVO_PADRAO)
        self.termos: Dict[str, str] = {}
        self._carregar()

    def _carregar(self):
        """Carrega termos existentes do arquivo JSON ou cria com os padrões."""
        if os.path.exists(self.caminho_arquivo):
            try:
                with open(self.caminho_arquivo, "r", encoding="utf-8") as f:
                    self.termos = json.load(f)
            except Exception as e:
                print(f"Aviso: Não foi possível ler o dicionário de pronúncia: {e}. Usando inicial.")
                self.termos = dict(self.VOCABULARIO_INICIAL)
        else:
            self.termos = dict(self.VOCABULARIO_INICIAL)
            self._salvar()

    def _salvar(self):
        """Persiste o dicionário no disco."""
        try:
            os.makedirs(os.path.dirname(self.caminho_arquivo), exist_ok=True)
            with open(self.caminho_arquivo, "w", encoding="utf-8") as f:
                json.dump(self.termos, f, ensure_ascii=False, indent=2, sort_keys=True)
        except Exception as e:
            print(f"Erro ao salvar dicionário de pronúncia: {e}")

    def aprender_termo(self, termo: str, pronuncia: str):
        """Adiciona ou atualiza um termo e sua forma falada no dicionário persistente."""
        termo = termo.strip()
        pronuncia = pronuncia.strip()
        if not termo or not pronuncia:
            raise ValueError("Termo e pronúncia não podem ser vazios.")
        self.termos[termo] = pronuncia
        self._salvar()

    def remover_termo(self, termo: str) -> bool:
        """Remove um termo do dicionário persistente."""
        termo = termo.strip()
        if termo in self.termos:
            del self.termos[termo]
            self._salvar()
            return True
        return False

    def listar_termos(self) -> Dict[str, str]:
        """Retorna todos os termos cadastrados."""
        return dict(self.termos)

    def aplicar(self, texto: str) -> str:
        """
        Substitui termos no texto respeitando limites de palavras inteiras (word boundaries).
        Ordena por tamanho decrescente de termo para priorizar termos compostos maiores.
        """
        if not texto or not self.termos:
            return texto

        # Ordena termos por comprimento decrescente (ex: "Open Source" antes de "Open")
        termos_ordenados = sorted(self.termos.keys(), key=len, reverse=True)

        for termo in termos_ordenados:
            pronuncia = self.termos[termo]
            # Usa \b apenas se o termo começa/termina com alfanumérico
            prefixo_b = r'\b' if re.match(r'^\w', termo) else ''
            sufixo_b = r'\b' if re.match(r'.*\w$', termo) else ''
            padrao = rf'{prefixo_b}{re.escape(termo)}{sufixo_b}'

            # Se o termo for todo maiúsculo (sigla ex: ETL, DW), preserva case-sensitive estrito
            if termo.isupper() and len(termo) > 1:
                texto = re.sub(padrao, pronuncia, texto)
            else:
                texto = re.sub(padrao, pronuncia, texto, flags=re.IGNORECASE)

        return texto
