FROM python:3.11-slim

# Dependências de sistema para manipulação de áudio, codecs e fonemas
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    espeak-ng \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalação das dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Diretório compartilhado do sistema para cache de modelos (FHS: /var/cache/models)
# Permissões 1777 (sticky bit) estilo /tmp: qualquer usuário pode ler e escrever
ENV HF_HOME=/var/cache/models/huggingface
RUN mkdir -p /var/cache/models/huggingface && \
    chmod -R 1777 /var/cache/models

# Copia os arquivos do projeto
COPY . .

# Volumes para persistência de livros, áudios e modelos em cache
VOLUME ["/app/livros", "/app/audio", "/var/cache/models"]

ENTRYPOINT ["python3", "cli.py"]
CMD ["--help"]
