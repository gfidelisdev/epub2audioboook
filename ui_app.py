import os
import sys
import tempfile
import streamlit as st

from parsers import get_parser
from core.synthesizer import AudioSynthesizer
from utils.phonetic_dict import PronunciationDictionary

st.set_page_config(
    page_title="epub2audiobook | Conversor de Livros em Áudio",
    page_icon="🎙️",
    layout="wide"
)

st.title("🎙️ epub2audiobook - Conversor Local para Audiobook")
st.caption("Síntese neural local em Português Brasileiro (PT-BR) com prosódia e aprendizado contínuo.")

tab_conversao, tab_calibrador, tab_pronuncia, tab_vozes = st.tabs([
    "📖 Conversão de Livros",
    "🎙️ Calibrador de Voz",
    "🧠 Dicionário de Pronúncia",
    "🎛️ Vozes & Presets"
])

# -------------------------------------------------------------
# ABA 1: CONVERSÃO DE LIVROS
# -------------------------------------------------------------
with tab_conversao:
    col_upload, col_configs = st.columns([1.2, 1])

    with col_upload:
        st.subheader("1. Selecione o Livro Fonte")
        arquivo_up = st.file_uploader(
            "Arraste ou selecione o arquivo (.epub, .pdf, .mobi, .txt, .md):",
            type=["epub", "pdf", "mobi", "txt", "md"]
        )

        capitulos_extraidos = []
        if arquivo_up:
            ext = os.path.splitext(arquivo_up.name)[1].lower()
            temp_book_path = os.path.join(tempfile.gettempdir(), arquivo_up.name)
            with open(temp_book_path, "wb") as f:
                f.write(arquivo_up.getbuffer())

            try:
                parser = get_parser(temp_book_path)
                with st.spinner("Analisando estrutura e extraindo capítulos..."):
                    capitulos_extraidos = parser.extrair_capitulos(temp_book_path)
                st.success(f"Livro carregado com sucesso! Total de capítulos/seções: {len(capitulos_extraidos)}")
            except Exception as e:
                st.error(f"Erro ao processar livro: {e}")

    with col_configs:
        st.subheader("2. Configuração de Voz e Ritmo")

        from core.calibrator import VoiceCalibrator
        vozes_calibradas = VoiceCalibrator.listar_vozes_calibradas()

        opcoes_vozes = {
            "pm_alex": "pm_alex - Masculina (Padrão/Neutra)",
            "pm_santa": "pm_santa - Masculina (Grave/Sóbria)",
            "pf_dora": "pf_dora - Feminina",
            "narrador_classico": "★ Narrador Clássico (75% Alex + 25% Santa)",
            "contador_historias": "★ Contador de Histórias (65% Alex + 35% Dora)",
            "voz_suave": "★ Voz Suave (80% Dora + 20% Alex)"
        }
        # Adiciona as vozes calibradas pelo usuário no topo
        if vozes_calibradas:
            opcoes_vozes = {**vozes_calibradas, **opcoes_vozes}

        voz_selecionada = st.selectbox(
            "Perfil Vocal / Preset:",
            options=list(opcoes_vozes.keys()),
            format_func=lambda x: opcoes_vozes[x],
            index=0
        )

        velocidade = st.slider(
            "Velocidade da fala:",
            min_value=0.8,
            max_value=1.4,
            value=1.0,
            step=0.05,
            help="1.0 é o ritmo padrão de leitura de audiolivro."
        )

        pasta_saida = st.text_input("Pasta de Saída dos Áudios:", value="audio")

    st.markdown("---")
    st.subheader("3. Capítulos e Execução da Narração")

    if capitulos_extraidos:
        opcoes_caps = [f"[{c['indice']:02d}] {c['titulo']}" for c in capitulos_extraidos]
        caps_selecionados = st.multiselect(
            "Selecione os capítulos que deseja narrar (vazio = narrar todos):",
            options=opcoes_caps,
            default=[]
        )

        # Prévia de texto
        cap_preview_idx = st.selectbox(
            "Visualizar prévia do texto do capítulo:",
            options=range(len(capitulos_extraidos)),
            format_func=lambda i: opcoes_caps[i]
        )
        if cap_preview_idx is not None:
            with st.expander("Prévia do Texto Limpo"):
                st.text_area("Conteúdo:", value=capitulos_extraidos[cap_preview_idx]["texto"][:1500] + "...", height=180, disabled=True)

        if st.button("🚀 Iniciar Narração do Audiobook", type="primary", use_container_width=True):
            caps_para_processar = capitulos_extraidos
            if caps_selecionados:
                indices_escolhidos = [int(item[1:3]) for item in caps_selecionados]
            # Cria subpasta com o nome base do livro para separar e não sobrescrever livros diferentes
            nome_livro_base = os.path.splitext(arquivo_up.name)[0]
            pasta_destino_livro = os.path.join(pasta_saida, nome_livro_base) if pasta_saida == "audio" or not pasta_saida.endswith(nome_livro_base) else pasta_saida
            os.makedirs(pasta_destino_livro, exist_ok=True)

            barra_progresso = st.progress(0.0)
            status_box = st.empty()
            audio_players = st.container()

            try:
                sintetizador = AudioSynthesizer(lang_code='p', voz=voz_selecionada, velocidade=velocidade)
                total_c = len(caps_para_processar)

                for i, cap in enumerate(caps_para_processar, start=1):
                    arq_mp3 = os.path.join(pasta_destino_livro, f"capitulo_{cap['indice']:02d}.mp3")
                    status_box.info(f"Narrando [{i}/{total_c}]: **{cap['titulo']}**...")

                    def callback_prog(p_idx, p_tot, p_txt):
                        pct = ((i - 1) / total_c) + (p_idx / p_tot) * (1 / total_c)
                        barra_progresso.progress(min(pct, 1.0))

                    sintetizador.sintetizar_texto(
                        texto=cap["texto"],
                        arquivo_saida=arq_mp3,
                        formato="mp3",
                        progresso_cb=callback_prog
                    )

                    with audio_players:
                        st.write(f"✅ **{cap['titulo']}** salvo em `{arq_mp3}`:")
                        with open(arq_mp3, "rb") as f_audio:
                            st.audio(f_audio.read(), format="audio/mp3")

                barra_progresso.progress(1.0)
                status_box.success(f"🎉 Conversão concluída com sucesso! Áudios salvos na pasta: `{pasta_destino_livro}/`")

            except Exception as e:
                st.error(f"Erro durante a narração: {e}")
    else:
        st.info("Envie um livro acima para visualizar e selecionar os capítulos.")


