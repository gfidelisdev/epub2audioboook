import os
import sys
import click
from parsers import get_parser
from core.synthesizer import AudioSynthesizer

@click.group()
def cli():
    """epub2audiobook - Conversor de EPUB, PDF e Textos para Audiobook em PT-BR."""
    pass

@cli.command("extrair")
@click.argument("arquivo", type=click.Path(exists=True))
@click.option("--paginas", "-p", default=None, type=str, help="Intervalo de páginas/seções a extrair (ex: '1-10', '5', '10-20').")
@click.option("--saida", "-o", default="capitulos_extraidos", help="Diretório onde salvar os capítulos extraídos.")
def extrair_cmd(arquivo, paginas, saida):
    """Extrai os capítulos de um livro (EPUB, PDF, TXT) em arquivos de texto separados."""
    click.echo(f"Carregando parser para: {arquivo}")
    try:
        parser = get_parser(arquivo)
        capitulos = parser.extrair_capitulos(arquivo, range_paginas=paginas)
        os.makedirs(saida, exist_ok=True)

        click.echo(f"Total de capítulos/seções identificados: {len(capitulos)}")
        for cap in capitulos:
            nome_arquivo = os.path.join(saida, f"capitulo_{cap['indice']:02d}.txt")
            with open(nome_arquivo, "w", encoding="utf-8") as f:
                f.write(cap["texto"])
            rotulo_pag = f" [Pág {cap['pagina']}]" if "pagina" in cap else ""
            click.echo(f"  -> Salvo: {nome_arquivo}{rotulo_pag} ({cap['titulo'][:50]})")

        click.echo(f"\nExtração concluída com sucesso em: {saida}/")
    except Exception as e:
        click.echo(f"Erro ao extrair capítulos: {e}", err=True)
        sys.exit(1)

@cli.command("converter")
@click.argument("arquivo", type=click.Path(exists=True))
@click.option("--paginas", "-p", default=None, type=str, help="Intervalo de páginas/seções a narrar (ex: '1-10', '5', '10-20').")
@click.option("--voz", "-v", default="pm_alex",
              help="Voz pura (pm_alex, pm_santa, pf_dora) ou Preset (narrador_classico, contador_historias, voz_suave) ou Mix (ex: 'pm_santa:0.7,pm_alex:0.3').")
@click.option("--velocidade", "-s", default=1.0, type=float, help="Velocidade da fala (ex: 1.0, 1.1).")
@click.option("--saida", "-o", default="audio", help="Diretório de saída para os áudios.")
@click.option("--formato", "-f", default="mp3", type=click.Choice(["mp3", "wav"]), help="Formato do arquivo de áudio final.")
@click.option("--capitulo", "-c", default=None, type=int, help="Processa apenas o capítulo especificado pelo índice.")
def converter_cmd(arquivo, paginas, voz, velocidade, saida, formato, capitulo):
    """Processa diretamente um arquivo (EPUB, PDF, TXT) e gera os áudios narrados."""
    click.echo(f"Iniciando conversão de: {arquivo}")
    try:
        parser = get_parser(arquivo)
        capitulos = parser.extrair_capitulos(arquivo, range_paginas=paginas)
        if not capitulos:
            click.echo("Nenhum conteúdo pôde ser extraído do arquivo com os filtros aplicados.", err=True)
            sys.exit(1)

        if capitulo is not None:
            capitulos = [c for c in capitulos if c["indice"] == capitulo]
            if not capitulos:
                click.echo(f"Capítulo {capitulo} não encontrado.", err=True)
                sys.exit(1)

        # Se a saída for a padrão 'audio' ou um diretório base, organiza em subpasta com o nome do livro
        nome_base_livro = os.path.splitext(os.path.basename(arquivo))[0]
        pasta_livro = os.path.join(saida, nome_base_livro) if saida == "audio" or not saida.endswith(nome_base_livro) else saida
        os.makedirs(pasta_livro, exist_ok=True)

        sintetizador = AudioSynthesizer(lang_code='p', voz=voz, velocidade=velocidade)

        total = len(capitulos)
        click.echo(f"Total de capítulos para narrar: {total}")
        click.echo(f"Diretório de destino: {pasta_livro}/")

        for i, cap in enumerate(capitulos, start=1):
            arq_saida = os.path.join(pasta_livro, f"capitulo_{cap['indice']:02d}.{formato}")
            click.echo(f"\n[{i}/{total}] Narrando: {cap['titulo']} -> {arq_saida}")

            def callback_progresso(idx, total_p, texto_p):
                previa = (texto_p[:45] + "...") if len(texto_p) > 45 else texto_p
                click.echo(f"   [{idx}/{total_p}] {previa}")

            sintetizador.sintetizar_texto(
                texto=cap["texto"],
                arquivo_saida=arq_saida,
                formato=formato,
                progresso_cb=callback_progresso
            )

        click.echo(f"\nTodos os áudios foram gerados com sucesso na pasta: {pasta_livro}/")

    except Exception as e:
        click.echo(f"Erro durante a conversão: {e}", err=True)
        sys.exit(1)

@cli.command("vozes")
def vozes_cmd():
    """Lista as vozes disponíveis para o idioma português."""
    click.echo("Vozes puras em Português:")
    for cod, desc in AudioSynthesizer.VOZES_DISPONIVEIS.items():
        click.echo(f"  - {cod:<20}: {desc}")

    click.echo("\nPresets de Voice Blending (Mix):")
    for cod, info in AudioSynthesizer.PRESETS_VOZES.items():
        comp_str = " + ".join([f"{int(p*100)}% {v}" for v, p in info["composicao"].items()])
        click.echo(f"  - {cod:<20}: {info['nome']} ({comp_str})")

    from core.calibrator import VoiceCalibrator
    calibradas = VoiceCalibrator.listar_vozes_calibradas()
    if calibradas:
        click.echo("\nVozes Calibradas pelo Usuário:")
        for cod, desc in calibradas.items():
            click.echo(f"  - {cod:<20}: {desc}")

