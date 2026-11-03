# @title generate_qwen_metrics.py
"""
Análise comparativa entre redações sintéticas (geradas por IA) e naturais (referência).
Lê as redações sintéticas do Google Drive e as compara com as redações naturais em termos de:
- Diversidade Lexical (TTR)
- Complexidade Lexical (baseada em sílabas)
- Subjetividade (via modelo BERT)
"""

import os
import re
import json
import random
import statistics
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

import pandas as pd
import numpy as np
import torch
from tqdm.notebook import tqdm  # ← Utiliza barras nativas em HTML do Colab
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# --- Visualização e estatística ---
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import mannwhitneyu

# ============================================================
# 0. CONFIGURAÇÃO DO GOOGLE DRIVE
# ============================================================
try:
    from google.colab import drive
    drive.mount('/content/drive')
    print("Google Drive montado com sucesso!")
except ImportError:
    print("Ambiente não é Google Colab. Certifique-se de que o caminho do Drive esteja correto.")

# ============================================================
# 1. DEFINIÇÃO DOS CAMINHOS
# ============================================================
DRIVE_BASE = "/content/drive/MyDrive" if os.path.exists("/content/drive/MyDrive") else "."
SINTETICO_ROOT = os.path.join(DRIVE_BASE, "dataset", "TopicAlignment", "Strategy1", "synthetic_essays", "qwen_essays")
NATURAL_ROOT = os.path.join(DRIVE_BASE, "dataset", "TopicAlignment", "json_dataset", "gpt4TurboOneshot")

# Domínios (subpastas)
DOMINIOS = ['high_score', 'medium_score', 'low_score']

# Parâmetros da amostra
N_AMOSTRA = 30
SEED = 42

# Pasta para salvar resultados
RESULTADOS_DIR = os.path.join(DRIVE_BASE, "dataset", "TopicAlignment", "Strategy1", "results", "qwen_evaluations")
os.makedirs(RESULTADOS_DIR, exist_ok=True)

# ============================================================
# 2. FUNÇÕES AUXILIARES DE TEXTO
# ============================================================

def contar_silabas_pt(palavra: str) -> int:
    """Estima o número de sílabas de uma palavra em português."""
    palavra = palavra.lower().strip()
    if not palavra:
        return 0
    palavra = re.sub(r'[^a-zà-ÿ]', '', palavra)
    vogais = r'[aeiouyáéíóúâêôãõàüí]'
    nucleos = re.findall(f'{vogais}+', palavra)
    total = len(nucleos)
    return max(total, 1)

def extrair_palavras(texto: str) -> List[str]:
    """Retorna lista de palavras com 3+ caracteres."""
    if not texto or not texto.strip():
        return []
    return re.findall(r'\b[a-zA-ZÀ-ÿ]{3,}\b', texto.lower())

def diversidade_lexica(texto: str) -> float:
    """Type-Token Ratio (TTR)."""
    palavras = extrair_palavras(texto)
    if not palavras:
        return 0.0
    return len(set(palavras)) / len(palavras)

def complexidade_lexica(texto: str) -> float:
    """Índice de complexidade lexical baseado em sílabas."""
    palavras = extrair_palavras(texto)
    if not palavras:
        return 0.0

    total_silabas = 0
    palavras_4silabas = 0
    palavras_5silabas = 0

    for palavra in palavras:
        num_silabas = contar_silabas_pt(palavra)
        total_silabas += num_silabas
        if num_silabas >= 4:
            palavras_4silabas += 1
        if num_silabas >= 5:
            palavras_5silabas += 1

    prop_longas = palavras_4silabas / len(palavras)
    prop_muito_longas = palavras_5silabas / len(palavras)
    silabas_por_palavra = total_silabas / len(palavras)

    indice = (prop_longas * 0.4 +
              prop_muito_longas * 0.3 +
              min(silabas_por_palavra / 8.0, 1.0) * 0.3)
    return indice

# ============================================================
# 3. SUBJETIVIDADE COM BERT
# ============================================================

