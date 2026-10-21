import os
import json
import re
import time
import requests
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# ============================================================
# CONFIGURAÇÕES - ALTERE AQUI SE NECESSÁRIO
# ============================================================

# Carrega as variáveis do arquivo .env
DIRETORIO_PROJETO = Path(__file__).resolve().parents[3]
load_dotenv(DIRETORIO_PROJETO / ".env")

# Carrega a chave de API do Mistral
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    raise ValueError("A variável MISTRAL_API_KEY não foi encontrada no arquivo .env!")
MODELO = "open-mistral-nemo"                         # mesmo modelo da geração

# Caminho do arquivo de configuração em JSON
ARQUIVO_CONFIG = DIRETORIO_PROJETO / "config.json"

# Carrega as configurações
with ARQUIVO_CONFIG.open("r", encoding="utf-8") as arq:
    CONFIG = json.load(arq)

PASTA_BASE_ENTRADA = (DIRETORIO_PROJETO / CONFIG["pasta_base_entrada"]).resolve()
PASTA_BASE_SAIDA = (DIRETORIO_PROJETO / CONFIG["pasta_base_saida"]).resolve()

# PASTA_BASE_ENTRADA = r"C:\Users\AdminUser\Documents\IC\redacoesSinteticas"  # pasta que contém as subpastas baixa, media, alta
# PASTA_BASE_SAIDA   = r"C:\Users\AdminUser\Documents\IC\redacoesAnalisadas"   # onde serão criadas as pastas de saída


DELAY_SEGUNDOS = 0.5     # pausa entre análises de frases

# Mapeamento das subpastas de entrada para os nomes das pastas de saída
'''
SUBPASTAS = {
    "baixa": "Analise_baixas",
    "media": "Analise_medias",
    "alta":  "Analise_altas"
}
'''

# ============================================================
# Função para dividir redação em frases (mantendo pontuação)
# ============================================================
def dividir_em_frases(texto):
    """
    Divide um texto em frases usando padrão simples: . ! ? seguidos de espaço ou fim de string.
    Preserva abreviações como "Dr.", "Sr.", "etc." - essa regex básica já resolve.
    """
    texto = re.sub(r'\n+', ' ', texto)
    frases = re.split(r'(?<=[.!?])\s+(?=[A-Z])', texto)
    frases = [f.strip() for f in frases if f.strip()]
    return frases

# ============================================================
# Chamada à API Mistral para analisar uma frase
# ============================================================
def analisar_frase(frase, comando_tematico, tentativa=1):
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""Você é um especialista em análise de coerência textual. 
Tema central da redação: "{comando_tematico}"

Considere a seguinte frase extraída da redação:
"{frase}"

Responda APENAS com um objeto JSON válido, sem texto adicional, seguindo exatamente este formato:
{{"link": true/false, "evento": "uma breve explicação de como a frase se conecta ou não ao tema"}}

Regras:
- link = true se a frase mencionar direta ou indiretamente algo relacionado ao tema proposto.
- link = false se a frase for totalmente desconectada do tema.
- O evento deve descrever a ação, situação ou processo que vincula a frase ao tema.

Faça a análise com rigor, mas sem inventar conexões inexistentes.
"""
    
    payload = {
        "model": MODELO,
        "messages": [
            {"role": "system", "content": "Você é um assistente que responde exclusivamente com JSON válido."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "top_p": 0.9,
        "max_tokens": 300
    }
    
    try:
        resposta = requests.post(url, json=payload, headers=headers, timeout=30)
        if resposta.status_code == 200:
            dados = resposta.json()
            conteudo = dados["choices"][0]["message"]["content"].strip()
            json_match = re.search(r'\{.*\}', conteudo, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"link": False, "evento": f"Erro de parsing: {conteudo[:100]}"}
        else:
            if tentativa <= 3:
                time.sleep(2)
                return analisar_frase(frase, comando_tematico, tentativa+1)
            return {"link": False, "evento": f"Erro HTTP {resposta.status_code}"}
    except Exception as e:
        if tentativa <= 3:
            time.sleep(2)
            return analisar_frase(frase, comando_tematico, tentativa+1)
        return {"link": False, "evento": f"Exceção: {str(e)}"}

# ============================================================
# Processar um único arquivo de redação (JSON)
# ============================================================
def processar_arquivo(caminho_json):
    with open(caminho_json, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    
    redacao = dados.get("redacao", "")
    comando = dados.get("comando", "")
    
    if not redacao or not comando:
        print(f"  ⚠️ Arquivo {os.path.basename(caminho_json)} sem redação ou comando. Pulando.")
        return None
    
    frases = dividir_em_frases(redacao)
    print(f"  📄 {len(frases)} frases detectadas.")
    
    analise_frases = []
    for idx, frase in enumerate(frases, 1):
        print(f"    Analisando frase {idx}/{len(frases)}...")
        resultado = analisar_frase(frase, comando)
        analise_frases.append({
            "frase": frase,
            "link": resultado.get("link", False),
            "evento": resultado.get("evento", "")
        })
        time.sleep(DELAY_SEGUNDOS)
    
    dados_analisados = {
        "original_arquivo": os.path.basename(caminho_json),
        "comando": comando,
        "redacao": redacao,
        "analise_frases": analise_frases,
        "data_analise": datetime.now().isoformat()
    }
    return dados_analisados

# ============================================================
# Função principal: processa cada subpasta (baixa, media, alta)
# ============================================================
def main():
    # Verifica se a pasta base de entrada existe
    if not PASTA_BASE_ENTRADA.is_dir():
        print(f"❌ Pasta base de entrada não encontrada: {PASTA_BASE_ENTRADA}")
        return

    # Percorre as subpastas de entrada automaticamente
    for pasta_entrada in sorted(PASTA_BASE_ENTRADA.iterdir()):

        # Ignora arquivos e considera apenas diretórios
        if not pasta_entrada.is_dir():
            continue

        # A saída terá o mesmo nome da pasta de entrada
        caminho_entrada = pasta_entrada
        caminho_saida = PASTA_BASE_SAIDA / pasta_entrada.name

        # Lista os arquivos JSON da subpasta
        arquivos = sorted(pasta_entrada.glob("*.json"))

        if not arquivos:
            print(f"⚠️ Nenhum arquivo .json encontrado em {caminho_entrada}")
            continue

        # Cria a pasta de saída correspondente
        caminho_saida.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"📁 Processando pasta: {pasta_entrada.name.upper()} ({len(arquivos)} arquivos)")
        print(f"   Entrada: {caminho_entrada}")
        print(f"   Saída:   {caminho_saida}")
        print(f"{'='*60}\n")

        for idx, arquivo in enumerate(arquivos, 1):
            print(f"[{idx}/{len(arquivos)}] Analisando: {arquivo.name}")

            resultado = processar_arquivo(arquivo)

            if resultado:
                nome_saida_arq = f"{arquivo.stem}_analise.json"
                caminho_saida_arq = caminho_saida / nome_saida_arq

                with caminho_saida_arq.open("w", encoding="utf-8") as f:
                    json.dump(resultado, f, ensure_ascii=False, indent=2)

                print(f"  ✅ Salvo em: {caminho_saida_arq}\n")
            else:
                print("  ❌ Falha na análise.\n")

    print("\n🎉 Análise concluída para todas as pastas!")

if __name__ == "__main__":
    main()