# epub2audiobook - Contexto de Domínio

Conversor local de livros digitais (EPUB, PDF, TXT) em audiolivros falados em Português Brasileiro (PT-BR) com síntese neural leve e prosódia expressiva.

## Language

**Livro Fonte**:
Arquivo original fornecido pelo usuário para conversão (.epub, .pdf, .mobi, .txt, .md).
_Avoid_: Documento bruto, input file

**Capítulo**:
Unidade lógica de conteúdo extraída do Livro Fonte para processamento e narração sequencial independente.
_Avoid_: Arquivo de texto, pedaço, slice

**Segmento Prosódico**:
Cláusula, frase ou oração delimitada por pontuação e travessões com parâmetros próprios de pausa, ritmo e entonação.
_Avoid_: Frase crua, linha, chunk

**Dicionário de Pronúncia**:
Repositório persistente de termos técnicos, estrangeirismos e siglas com sua representação falada fonetizada para aprendizado contínuo.
_Avoid_: Tabela de substituição, blacklist, whitelist

**Mix de Vozes (Voice Blend)**:
Vetor acústico gerado pela combinação ponderada de múltiplos perfis de voz nativos do sintetizador para criar novas personalidades vocais.
_Avoid_: Voz clonada, voz sintética estática

**Sintetizador**:
Mecanismo neural local de inferência TTS que converte Segmentos Prosódicos em forma de onda de áudio.
_Avoid_: Motor de voz, backend de fala

**Audiobook Gerado**:
Conjunto de faixas de áudio (.mp3) finalizadas, normalizadas e organizadas por capítulos com metadados.
_Avoid_: Áudios soltos, output

**Áudio de Referência**:
Gravação de fala fornecida pelo usuário acompanhada de transcrição revisada para guiar a calibração do sintetizador.
_Avoid_: Amostra bruta, dataset de treino

**Calibrador Vocal**:
Módulo que otimiza o vetor de embedding de voz, cadência prosódica e pronúncias fonéticas a partir de um Áudio de Referência validado pelo usuário.
_Avoid_: Fine-tuner pesado, re-treinador de modelo
