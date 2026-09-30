import re
from typing import List, Tuple, Dict, Any

class TextSegmenterPTBR:
    """
    Segmenta texto em unidades de prosódia respeitando o tipo de pontuação final
    e contexto (diálogo, pergunta, exclamação, suspense) para aplicação de
    pausas naturais e modulação de entonação/ritmo em sintetizadores de fala (TTS).
    """

    # Tipos de pausas associadas à pontuação (segundos recomendados para audiobooks)
    PAUSAS = {
        "virgula": 0.20,       # , ; : (pausa de fôlego/respiração curta)
        "ponto_final": 0.50,   # . (conclusão de sentença)
        "pergunta": 0.55,      # ? (pausa de pergunta reflexiva)
        "exclamacao": 0.55,    # ! (pausa de ênfase)
        "reticencias": 0.70,   # ... (hesitação ou suspense dramático)
        "travessao": 0.35,     # diálogos e quebras de oração com —
        "paragrafo": 0.75,     # transição entre ideias/cenas
    }

    # Modulação de velocidade relativa para entonação expressiva
    FATOR_VELOCIDADE = {
        "normal": 1.0,
        "dialogo": 1.04,       # Diálogos costumam ter fala ligeiramente mais ágil
        "pergunta": 1.02,      # Inflexão de questionamento
        "exclamacao": 1.03,    # Ênfase / energia
        "reticencias": 0.94,   # Cadência mais lenta/dramática em reticências
    }

    @classmethod
    def segmentar_frases(cls, paragrafo: str) -> List[Dict[str, Any]]:
        """
        Divide um parágrafo em frases/cláusulas com prosódia calibrada.
        Retorna lista de dicionários:
        [
            {
                "texto": str,
                "pausa": float,
                "fator_velocidade": float,
                "tipo": str
            },
            ...
        ]
        """
        texto = paragrafo.strip()
        if not texto:
            return []

        # Identifica se o parágrafo como um todo inicia como fala direta de personagem
        paragrafo_eh_dialogo = bool(re.match(r'^[—–-]', texto))

        # Normaliza reticências para caractere único temporário para não confundir com pontos
        texto = re.sub(r'\.{3,}|…', ' … ', texto)
        
        # Divide sentenças preservando os delimitadores de pontuação e travessões
        # Reconhece: ?, !, …, ., ;, :, —
        partes = re.split(r'(?<=[.?!…;:—])\s+', texto)

        segmentos = []
        for parte in partes:
            trecho = parte.strip()
            if not trecho:
                continue

            trecho_inicia_travessao = bool(re.match(r'^[—–-]', trecho))

            # Se começar com travessão isolado (ex: início de fala de diálogo '— Olá'), remove o travessão inicial
            trecho_processado = re.sub(r'^[—–-]\s*', '', trecho).strip()
            if not trecho_processado:
                continue

            eh_dialogo = paragrafo_eh_dialogo or trecho_inicia_travessao

            # Determina o tipo de pontuação, pausa e fator de velocidade prosódica
            pausa = 0.0
            tipo = "normal"
            fator_velocidade = cls.FATOR_VELOCIDADE["normal"]

            if re.search(r'\.{3,}$|…$', trecho_processado):
                pausa = cls.PAUSAS["reticencias"]
                tipo = "reticencias"
                fator_velocidade = cls.FATOR_VELOCIDADE["reticencias"]
            elif trecho_processado.endswith('?'):
                pausa = cls.PAUSAS["pergunta"]
                tipo = "pergunta"
                fator_velocidade = cls.FATOR_VELOCIDADE["pergunta"]
            elif trecho_processado.endswith('!'):
                pausa = cls.PAUSAS["exclamacao"]
                tipo = "exclamacao"
                fator_velocidade = cls.FATOR_VELOCIDADE["exclamacao"]
            elif trecho_processado.endswith('.'):
                pausa = cls.PAUSAS["ponto_final"]
                tipo = "ponto_final"
            elif re.search(r'[,;:]$', trecho_processado):
                pausa = cls.PAUSAS["virgula"]
                tipo = "virgula"
            elif re.search(r'[—–-]$', trecho_processado):
                pausa = cls.PAUSAS["travessao"]
                tipo = "travessao"
                trecho_processado = trecho_processado.rstrip('—–- ').strip()

            if eh_dialogo and tipo not in ["reticencias"]:
                fator_velocidade = cls.FATOR_VELOCIDADE["dialogo"]

            # Restaura reticências para o formato padrão legível
            trecho_limpo = trecho_processado.replace('…', '...')
            if trecho_limpo:
                segmentos.append({
                    "texto": trecho_limpo,
                    "pausa": pausa,
                    "fator_velocidade": fator_velocidade,
                    "tipo": tipo
                })

        # Se nenhuma pontuação casou, retorna o trecho como um todo
        if not segmentos:
            segmentos.append({
                "texto": texto.replace('…', '...'),
                "pausa": cls.PAUSAS["ponto_final"],
                "fator_velocidade": cls.FATOR_VELOCIDADE["normal"],
                "tipo": "ponto_final"
            })

        return segmentos