# -------------------------------------------------------------
# ABA 2: CALIBRADOR DE VOZ (ÁUDIO + TRANSCRIÇÃO REVISADA)
# -------------------------------------------------------------
with tab_calibrador:
    st.subheader("🎙️ Calibrar Perfil de Voz com Áudio de Referência")
    st.write(
        "Forneça um áudio com a entonação, timbre e naturalidade que você aprecia. "
        "O sistema transcreverá a fala usando o modelo Whisper local (offline), exibirá o texto para sua revisão "
        "e, com o seu aval, calibrará o perfil acústico para gerar uma nova voz personalizada."
    )

    from core.calibrator import VoiceCalibrator
    calibrador = VoiceCalibrator()

    col_up_aud, col_info_aud = st.columns([1.2, 1])

    with col_up_aud:
        audio_ref_file = st.file_uploader(
            "Selecione um áudio de referência (.wav, .mp3, .ogg, .m4a):",
            type=["wav", "mp3", "ogg", "m4a"],
            key="calib_audio_uploader"
        )

        if audio_ref_file:
            caminho_temp_ref = os.path.join(tempfile.gettempdir(), f"ref_{audio_ref_file.name}")
            with open(caminho_temp_ref, "wb") as f:
                f.write(audio_ref_file.getbuffer())
            st.audio(audio_ref_file, format=f"audio/{audio_ref_file.type.split('/')[-1] if '/' in audio_ref_file.type else 'mp3'}")

    with col_info_aud:
        st.markdown("**Configurações de Calibração**")
        nome_calibrada = st.text_input("Nome da Nova Voz Calibrada:", value="meu_narrador_natural")
        voz_partida = st.selectbox(
            "Voz base de partida para a modulação:",
            options=["pm_alex", "pm_santa", "pf_dora", "narrador_classico"],
            help="A voz base fornecerá a estrutura fonética que será aproximada do seu áudio."
        )
        peso_calib = st.slider(
            "Intensidade de Calibração (Alpha):",
            min_value=0.1,
            max_value=0.6,
            value=0.35,
            step=0.05,
            help="Valores entre 0.25 e 0.40 garantem naturalidade sem perda de estabilidade fonética."
        )

    st.markdown("---")

    if audio_ref_file:
        if st.button("📝 1. Transcrever Áudio de Referência", type="secondary"):
            with st.spinner("Transcrevendo com Whisper local (CPU)..."):
                try:
                    texto_transcrito = calibrador.transcrever_audio(caminho_temp_ref)
                    st.session_state["transcricao_calib"] = texto_transcrito
                    st.success("Transcrição concluída! Revise o texto abaixo antes de prosseguir.")
                except Exception as e:
                    st.error(f"Erro na transcrição: {e}")

        # Se já tivermos transcrição na sessão (ou se o usuário quiser editar)
        transcricao_atual = st.session_state.get("transcricao_calib", "")
        if transcricao_atual:
            st.subheader("2. Revisão da Transcrição")
            texto_revisado = st.text_area(
                "Ajuste qualquer palavra, sigla ou pontuação que o Whisper tenha interpretado de forma imprecisa:",
                value=transcricao_atual,
                height=150
            )

            if st.button("🚀 3. Confirmar e Calibrar Voz", type="primary", use_container_width=True):
                with st.spinner("Calibrando matriz acústica de voz e métricas de prosódia..."):
                    try:
                        res = calibrador.calibrar(
                            caminho_audio=caminho_temp_ref,
                            transcricao_revisada=texto_revisado,
                            nome_nova_voz=nome_calibrada,
                            voz_base=voz_partida,
                            peso_ajuste=peso_calib
                        )
                        st.success(f"🎉 Voz '{nome_calibrada}' calibrada e salva com sucesso!")
                        st.json({
                            "Nome": res["nome"],
                            "Arquivo de pesos": res["arquivo_tensor"],
                            "Velocidade recomendada": f"{res['velocidade_recomendada']}x",
                            "Duração do áudio base": f"{res['metricas_audio']['duracao_total']:.1f} segundos"
                        })
                        st.info("A nova voz calibrada já está disponível para uso na aba '📖 Conversão de Livros'!")
                    except Exception as e:
                        st.error(f"Erro durante a calibração: {e}")
    else:
        st.info("Envie um arquivo de áudio acima para iniciar o processo de transcrição e calibração.")


