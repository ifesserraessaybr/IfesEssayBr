# -*- coding: utf-8 -*-
"""
ANÁLISE DE COERÊNCIA FRASE A FRASE – QWEN (LOCAL)
Lê redações sintéticas (JSON) das pastas baixo, medio, alto, excelente,
analisa cada frase com Qwen 7B em 4-bit e salva JSONs com link/evento.
Versão para Google Colab com montagem do Drive.
"""


!pip install unsloth

# ------------------------------------------------------------
# 1. IMPORTS E CONFIGURAÇÕES
# ------------------------------------------------------------
from google.colab import drive, userdata
import os
import re
import gc
import time
import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from datetime import datetime
from tqdm import tqdm

# ------------------------------------------------------------
# 2. MONTAR DRIVE (tratando erro de já montado)
# ------------------------------------------------------------
try:
    drive.mount('/content/drive')
except ValueError:
    print("Drive já montado. Prosseguindo...")

# Pega o token do Hugging Face (crie um secret chamado HF_TOKEN)
HF_TOKEN = userdata.get('HF_TOKEN')
if not HF_TOKEN:
    raise ValueError("❌ Token HF não encontrado. Crie um secret 'HF_TOKEN' no Colab.")

# Verifica GPU
if not torch.cuda.is_available():
    raise RuntimeError("❌ GPU não detectada! Ative em: Ambiente de execução > Alterar tipo.")

print(f"✅ GPU: {torch.cuda.get_device_name(0)}")

# ------------------------------------------------------------
# 3. CONFIGURAÇÃO DO MODELO (Qwen 7B – cabe na T4)
# ------------------------------------------------------------
MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"   # ou 14B se tiver mais memória (mas 7B é mais seguro)

print("Carregando tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True, token=HF_TOKEN)
tokenizer.pad_token = tokenizer.eos_token

# Configuração 4-bit com disable_exllama para evitar erro de device_map misto
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    disable_exllama=True,   # ← essencial para evitar o ValueError
)

print("Carregando modelo (4-bit)...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True,
    token=HF_TOKEN,
)
model.eval()
print(f"✅ Modelo {MODEL_NAME} carregado!")

# ------------------------------------------------------------
# 4. FUNÇÕES AUXILIARES
# ------------------------------------------------------------
def dividir_em_frases(texto):
    """Divide texto em frases usando pontuação final."""
    texto = re.sub(r'\n+', ' ', texto)
    frases = re.split(r'(?<=[.!?])\s+(?=[A-Z])', texto)
    frases = [f.strip() for f in frases if f.strip()]
    return frases

