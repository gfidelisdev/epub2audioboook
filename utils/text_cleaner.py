import re

try:
    from num2words import num2words
except ImportError:
    num2words = None

class TextCleanerPTBR:
    """Normalizador de texto para síntese de voz (TTS) em Português Brasileiro."""

    ABREVIACOES = {
        r'\bSr\.(?=\s|$)': 'Senhor',
        r'\bSra\.(?=\s|$)': 'Senhora',
        r'\bDr\.(?=\s|$)': 'Doutor',
        r'\bDra\.(?=\s|$)': 'Doutora',
        r'\bProf\.(?=\s|$)': 'Professor',
        r'\bProfa\.(?=\s|$)': 'Professora',
        r'\bpág\.(?=\s|$)': 'página',
        r'\bpágs\.(?=\s|$)': 'páginas',
        r'\bcap\.(?=\s|$)': 'capítulo',
        r'\bex\.(?=\s|$)': 'exemplo',
        r'\bobs\.(?=\s|$)': 'observação',
        r'\betc\.(?=\s|$)': 'etcétera',
        r'\bvs\.(?=\s|$)': 'versus',
        r'\bv\.(?=\s|$)': 'versículo',
    }

    # Mapeamento de termos e grafias de Portugal e países lusófonos (PALOP) para o Português Brasileiro (PT-BR)
    # Evita que o sintetizador produza fonemas com sotaque fechado ou termos estranhos ao ouvinte brasileiro
    LUSOFONIA_PARA_PTBR = {
        # Vocabulário e termos comuns de tecnologia e dia a dia
        r'\bequipas\b': 'equipes',
        r'\bequipa\b': 'equipe',
        r'\bficheiros\b': 'arquivos',
        r'\bficheiro\b': 'arquivo',
        r'\butilizadores\b': 'usuários',
        r'\butilizador\b': 'usuário',
        r'\becrãs\b': 'telas',
        r'\becrã\b': 'tela',
        r'\btelemóveis\b': 'celulares',
        r'\btelemóvel\b': 'celular',
        r'\bacedem\b': 'acessam',
        r'\baceder\b': 'acessar',
        r'\bconnosco\b': 'conosco',
        r'\bde facto\b': 'de fato',
        r'\bà muito tempo\b': 'há muito tempo',

        # Consoantes mudas pré-acordo / grafia europeia (adoptar, projecto, acto, etc.)
        r'\badopt(ar|ou|aram|am|ará|ariam|ado|ada|ados|adas|am-se|ando)\b': r'adot\1',
        r'\badopç(ão|ões)\b': r'adoç\1',
        r'\bproject(o|os)\b': r'projet\1',
        r'\bact(o|os)\b': r'at\1',
        r'\bactiv(o|os|a|as|idade|idades)\b': r'ativ\1',
        r'\bactual(mente)?\b': r'atual\1',
        r'\bactualizaç(ão|ões)\b': r'atualizaç\1',
        r'\bactualiz(ar|ado|ada|ados|adas|ou|am)\b': r'atualiz\1',
        r'\bafect(o|os|a|am|ou|ar|ado|ada|ados|adas)\b': r'afet\1',
        r'\bóptim(o|os|a|as)\b': r'ótim\1',
        r'\bdirecç(ão|ões)\b': r'direç\1',
        r'\bcorrecc(ão|ões)\b': r'correç\1',
        r'\binfecç(ão|ões)\b': r'infeç\1',
        r'\bdescodific(ar|ado|ada|ou|am)\b': r'decodific\1',
    }

    @classmethod
    def expandir_moeda(cls, texto: str) -> str:
        def _sub_moeda(match):
            reais = match.group(1).replace(".", "")
            centavos = match.group(2)
            if num2words:
                r_ext = num2words(int(reais), lang='pt_BR')
                c_ext = num2words(int(centavos), lang='pt_BR') if centavos and int(centavos) > 0 else ""
                moeda_str = f"{r_ext} {'real' if int(reais) == 1 else 'reais'}"
                if c_ext:
                    moeda_str += f" e {c_ext} {'centavo' if int(centavos) == 1 else 'centavos'}"
                return moeda_str
            return f"{reais} reais" + (f" e {centavos} centavos" if centavos else "")

        return re.sub(r'R\$\s*(\d+(?:\.\d{3})*),?(\d{2})?', _sub_moeda, texto)

    @classmethod
    def expandir_ordinais(cls, texto: str) -> str:
        def _sub_ordinal_m(match):
            num = int(match.group(1))
            if num2words:
                return num2words(num, to='ordinal', lang='pt_BR')
            return f"{num}º"

        def _sub_ordinal_f(match):
            num = int(match.group(1))
            if num2words:
                return num2words(num, to='ordinal', lang='pt_BR').replace("o", "a")
            return f"{num}ª"

        texto = re.sub(r'\b(\d+)º\b', _sub_ordinal_m, texto)
        texto = re.sub(r'\b(\d+)ª\b', _sub_ordinal_f, texto)
        return texto

    @classmethod
    def limpar_artefatos(cls, texto: str) -> str:
        # Remove URLs
        texto = re.sub(r'https?://\S+|www\.\S+', '', texto)
        # Remove emails
        texto = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', texto)
        # Remove notas de rodapé numéricas coladas em palavras (ex: palavra[1] ou palavra¹)
        texto = re.sub(r'\[\d+\]', '', texto)
        texto = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹⁰]', '', texto)
        # Remove marcadores de lista/bullets comuns em PDFs e documentos
        texto = re.sub(r'[\uf0b7\u2022\u25cf\u25aa\u25b6▪•►]', ' ', texto)
        # Remove asteriscos ou barras repetidas (separadores visuais comuns em livros)
        texto = re.sub(r'[\*\-_=~]{3,}', ' ', texto)
        # Normaliza aspas
        texto = texto.replace('“', '"').replace('”', '"')
        # Corrige ênclises/próclises com espaçamento quebrado típico de extração de PDF (ex: "faz -se" -> "faz-se")
        texto = re.sub(
            r'(\b\w+)\s+-\s*(se|lhe|lhes|me|te|nos|vos|o|a|os|as|lo|la|los|las|no|na|nos|nas)\b',
            r'\1-\2',
            texto,
            flags=re.IGNORECASE
        )
        # Em diálogos e quebras de oração, normaliza travessões (ou hífen isolado com espaços) para ' — '
        texto = re.sub(r'(?<=\s)[–—\-](?=\s)', ' — ', texto)
        texto = re.sub(r'[–—]', ' — ', texto)
        # Normaliza sequências de múltiplos pontos para reticências padrão
        texto = re.sub(r'\.{4,}', '...', texto)
        return texto

    @classmethod
    def normalizar(cls, texto: str) -> str:
        if not texto:
            return ""

        # Normaliza termos e grafias de Portugal/PALOP para PT-BR
        for padrao, subst in cls.LUSOFONIA_PARA_PTBR.items():
            texto = re.sub(padrao, subst, texto, flags=re.IGNORECASE)

        # Expande abreviações comuns
        for padrao, subst in cls.ABREVIACOES.items():
            texto = re.sub(padrao, subst, texto, flags=re.IGNORECASE)

        # Expande valores monetários
        texto = cls.expandir_moeda(texto)

        # Expande ordinais (1º, 2ª...)
        texto = cls.expandir_ordinais(texto)

        # Aplica dicionário de pronúncia personalizável/aprendido
        try:
            from utils.phonetic_dict import PronunciationDictionary
            dicionario = PronunciationDictionary()
            texto = dicionario.aplicar(texto)
        except Exception as e:
            # Fallback seguro caso ocorra erro ao carregar dicionário
            pass

        # Ajusta espaços múltiplos
        texto = re.sub(r'[ \t]+', ' ', texto)
        # Preserva quebras duplas de parágrafo limpas
        texto = re.sub(r'\n\s*\n+', '\n\n', texto)

        return texto.strip()