class SubjetividadeModel:
    def __init__(self, device: Optional[str] = None):
        self.device = device if device else ('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Carregando modelo de subjetividade em {self.device}...")
        self.tokenizer = AutoTokenizer.from_pretrained("cffl/bert-base-styleclassification-subjective-neutral")
        self.model = AutoModelForSequenceClassification.from_pretrained(
            "cffl/bert-base-styleclassification-subjective-neutral",
            use_safetensors=True
        ).to(self.device)
        self.model.eval()

    def predict(self, texto: str) -> float:
        inputs = self.tokenizer(texto, return_tensors="pt", truncation=True, max_length=512).to(self.device)
        with torch.no_grad():
            logits = self.model(**inputs).logits
        probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
        return float(probs[1])

# ============================================================
# 4. LEITURA DE ARQUIVOS JSON
# ============================================================

def ler_texto_natural(caminho: str) -> str:
    """Extrai o texto da redação original."""
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        if "redacao" in dados:
            campo = dados["redacao"]
            return ' '.join(campo.values()) if isinstance(campo, dict) else str(campo)
        if "comando_tematico" in dados:
            campo = dados["comando_tematico"]
            return ' '.join(campo.values()) if isinstance(campo, dict) else str(campo)
        return ""
    except Exception as e:
        return ""

def ler_texto_sintetico(caminho: str) -> str:
    """Extrai o campo 'redacao' do JSON sintético."""
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        redacao = dados.get("redacao")
        if isinstance(redacao, str):
            return redacao
        elif isinstance(redacao, dict):
            return ' '.join(redacao.values())
        return ""
    except Exception as e:
        return ""

# ============================================================
# 5. PAREAMENTO FLEXÍVEL DE ARQUIVOS
# ============================================================

def listar_pares_por_faixa(sintetico_root: str, natural_root: str, dominios: List[str]) -> Dict[str, List[Tuple[str, str]]]:
    """Busca pares de forma flexível ignorando sufixos e timestamps."""
    pares_por_dominio = defaultdict(list)

    if not os.path.isdir(natural_root) or not os.path.isdir(sintetico_root):
        return {}

    arquivos_nat = [f for f in os.listdir(natural_root) if f.lower().endswith('.json')]
    print(f"Encontrados {len(arquivos_nat)} arquivos originais em {natural_root}")

    for arq_nat in arquivos_nat:
        nome_base_nat = os.path.splitext(arq_nat)[0].strip()
        caminho_nat = os.path.join(natural_root, arq_nat)

        for dominio in dominios:
            subpasta_sint = os.path.join(sintetico_root, dominio)
            if not os.path.isdir(subpasta_sint):
                continue

            arquivos_sint = [f for f in os.listdir(subpasta_sint) if f.lower().endswith('.json')]
            encontrados = []
            for arq_s in arquivos_sint:
                nome_s_sem_ext = os.path.splitext(arq_s)[0]
                if nome_s_sem_ext.startswith(nome_base_nat):
                    encontrados.append(arq_s)

            if encontrados:
                arq_sint = encontrados[0]
                caminho_sint = os.path.join(subpasta_sint, arq_sint)
                pares_por_dominio[dominio].append((caminho_nat, caminho_sint))

    return dict(pares_por_dominio)

def amostrar_pares(pares_por_dominio: Dict[str, List], n_amostra: int = 30, seed: int = 42) -> Dict[str, List]:
    random.seed(seed)
    amostras = {}
    for dominio, pares in pares_por_dominio.items():
        amostra = random.sample(pares, n_amostra) if len(pares) > n_amostra else pares
        amostras[dominio] = amostra
        print(f"Domínio '{dominio}': {len(pares)} pares encontrados, amostra = {len(amostra)}")
    return amostras

# ============================================================
# 6. ESTATÍSTICAS E GRÁFICOS
# ============================================================

def estatisticas(valores: List[float]) -> Dict[str, float]:
    if not valores:
        return {'media': 0.0, 'desvio_padrao': 0.0, 'mediana': 0.0}
    media = statistics.mean(valores)
    desvio = statistics.stdev(valores) if len(valores) > 1 else 0.0
    mediana = statistics.median(valores)
    return {'media': media, 'desvio_padrao': desvio, 'mediana': mediana}

def gerar_graficos(dados_naturais, dados_sinteticos, dominio, output_dir):
    nat = [d for d in dados_naturais if d['dominio'] == dominio]
    sint = [d for d in dados_sinteticos if d['dominio'] == dominio]
    if not nat or not sint:
        return

    df_nat = pd.DataFrame(nat)
    df_sint = pd.DataFrame(sint)
    df_nat['tipo'] = 'Natural'
    df_sint['tipo'] = 'Sintético'
    df = pd.concat([df_nat, df_sint], ignore_index=True)

    metricas = ['ttr', 'complexidade', 'subjetividade']
    titulos = {
        'ttr': 'Diversidade Lexical (TTR)',
        'complexidade': 'Complexidade Lexical',
        'subjetividade': 'Subjetividade (BERT)'
    }

    sns.set_style("whitegrid")

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    for i, metrica in enumerate(metricas):
        ax = axes[i]
        sns.boxplot(data=df, x='tipo', y=metrica, palette='Set2', ax=ax)
        ax.set_title(f"{titulos[metrica]}\n{dominio.upper()}")
        ax.set_xlabel('')
        ax.set_ylabel(metrica.capitalize())
        sns.stripplot(data=df, x='tipo', y=metrica, color='black', alpha=0.3, ax=ax)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'boxplots_{dominio}.png'), dpi=150)
    plt.close()

    for metrica in metricas:
        plt.figure(figsize=(8, 5))
        sns.histplot(data=df, x=metrica, hue='tipo', kde=True, alpha=0.5, bins=15)
        plt.title(f"{titulos[metrica]}\n{dominio.upper()}")
        plt.xlabel(metrica.capitalize())
        plt.ylabel('Frequência')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f'hist_{dominio}_{metrica}.png'), dpi=150)
        plt.close()

    resultados_teste = {}
    for metrica in metricas:
        vals_nat = [d[metrica] for d in nat]
        vals_sint = [d[metrica] for d in sint]
        stat, p = mannwhitneyu(vals_nat, vals_sint, alternative='two-sided')
        resultados_teste[metrica] = {'statistic': stat, 'p-value': p}
        print(f"  {dominio} | {metrica}: Mann-Whitney U = {stat:.3f}, p = {p:.4f}")

    return resultados_teste

