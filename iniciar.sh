#!/usr/bin/env bash
set -e

# ==============================================================================
# epub2audiobook - Instalador e Inicializador Automático Local (Linux / macOS)
# ==============================================================================

DIR_RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR_RAIZ"

echo "=========================================================="
echo "   🎙️  epub2audiobook - Inicializador Local (PT-BR)"
echo "=========================================================="

# 1. Verifica se o Python 3 está disponível
if ! command -v python3 &>/dev/null; then
    echo "❌ Erro: python3 não foi encontrado no sistema."
    echo "Instale o Python 3.10 ou superior para prosseguir."
    exit 1
fi

# 2. Cria o ambiente virtual se não existir
if [ ! -d "venv" ]; then
    echo "📦 Criando ambiente virtual Python (venv)..."
    python3 -m venv venv
fi

# 3. Ativa o ambiente virtual
source venv/bin/activate

# 4. Instala ou atualiza as dependências necessárias
echo "🔍 Verificando dependências do projeto..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# 5. Verifica dependências do sistema de áudio
if ! command -v ffmpeg &>/dev/null; then
    echo "⚠️  Aviso: 'ffmpeg' não detectado no PATH do sistema."
    echo "    Recomendado instalar ffmpeg para conversão MP3 de alta performance."
fi

# 6. Inicia a interface Web Streamlit
echo ""
echo "🚀 Iniciando a interface gráfica Web em http://localhost:8501 ..."
echo "Pressione Ctrl+C a qualquer momento para encerrar."
echo ""

python3 cli.py ui --porta 8501
