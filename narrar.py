import sys
import os
import soundfile as sf
import numpy as np
from kokoro import KPipeline

# Idioma em português: 'p' (para inglês seria 'a' ou 'b')
pipeline = KPipeline(lang_code='p')

def narrar_arquivo(caminho_txt, voz="pm_alex", arquivo_saida="audio/narracao_completa.wav"):
    """
    Vozes disponíveis em português (Kokoro v0.8.4+):
      - 'pm_alex'  (Masculina, padrão/neutra)
      - 'pm_santa' (Masculina, mais grave/sóbria)
      - 'pf_dora'  (Feminina)
    """
    if not os.path.exists(caminho_txt):
        print(f"Erro: Arquivo '{caminho_txt}' não encontrado.")
        return

    with open(caminho_txt, "r", encoding="utf-8") as f:
        conteudo = f.read()

    # Separa por quebras de parágrafo reais
    paragrafos = [p.strip() for p in conteudo.split("\n\n") if p.strip()]
    total_paragrafos = len(paragrafos)

    print(f"Iniciando narração de '{caminho_txt}'")
    print(f"Total de parágrafos: {total_paragrafos} | Voz: {voz}")

    taxa_amostragem = 24000
    # 450ms de pausa natural e respiração entre parágrafos
    pausa_paragrafo = np.zeros(int(taxa_amostragem * 0.45), dtype=np.float32)
    
    amostras_audio = []

    for idx, p in enumerate(paragrafos, start=1):
        # Mostra progresso e uma prévia do parágrafo atual
        previa = (p[:50] + "...") if len(p) > 50 else p
        print(f"[{idx}/{total_paragrafos}] ({len(p)} caracteres) {previa}")

        try:
            # O Kokoro faz o chunking interno por frases/pontuações
            generator = pipeline(p, voice=voz, speed=1.0)
            for _, _, audio in generator:
                amostras_audio.append(audio)
            
            # Adiciona respiro ao fim do parágrafo
            amostras_audio.append(pausa_paragrafo)

        except Exception as e:
            print(f"Aviso: Erro ao narrar o parágrafo {idx}: {e}")
            continue

    if not amostras_audio:
        print("Nenhum áudio pôde ser gerado.")
        return

    # Garante que a pasta de saída exista
    os.makedirs(os.path.dirname(arquivo_saida) or ".", exist_ok=True)

    print("\nConcatenando faixas e gravando áudio final...")
    audio_final = np.concatenate(amostras_audio)
    sf.write(arquivo_saida, audio_final, taxa_amostragem)
    
    duracao_segundos = len(audio_final) / taxa_amostragem
    minutos = int(duracao_segundos // 60)
    segundos = int(duracao_segundos % 60)
    print(f"Concluído! Áudio salvo em: {arquivo_saida}")
    print(f"Duração total: {minutos}m {segundos}s")

if __name__ == "__main__":
    # Permite passar parâmetros via CLI: python narrar.py capitulo.txt [voz] [saida.wav]
    arquivo_entrada = sys.argv[1] if len(sys.argv) > 1 else "capitulos_extraidos/capitulo_01.txt"
    voz_escolhida = sys.argv[2] if len(sys.argv) > 2 else "pm_alex"
    arquivo_saida = sys.argv[3] if len(sys.argv) > 3 else "audio/capitulo_01.wav"

    narrar_arquivo(arquivo_entrada, voz=voz_escolhida, arquivo_saida=arquivo_saida)