# ============================================================
# 7. MAIN
# ============================================================

def main():
    print("\n=== Verificando diretórios ===")
    print(f"SINTETICO_ROOT: {SINTETICO_ROOT}")
    print(f"NATURAL_ROOT: {NATURAL_ROOT}")

    if not os.path.isdir(SINTETICO_ROOT) or not os.path.isdir(NATURAL_ROOT):
        print("❌ ERRO: Verifique se os diretórios no Drive existem.")
        return

    print("\n=== 1. Pareando documentos ===")
    todos_pares = listar_pares_por_faixa(SINTETICO_ROOT, NATURAL_ROOT, DOMINIOS)
    print("Resumo:", {k: len(v) for k, v in todos_pares.items()})
    if not todos_pares:
        print("❌ Nenhum par encontrado.")
        return

    amostras = amostrar_pares(todos_pares, N_AMOSTRA, SEED)

    print("\n=== 2. Carregando modelo de subjetividade ===")
    subj_model = SubjetividadeModel()

    dados_naturais = []
    dados_sinteticos = []

    print("\n=== 3. Calculando métricas ===")
    # Visualização limpa com tqdm.notebook sem quebra de linhas
    for dominio, pares in tqdm(amostras.items(), desc="Domínios"):
        for nat_path, sint_path in tqdm(pares, desc=f"Lendo {dominio.upper()}", leave=False):
            texto_nat = ler_texto_natural(nat_path)
            texto_sint = ler_texto_sintetico(sint_path)

            if not texto_nat or not texto_sint:
                continue

            dados_naturais.append({
                'dominio': dominio,
                'arquivo': os.path.basename(nat_path),
                'ttr': diversidade_lexica(texto_nat),
                'complexidade': complexidade_lexica(texto_nat),
                'subjetividade': subj_model.predict(texto_nat)
            })
            dados_sinteticos.append({
                'dominio': dominio,
                'arquivo': os.path.basename(sint_path),
                'ttr': diversidade_lexica(texto_sint),
                'complexidade': complexidade_lexica(texto_sint),
                'subjetividade': subj_model.predict(texto_sint)
            })

    print("\n=== 4. Estatísticas descritivas ===")
    resultados = {}
    for dominio in DOMINIOS:
        nat_dom = [d for d in dados_naturais if d['dominio'] == dominio]
        sint_dom = [d for d in dados_sinteticos if d['dominio'] == dominio]
        if not nat_dom or not sint_dom:
            continue

        resultados[dominio] = {
            'natural': {
                'ttr': estatisticas([d['ttr'] for d in nat_dom]),
                'complexidade': estatisticas([d['complexidade'] for d in nat_dom]),
                'subjetividade': estatisticas([d['subjetividade'] for d in nat_dom]),
                'n_amostras': len(nat_dom)
            },
            'sintetico': {
                'ttr': estatisticas([d['ttr'] for d in sint_dom]),
                'complexidade': estatisticas([d['complexidade'] for d in sint_dom]),
                'subjetividade': estatisticas([d['subjetividade'] for d in sint_dom]),
                'n_amostras': len(sint_dom)
            }
        }

    with open(os.path.join(RESULTADOS_DIR, "resultados_metricas.json"), 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print("\n=== 5. Gerando CSV para avaliação humana ===")
    linhas = []
    for dominio, pares in amostras.items():
        for nat_path, sint_path in pares:
            nome_base = os.path.basename(nat_path)
            linhas.append({
                'dominio': dominio, 'arquivo': nome_base, 'tipo': 'natural',
                'texto': ler_texto_natural(nat_path)[:1000],
                'fluencia': '', 'coerencia': '', 'realismo': '', 'especificidade': ''
            })
            linhas.append({
                'dominio': dominio, 'arquivo': nome_base, 'tipo': 'sintetico',
                'texto': ler_texto_sintetico(sint_path)[:1000],
                'fluencia': '', 'coerencia': '', 'realismo': '', 'especificidade': ''
            })
    
    df_csv = pd.DataFrame(linhas)
    csv_path = os.path.join(RESULTADOS_DIR, "avaliacao_humana.csv")
    df_csv.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"CSV salvo em: {csv_path}")

    print("\n=== 6. Gerando gráficos e testes estatísticos ===")
    resultados_teste = {}
    for dominio in DOMINIOS:
        testes = gerar_graficos(dados_naturais, dados_sinteticos, dominio, RESULTADOS_DIR)
        if testes:
            resultados_teste[dominio] = testes

    with open(os.path.join(RESULTADOS_DIR, "testes_estatisticos.json"), 'w', encoding='utf-8') as f:
        json.dump(resultados_teste, f, indent=2, ensure_ascii=False)

    print(f"\n🎉 Análise concluída! Resultados salvos em: {RESULTADOS_DIR}")

if __name__ == "__main__":
    main()