# -------------------------------------------------------------
# ABA 3: DICIONÁRIO DE PRONÚNCIA (APRENDIZADO)
# -------------------------------------------------------------
with tab_pronuncia:
    st.subheader("🧠 Ensinar Novas Pronúncias ao Sistema")
    st.write(
        "Adicione termos técnicos, siglas ou nomes de personagens para que o sintetizador "
        "aprenda a falar exatamente como desejado. Todas as alterações são salvas permanentemente."
    )

    dicionario = PronunciationDictionary()

    c_form1, c_form2, c_btn = st.columns([1.5, 2, 1])
    with c_form1:
        novo_termo = st.text_input("Termo ou Sigla Original (ex: ETL, API, Kafka):")
    with c_form2:
        nova_pronuncia = st.text_input("Como deve ser falado (ex: E T L, A P I, Cáfca):")
    with c_btn:
        st.write("")
        st.write("")
        if st.button("➕ Aprender Termo", use_container_width=True):
            if novo_termo and nova_pronuncia:
                dicionario.aprender_termo(novo_termo, nova_pronuncia)
                st.success(f"Aprendido: '{novo_termo}' -> '{nova_pronuncia}'!")
                st.rerun()
            else:
                st.warning("Preencha ambos os campos.")

    st.markdown("---")
    st.subheader("Termos Aprendidos Cadastrados")

    termos_atuais = dicionario.listar_termos()
    col_pesquisa, _ = st.columns([2, 1])
    pesquisa = col_pesquisa.text_input("🔍 Filtrar termos cadastrados:", "")

    itens = sorted(termos_atuais.items())
    if pesquisa:
        itens = [item for item in itens if pesquisa.lower() in item[0].lower() or pesquisa.lower() in item[1].lower()]

    for t, p in itens:
        c1, c2, c3 = st.columns([2, 3, 1])
        c1.markdown(f"**`{t}`**")
        c2.write(f"🗣️ *{p}*")
        if c3.button("Remover", key=f"del_{t}"):
            dicionario.remover_termo(t)
            st.rerun()


# -------------------------------------------------------------
# ABA 3: VOZES & PRESETS (VOICE BLENDING)
# -------------------------------------------------------------
with tab_vozes:
    st.subheader("🎛️ Voice Blending: Mistura e Criação de Novas Vozes")
    st.write(
        "O sistema permite misturar as matrizes acústicas do Kokoro sem gastar mais memória nem CPU. "
        "Ajuste os percentuais abaixo para criar uma voz única."
    )

    col_sliders, col_preview = st.columns([1.5, 1])

    with col_sliders:
        p_alex = st.slider("Masculina Neutra (pm_alex %):", 0, 100, 50, step=5)
        p_santa = st.slider("Masculina Grave (pm_santa %):", 0, 100, 30, step=5)
        p_dora = st.slider("Feminina (pf_dora %):", 0, 100, 20, step=5)

        soma = p_alex + p_santa + p_dora
        if soma == 0:
            st.error("A soma dos percentuais não pode ser zero.")
        else:
            w_alex = round(p_alex / soma, 2)
            w_santa = round(p_santa / soma, 2)
            w_dora = round(p_dora / soma, 2)
            st.caption(f"Pesos normalizados: Alex ({w_alex}) | Santa ({w_santa}) | Dora ({w_dora})")

    with col_preview:
        st.subheader("Teste Imediato da Voz")
        frase_teste = st.text_area(
            "Frase de teste:",
            value="Bem-vindo ao epub2audiobook. Esta é uma demonstração da voz híbrida sintetizada localmente!"
        )

        if st.button("🔊 Gerar Áudio de Teste", use_container_width=True):
            if soma > 0:
                with st.spinner("Gerando prévia..."):
                    mix_str = f"pm_alex:{w_alex},pm_santa:{w_santa},pf_dora:{w_dora}"
                    synth_teste = AudioSynthesizer(lang_code='p', voz=mix_str)
                    out_teste = os.path.join(tempfile.gettempdir(), "preview_voz.mp3")
                    synth_teste.sintetizar_texto(frase_teste, out_teste, formato="mp3")
                    with open(out_teste, "rb") as f_prev:
                        st.audio(f_prev.read(), format="audio/mp3")
                        st.success("Prévia gerada com sucesso!")
