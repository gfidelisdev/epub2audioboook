# Versão com suporte a EPUB
# Segue a ordem oficial de leitura do livro (spine) e extrai o texto preservando estrutura.
import sys
import os
import re
from ebooklib import epub
from bs4 import BeautifulSoup
import warnings

# Suprime avisos irrelevantes do ebooklib
warnings.filterwarnings("ignore")

def extrair_texto_limpo(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove apenas scripts, estilos e mídias
    for tag in soup(['script', 'style', 'svg', 'img']):
        tag.decompose()

    # Pega todo o texto preservando quebras de parágrafo naturais
    linhas = []
    # Itera por elementos que tipicamente carregam texto legível
    for elem in soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'blockquote', 'li']):
        # Evita duplicar texto se for uma div pai contendo parágrafos filhos
        if elem.name == 'div' and elem.find(['p', 'div']):
            continue

        texto = elem.get_text(separator=' ', strip=True)
        if texto:
            texto = re.sub(r'\s+', ' ', texto)
            linhas.append(texto)

    # Fallback caso o EPUB não use tags semânticas estruturadas
    if not linhas:
        texto_geral = soup.get_text(separator='\n', strip=True)
        linhas = [re.sub(r'\s+', ' ', l) for l in texto_geral.split('\n') if l.strip()]

    return "\n\n".join(linhas)

def processar_epub(caminho_epub, pasta_saida="capitulos_extraidos"):
    os.makedirs(pasta_saida, exist_ok=True)
    livro = epub.read_epub(caminho_epub)
    
    print(f"Lendo livro: {livro.get_metadata('DC', 'title') or caminho_epub}")

    # Usa o spine (espinha dorsal do livro) para garantir a ordem correta de leitura
    ordem_itens = [item_id for item_id, _ in livro.spine]
    capitulos_salvos = 0

    for item_id in ordem_itens:
        item = livro.get_item_with_id(item_id)
        if not item:
            continue

        texto = extrair_texto_limpo(item.get_content())
        
        # Filtra páginas inúteis (capas, termos de licença vazios ou seções com menos de 100 caracteres)
        if len(texto) < 100:
            continue

        capitulos_salvos += 1
        nome_arquivo = os.path.join(pasta_saida, f"capitulo_{capitulos_salvos:02d}.txt")
        
        with open(nome_arquivo, "w", encoding="utf-8") as f:
            f.write(texto)

        # Exibe prévia para diagnóstico
        primeiras_palavras = texto[:80].replace("\n", " ")
        print(f"-> Salvo {nome_arquivo} ({len(texto)} caracteres): \"{primeiras_palavras}...\"")

    print(f"\nTotal extraído: {capitulos_salvos} arquivos salvos na pasta '{pasta_saida}'.")

if __name__ == "__main__":
    arquivo = sys.argv[1] if len(sys.argv) > 1 else "livros/livro.epub"
    if not os.path.exists(arquivo):
        print(f"Erro: Arquivo '{arquivo}' não encontrado.")
        sys.exit(1)
    
    processar_epub(arquivo)