def analisar_frase_qwen(frase, comando, tentativa=1):
    """
    Envia a frase para o Qwen e pede classificação JSON.
    Retorna {'link': bool, 'evento': str}
    """
    prompt = f"""Você é um especialista em análise de coerência textual.
Tema central da redação: "{comando}"

Considere a seguinte frase extraída da redação:
"{frase}"

Responda APENAS com um objeto JSON válido, sem texto adicional, seguindo exatamente este formato:
{{"link": true/false, "evento": "uma breve explicação de como a frase se conecta ou não ao tema"}}

Regras:
- link = true se a frase mencionar direta ou indiretamente algo relacionado ao tema.
- link = false se for totalmente desconectada.
- O evento deve descrever a ação, situação ou processo que vincula a frase ao tema.
Faça a análise com rigor, sem inventar conexões."""

    messages = [{"role": "user", "content": prompt}]
    full_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(full_prompt, return_tensors="pt", truncation=True, max_length=4096).to("cuda")

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=300,
            temperature=0.2,
            do_sample=True,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    generated = outputs[0][inputs["input_ids"].shape[1]:]
    resposta = tokenizer.decode(generated, skip_special_tokens=True).strip()

    # Tenta extrair JSON
    try:
        json_match = re.search(r'\{.*\}', resposta, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            return {"link": False, "evento": f"Erro de parsing: {resposta[:100]}"}
    except Exception as e:
        if tentativa < 3:
            time.sleep(1)
            return analisar_frase_qwen(frase, comando, tentativa+1)
        return {"link": False, "evento": f"Exceção: {str(e)}"}

def processar_arquivo(caminho_json, pasta_saida):
    """Processa um único arquivo JSON de redação sintética."""
    with open(caminho_json, 'r', encoding='utf-8') as f:
        dados = json.load(f)

    redacao = dados.get("redacao", "")
    comando = dados.get("comando", "")

    if not redacao or not comando:
        print(f"  ⚠️ Arquivo {os.path.basename(caminho_json)} sem redação ou comando. Pulando.")
        return

    frases = dividir_em_frases(redacao)
    print(f"  📄 {len(frases)} frases detectadas.")

    analise_frases = []
    for idx, frase in enumerate(frases, 1):
        print(f"    Analisando frase {idx}/{len(frases)}...", end=" ")
        resultado = analisar_frase_qwen(frase, comando)
        analise_frases.append({
            "frase": frase,
            "link": resultado.get("link", False),
            "evento": resultado.get("evento", "")
        })
        print("OK")
        time.sleep(0.2)  # pequena pausa para não sobrecarregar

    dados_analisados = {
        "original_arquivo": os.path.basename(caminho_json),
        "comando": comando,
        "redacao": redacao,
        "analise_frases": analise_frases,
        "data_analise": datetime.now().isoformat()
    }

    nome_saida = os.path.basename(caminho_json).replace('.json', '_analise.json')
    caminho_saida = os.path.join(pasta_saida, nome_saida)
    with open(caminho_saida, 'w', encoding='utf-8') as f:
        json.dump(dados_analisados, f, ensure_ascii=False, indent=2)

    print(f"  ✅ Salvo em: {caminho_saida}")

# ------------------------------------------------------------
# 5. CONFIGURAÇÃO DOS CAMINHOS (AJUSTE AQUI)
# ------------------------------------------------------------
# Altere para o caminho correto dentro do seu Drive
DRIVE_BASE = "/content/drive/MyDrive/IC_mistral_qwen"

# Pasta onde estão as redações sintéticas (com subpastas: baixo, medio, alto, excelente)
PASTA_ENTRADA = os.path.join(DRIVE_BASE, "redacoes_sinteticas/redacoesSinteticas_variadas_qwen")
# Se a estrutura for diferente (ex: redacoes_sinteticas/redacoesSinteticas_variadas),
# ajuste a linha acima.

# Pasta onde serão salvos os JSONs de análise
PASTA_SAIDA = os.path.join(DRIVE_BASE, "analises_coerencia_qwen")

# Mapeamento dos níveis (subpastas de entrada) para os nomes de saída
NIVEIS = {
    "baixo": "Analise_baixo",
    "medio": "Analise_medio",
    "alto": "Analise_alto",
}

# ------------------------------------------------------------
# 6. PROCESSAMENTO PRINCIPAL
# ------------------------------------------------------------
def main():
    # Verifica se a pasta de entrada existe
    if not os.path.isdir(PASTA_ENTRADA):
        print(f"❌ Pasta de entrada não encontrada: {PASTA_ENTRADA}")
        print("Verifique o caminho e a estrutura de pastas no seu Drive.")
        return

    # Processa cada nível
    for nivel_entrada, nome_saida in NIVEIS.items():
        caminho_entrada = os.path.join(PASTA_ENTRADA, nivel_entrada)
        if not os.path.isdir(caminho_entrada):
            print(f"⚠️ Subpasta '{nivel_entrada}' não encontrada. Pulando...")
            continue

        caminho_saida = os.path.join(PASTA_SAIDA, nome_saida)
        os.makedirs(caminho_saida, exist_ok=True)

        arquivos = [f for f in os.listdir(caminho_entrada) if f.endswith('.json')]
        if not arquivos:
            print(f"⚠️ Nenhum JSON em {caminho_entrada}")
            continue

        print(f"\n{'='*60}")
        print(f"📁 Nível: {nivel_entrada.upper()} ({len(arquivos)} arquivos)")
        print(f"   Entrada: {caminho_entrada}")
        print(f"   Saída:   {caminho_saida}")
        print(f"{'='*60}\n")

        for idx, arquivo in enumerate(arquivos, 1):
            print(f"[{idx}/{len(arquivos)}] Analisando: {arquivo}")
            caminho_json = os.path.join(caminho_entrada, arquivo)
            try:
                processar_arquivo(caminho_json, caminho_saida)
            except Exception as e:
                print(f"  ❌ Erro ao processar {arquivo}: {e}")
            # Libera memória após cada arquivo
            gc.collect()
            torch.cuda.empty_cache()
            print()

    print("\n🎉 Análise de coerência concluída para todos os níveis!")

if __name__ == "__main__":
    main()