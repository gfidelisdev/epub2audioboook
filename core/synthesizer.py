import os
from typing import Optional, Callable
from utils.text_cleaner import TextCleanerPTBR
from utils.segmenter import TextSegmenterPTBR
from utils.audio_encoder import converter_para_mp3

class AudioSynthesizer:
    VOZES_DISPONIVEIS = {
        "pm_alex": "Masculina (neutra/padrão)",
        "pm_santa": "Masculina (grave/sóbria)",
        "pf_dora": "Feminina"
    }

    # Presets narrativos de Voice Blending rebalanceados para sotaque 100% brasileiro
    PRESETS_VOZES = {
        "narrador_classico": {
            "nome": "Narrador Clássico (Neutro Encorpado)",
            "composicao": {"pm_alex": 0.75, "pm_santa": 0.25}
        },
        "contador_historias": {
            "nome": "Contador de Histórias (Expressivo)",
            "composicao": {"pm_alex": 0.65, "pf_dora": 0.35}
        },
        "voz_suave": {
            "nome": "Voz Feminina Suave",
            "composicao": {"pf_dora": 0.80, "pm_alex": 0.20}
        }
    }

    def __init__(self, lang_code: str = 'p', voz: str = "pm_alex", velocidade: float = 1.0, device: Optional[str] = None):
        self.lang_code = lang_code
        self.voz_nome = voz
        self.voz_resolvida = None
        self.velocidade = velocidade
        self.taxa_amostragem = 24000
        self.pipeline = None
        self.device = device
        self._pausa_cache = {}
        self._cache_vozes = {}

    def _obter_pausa(self, duracao_segundos: float):
        """Gera silêncio com a duração especificada em segundos com cache de memória."""
        import numpy as np
        duracao_chave = round(duracao_segundos, 2)
        if duracao_chave not in self._pausa_cache:
            num_samples = int(self.taxa_amostragem * duracao_chave)
            self._pausa_cache[duracao_chave] = np.zeros(num_samples, dtype=np.float32)
        return self._pausa_cache[duracao_chave]

    def _carregar_pipeline(self):
        if self.pipeline is None:
            from kokoro import KPipeline
            self.pipeline = KPipeline(lang_code=self.lang_code, repo_id='hexgrad/Kokoro-82M')

    def resolver_voz(self, identificador_voz: str):
        """
        Carrega ou sintetiza um vetor de voz via Voice Blending.
        Suporta:
        - Nome de voz pura: 'pm_alex', 'pm_santa', 'pf_dora'
        - Nome de preset: 'narrador_classico', 'contador_historias', 'voz_suave'
        - String de composição customizada: 'pm_santa:0.7,pm_alex:0.3'
        """
        self._carregar_pipeline()

        # Verifica cache local de vozes preparadas
        if identificador_voz in self._cache_vozes:
            return self._cache_vozes[identificador_voz]

        # 1. É um preset pronto?
        if identificador_voz in self.PRESETS_VOZES:
            comp = self.PRESETS_VOZES[identificador_voz]["composicao"]
            blend = None
            for voz_base, peso in comp.items():
                tensor_v = self.pipeline.load_voice(voz_base)
                blend = tensor_v * peso if blend is None else blend + (tensor_v * peso)
            self._cache_vozes[identificador_voz] = blend
            return blend

        # 2. É uma composição personalizada inline (ex: 'pm_santa:0.7,pm_alex:0.3')?
        if ":" in identificador_voz and "," in identificador_voz:
            partes = identificador_voz.split(",")
            blend = None
            for p in partes:
                if ":" in p:
                    nome, peso_str = p.split(":", 1)
                    nome = nome.strip()
                    peso = float(peso_str.strip())
                    tensor_v = self.pipeline.load_voice(nome)
                    blend = tensor_v * peso if blend is None else blend + (tensor_v * peso)
            if blend is not None:
                self._cache_vozes[identificador_voz] = blend
                return blend

        # 3. É uma voz calibrada salva no disco (.pt)?
        if identificador_voz.startswith("calibrada_"):
            nome_arquivo_base = identificador_voz.replace("calibrada_", "")
            caminho_pt = os.path.join(os.path.dirname(__file__), "..", "vozes_calibradas", f"{nome_arquivo_base}.pt")
            if os.path.exists(caminho_pt):
                import torch
                v_calibrada = torch.load(caminho_pt, map_location="cpu")
                self._cache_vozes[identificador_voz] = v_calibrada
                return v_calibrada

        # 4. É uma voz pura do Kokoro
        v = self.pipeline.load_voice(identificador_voz)
        self._cache_vozes[identificador_voz] = v
        return v

    def sintetizar_texto(
        self,
        texto: str,
        arquivo_saida: str,
        formato: str = "mp3",
        progresso_cb: Optional[Callable[[int, int, str], None]] = None
    ) -> str:
        self._carregar_pipeline()
        voz_vetor = self.resolver_voz(self.voz_nome)

        # 1. Normaliza texto para PT-BR (moedas, ordinais, abreviações, artefatos)
        texto_limpo = TextCleanerPTBR.normalizar(texto)
        paragrafos = [p.strip() for p in texto_limpo.split("\n\n") if p.strip()]
        total_paragrafos = len(paragrafos)

        if total_paragrafos == 0:
            raise ValueError("Texto vazio após limpeza e normalização.")

        os.makedirs(os.path.dirname(arquivo_saida) or ".", exist_ok=True)
        caminho_wav_temp = arquivo_saida if formato == "wav" else f"{arquivo_saida}.temp.wav"

        amostras_audio = []

        for idx, p in enumerate(paragrafos, start=1):
            if progresso_cb:
                progresso_cb(idx, total_paragrafos, p)

            # 2. Segmenta o parágrafo em orações com prosódia calibrada
            segmentos = TextSegmenterPTBR.segmentar_frases(p)

            for seg in segmentos:
                trecho_frase = seg["texto"]
                pausa_duracao = seg["pausa"]
                fator_prosodia = seg.get("fator_velocidade", 1.0)

                if not trecho_frase.strip():
                    continue

                try:
                    # Aplica modulação de entonação/ritmo ajustando a velocidade específica do trecho
                    velocidade_trecho = round(self.velocidade * fator_prosodia, 2)
                    gerador = self.pipeline(trecho_frase, voice=voz_vetor, speed=velocidade_trecho)
                    for _, _, audio in gerador:
                        amostras_audio.append(audio)

                    # Aplica pausa calibrada pelo tipo de pontuação (., ?, !, ..., ,, ;)
                    if pausa_duracao > 0:
                        amostras_audio.append(self._obter_pausa(pausa_duracao))

                except Exception as e:
                    print(f"Aviso no trecho '{trecho_frase[:30]}...': {e}")
                    continue

            # Pausa de respiração ao final do parágrafo inteiro
            pausa_fim_paragrafo = TextSegmenterPTBR.PAUSAS["paragrafo"]
            amostras_audio.append(self._obter_pausa(pausa_fim_paragrafo))

        if not amostras_audio:
            raise RuntimeError("Nenhum áudio gerado pelo modelo.")

        import numpy as np
        import soundfile as sf

        audio_final = np.concatenate(amostras_audio)
        sf.write(caminho_wav_temp, audio_final, self.taxa_amostragem)

        if formato == "mp3":
            sucesso = converter_para_mp3(caminho_wav_temp, arquivo_saida)
            if sucesso and os.path.exists(caminho_wav_temp):
                os.remove(caminho_wav_temp)
            elif not sucesso:
                arquivo_saida = caminho_wav_temp

        return arquivo_saida