@cli.command("calibrar")
@click.argument("audio", type=click.Path(exists=True))
@click.option("--nome", "-n", default="minha_voz_calibrada", help="Nome identificador da nova voz calibrada.")
@click.option("--base", "-b", default="pm_alex", help="Voz base de partida (pm_alex, pm_santa, pf_dora).")
@click.option("--peso", "-w", default=0.35, type=float, help="Intensidade da calibração (0.1 a 0.6).")
def calibrar_cmd(audio, nome, base, peso):
    """Calibra uma nova voz a partir de um áudio de referência com transcrição Whisper."""
    from core.calibrator import VoiceCalibrator
    calibrador = VoiceCalibrator()
    click.echo(f"Processando áudio de referência: {audio}")
    click.echo("Transcrevendo com Whisper local...")
    try:
        texto = calibrador.transcrever_audio(audio)
        click.echo(f"\n--- Transcrição Automática ---\n{texto}\n------------------------------")
        
        # Permite ao usuário revisar e confirmar a transcrição no terminal
        if click.confirm("Deseja utilizar esta transcrição para a calibração?", default=True):
            texto_final = texto
        else:
            texto_final = click.prompt("Digite ou cole a transcrição revisada", default=texto)

        click.echo("Calibrando matriz acústica e prosódia...")
        res = calibrador.calibrar(
            caminho_audio=audio,
            transcricao_revisada=texto_final,
            nome_nova_voz=nome,
            voz_base=base,
            peso_ajuste=peso
        )
        click.echo(f"\n✨ Voz calibrada salva com sucesso como: 'calibrada_{nome}'")
        click.echo(f"   Velocidade recomendada calculada: {res['velocidade_recomendada']}x")
        click.echo(f"   Use agora com: python cli.py converter livro.epub --voz calibrada_{nome}")
    except Exception as e:
        click.echo(f"Erro na calibração: {e}", err=True)
        sys.exit(1)

@cli.command("ui")
@click.option("--porta", "-p", default=8501, type=int, help="Porta onde rodar a interface Streamlit.")
@click.option("--host", default="0.0.0.0", help="Endereço de rede para escuta da interface.")
def ui_cmd(porta, host):
    """Inicia a interface de usuário gráfica (Web) com Streamlit."""
    import subprocess
    click.echo(f"Iniciando interface Web em http://localhost:{porta} ...")
    app_path = os.path.join(os.path.dirname(__file__), "ui_app.py")
    cmd = [
        sys.executable, "-m", "streamlit", "run", app_path,
        "--server.port", str(porta),
        "--server.address", host,
        "--browser.gatherUsageStats", "false"
    ]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        click.echo("\nInterface encerrada.")

@cli.command("baixar-modelos")
def baixar_modelos_cmd():
    """Pré-baixa os modelos neurais e pesos de vozes no cache persistente."""
    caminho_cache = os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
    click.echo(f"Diretório de cache de modelos: {caminho_cache}")
    click.echo("Verificando / baixando modelo Kokoro-82M e vozes em Português...")
    try:
        from kokoro import KPipeline
        pipeline = KPipeline(lang_code='p', repo_id='hexgrad/Kokoro-82M')
        # Pré-carrega cada voz para garantir que os arquivos estejam no cache local
        for voz in AudioSynthesizer.VOZES_DISPONIVEIS.keys():
            click.echo(f"  -> Cacheando voz '{voz}'...")
            pipeline.load_voice(voz)
        click.echo("Modelos e vozes prontos no cache local!")
    except Exception as e:
        click.echo(f"Erro ao baixar modelos: {e}", err=True)
        sys.exit(1)

@cli.group("pronuncia")
def pronuncia_group():
    """Gerencia o aprendizado e dicionário fonético de termos/siglas."""
    pass

@pronuncia_group.command("aprender")
@click.argument("termo")
@click.argument("pronuncia")
def aprender_pronuncia_cmd(termo, pronuncia):
    """Ensina uma nova pronúncia para uma sigla ou palavra técnica.
    
    Exemplo: cli.py pronuncia aprender 'ETL' 'E T L'
    """
    from utils.phonetic_dict import PronunciationDictionary
    dicionario = PronunciationDictionary()
    dicionario.aprender_termo(termo, pronuncia)
    click.echo(f"Termo aprendido: '{termo}' -> '{pronuncia}'")

@pronuncia_group.command("listar")
def listar_pronuncia_cmd():
    """Lista todos os termos cadastrados no dicionário de pronúncia."""
    from utils.phonetic_dict import PronunciationDictionary
    dicionario = PronunciationDictionary()
    termos = dicionario.listar_termos()
    click.echo(f"Total de termos aprendidos: {len(termos)}")
    for t, p in sorted(termos.items()):
        click.echo(f"  - {t:<20}: {p}")

@pronuncia_group.command("remover")
@click.argument("termo")
def remover_pronuncia_cmd(termo):
    """Remove um termo do dicionário de pronúncia."""
    from utils.phonetic_dict import PronunciationDictionary
    dicionario = PronunciationDictionary()
    removido = dicionario.remover_termo(termo)
    if removido:
        click.echo(f"Termo '{termo}' removido com sucesso.")
    else:
        click.echo(f"Termo '{termo}' não encontrado no dicionário.", err=True)

if __name__ == "__main__":
    cli()
