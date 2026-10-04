# -*- coding: utf-8 -*-
"""
Análise comparativa entre redações sintéticas (geradas por IA) e naturais (referência).
Adaptado para ler as redações sintéticas do Google Drive no caminho:
    IC_mistral_qwen/redacoesSinteticas

As redações naturais (GPT-4 Turbo One-shot) devem estar em uma pasta local ou também
no Drive (ajuste NATURAL_ROOT conforme necessário).
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
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForSequenceClassification



# --- Visualização e estatística ---
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import mannwhitneyu
from syllable import word2syllables

# ============================================================
# 0. CONFIGURAÇÃO DO GOOGLE DRIVE (para Colab ou Jupyter)
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
# Caminho base onde estão as redações sintéticas no Drive
DRIVE_BASE = "/content/drive/MyDrive" if os.path.exists("/content/drive/MyDrive") else "."
SINTETICO_ROOT = os.path.join(DRIVE_BASE, "IC_mistral_qwen", "redacoesSinteticas")

# Caminho das redações naturais (ajuste conforme sua estrutura)
# Exemplo: se estiverem no Drive, use o mesmo padrão:
# NATURAL_ROOT = os.path.join(DRIVE_BASE, "IC_mistral_qwen", "gpt4TurboOneshot")
# Se estiverem localmente, use o caminho absoluto.
NATURAL_ROOT = os.path.join(DRIVE_BASE, "IC", "gpt4TurboOneshot")


# Domínios (subpastas dentro de SINTETICO_ROOT)
DOMINIOS = ['alta', 'media', 'baixa']

# Parâmetros da amostra
N_AMOSTRA = 30
SEED = 42

# Pasta para salvar resultados (criada localmente)
RESULTADOS_DIR = os.path.join(DRIVE_BASE, "IC_mistral_qwen", "resultados_analise_qwen")

os.makedirs(RESULTADOS_DIR, exist_ok=True)

# ============================================================
# 2. FUNÇÕES AUXILIARES DE TEXTO (inalteradas)
# ============================================================

def extrair_palavras(texto: str) -> List[str]:
    """Retorna lista de palavras com 3+ caracteres (alfabéticos + acentos)."""
    if not texto or not texto.strip():
        return []
    return re.findall(r'\b[a-zA-ZÀ-ÿ]{3,}\b', texto.lower())

def diversidade_lexica(texto: str) -> float:
    """Type-Token Ratio (TTR) – diversidade lexical."""
    palavras = extrair_palavras(texto)
    if len(palavras) == 0:
        return 0.0
    return len(set(palavras)) / len(palavras)

def complexidade_lexica(texto: str) -> float:
    """
    Índice de complexidade lexical baseado em sílabas.
    Retorna valor entre 0 e 1.
    """
    palavras = extrair_palavras(texto)
    if not palavras:
        return 0.0

    total_silabas = 0
    palavras_4silabas = 0
    palavras_5silabas = 0

    for palavra in palavras:
        try:
            silabas = word2syllables(palavra)
            num_silabas = len(silabas)
            total_silabas += num_silabas
            if num_silabas >= 4:
                palavras_4silabas += 1
            if num_silabas >= 5:
                palavras_5silabas += 1
        except Exception:
            continue

    if len(palavras) == 0:
        return 0.0

    prop_longas = palavras_4silabas / len(palavras)
    prop_muito_longas = palavras_5silabas / len(palavras)
    silabas_por_palavra = total_silabas / len(palavras)

    indice = (prop_longas * 0.4 +
              prop_muito_longas * 0.3 +
              min(silabas_por_palavra / 8.0, 1.0) * 0.3)
    return indice

# ============================================================
# 3. SUBJETIVIDADE COM BERT (inalterado)
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
# 4. LEITURA DE ARQUIVOS JSON (inalterada)
# ============================================================

def ler_texto_natural(caminho: str) -> str:
    """Extrai o texto da redação original (campo 'redacao' – dicionário de frases)."""
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        if "redacao" in dados:
            campo = dados["redacao"]
            if isinstance(campo, dict):
                return ' '.join(campo.values())
            elif isinstance(campo, str):
                return campo
        if "comando_tematico" in dados:
            campo = dados["comando_tematico"]
            if isinstance(campo, dict):
                return ' '.join(campo.values())
            elif isinstance(campo, str):
                return campo
        return ""
    except Exception as e:
        print(f"Erro ao ler natural {caminho}: {e}")
        return ""

def ler_texto_sintetico(caminho: str) -> str:
    """Extrai o campo 'redacao' do JSON sintético (string)."""
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        redacao = dados.get("redacao")
        if isinstance(redacao, str):
            return redacao
        elif isinstance(redacao, dict):
            return ' '.join(redacao.values())
        else:
            return ""
    except Exception as e:
        print(f"Erro ao ler sintético {caminho}: {e}")
        return ""

# ============================================================
# 5. PARCAMENTO (ajustado para usar SINTETICO_ROOT)
# ============================================================

def listar_pares_por_faixa(sintetico_root: str, natural_root: str, dominios: List[str]) -> Dict[str, List[Tuple[str, str]]]:
    """
    Para cada arquivo original em natural_root, procura o correspondente sintético
    em sintetico_root/dominio/ com mesmo nome base.
    Retorna dicionário {dominio: [(nat_path, sint_path), ...]}
    """
    pares_por_dominio = defaultdict(list)

    if not os.path.isdir(natural_root):
        print(f"Erro: pasta natural não encontrada: {natural_root}")
        return {}

    if not os.path.isdir(sintetico_root):
        print(f"Erro: pasta sintética não encontrada: {sintetico_root}")
        return {}

    arquivos_nat = [f for f in os.listdir(natural_root) if f.lower().endswith('.json')]
    print(f"Encontrados {len(arquivos_nat)} arquivos originais em {natural_root}")

    for arq_nat in arquivos_nat:
        nome_base = os.path.splitext(arq_nat)[0]
        caminho_nat = os.path.join(natural_root, arq_nat)

        for dominio in dominios:
            subpasta_sint = os.path.join(sintetico_root, dominio)
            if not os.path.isdir(subpasta_sint):
                continue

            prefixo = f"{nome_base}_{dominio}"
            encontrados = [f for f in os.listdir(subpasta_sint) if f.startswith(prefixo) and f.endswith('.json')]
            if encontrados:
                arq_sint = encontrados[0]
                caminho_sint = os.path.join(subpasta_sint, arq_sint)
                pares_por_dominio[dominio].append((caminho_nat, caminho_sint))

    return dict(pares_por_dominio)

def amostrar_pares(pares_por_dominio: Dict[str, List], n_amostra: int = 30, seed: int = 42) -> Dict[str, List]:
    random.seed(seed)
    amostras = {}
    for dominio, pares in pares_por_dominio.items():
        if len(pares) > n_amostra:
            amostra = random.sample(pares, n_amostra)
        else:
            amostra = pares
        amostras[dominio] = amostra
        print(f"Domínio '{dominio}': {len(pares)} pares encontrados, amostra = {len(amostra)}")
    return amostras

# ============================================================
# 6. ESTATÍSTICAS E GRÁFICOS (inalterados)
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
        print(f"Domínio {dominio} sem dados para gráficos.")
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
    plt.rcParams['figure.figsize'] = (10, 6)

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    for i, metrica in enumerate(metricas):
        ax = axes[i]
        sns.boxplot(data=df, x='tipo', y=metrica, palette='Set2', ax=ax)
        ax.set_title(f'{titulos[metrica]} - {dominio.upper()}')
        ax.set_xlabel('')
        ax.set_ylabel(metrica.capitalize())
        sns.stripplot(data=df, x='tipo', y=metrica, color='black', alpha=0.3, ax=ax)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'boxplots_{dominio}.png'), dpi=150)
    plt.close()

    for metrica in metricas:
        plt.figure(figsize=(8, 5))
        sns.histplot(data=df, x=metrica, hue='tipo', kde=True, alpha=0.5, bins=15)
        plt.title(f'{titulos[metrica]} - {dominio.upper()}')
        plt.xlabel(metrica.capitalize())
        plt.ylabel('Frequência')
        plt.legend(title='Tipo')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f'hist_{dominio}_{metrica}.png'), dpi=150)
        plt.close()

    resultados_teste = {}
    for metrica in metricas:
        vals_nat = [d[metrica] for d in nat]
        vals_sint = [d[metrica] for d in sint]
        stat, p = mannwhitneyu(vals_nat, vals_sint, alternative='two-sided')
        resultados_teste[metrica] = {'statistic': stat, 'p-value': p}
        print(f"  {dominio} - {metrica}: Mann-Whitney U = {stat:.3f}, p = {p:.4f}")

    return resultados_teste

# ============================================================
# 7. MAIN (com verificação de diretórios)
# ============================================================

def main():
    print("\n=== Verificando diretórios ===")
    print(f"SINTETICO_ROOT: {SINTETICO_ROOT}")
    print(f"NATURAL_ROOT: {NATURAL_ROOT}")

    if not os.path.isdir(SINTETICO_ROOT):
        print(f"ERRO: O diretório das redações sintéticas não foi encontrado: {SINTETICO_ROOT}")
        print("Verifique se o Google Drive está montado e o caminho está correto.")
        return

    if not os.path.isdir(NATURAL_ROOT):
        print(f"ERRO: O diretório das redações naturais não foi encontrado: {NATURAL_ROOT}")
        return

    print("\n=== 1. Pareando documentos ===")
    todos_pares = listar_pares_por_faixa(SINTETICO_ROOT, NATURAL_ROOT, DOMINIOS)
    print("Resumo:", {k: len(v) for k, v in todos_pares.items()})
    if not todos_pares:
        print("Nenhum par encontrado. Verifique os nomes dos arquivos.")
        return

    amostras = amostrar_pares(todos_pares, N_AMOSTRA, SEED)

    print("\n=== 2. Carregando modelo de subjetividade ===")
    subj_model = SubjetividadeModel()

    dados_naturais = []
    dados_sinteticos = []

    print("\n=== 3. Calculando métricas ===")
    for dominio, pares in tqdm(amostras.items(), desc="Dominios"):
        for nat_path, sint_path in tqdm(pares, desc=f"  {dominio}", leave=False):
            texto_nat = ler_texto_natural(nat_path)
            texto_sint = ler_texto_sintetico(sint_path)

            if not texto_nat or not texto_sint:
                print(f"  Texto vazio em {nat_path} ou {sint_path} – ignorando")
                continue

            ttr_nat = diversidade_lexica(texto_nat)
            ttr_sint = diversidade_lexica(texto_sint)
            compl_nat = complexidade_lexica(texto_nat)
            compl_sint = complexidade_lexica(texto_sint)
            subj_nat = subj_model.predict(texto_nat)
            subj_sint = subj_model.predict(texto_sint)

            dados_naturais.append({
                'dominio': dominio,
                'arquivo': os.path.basename(nat_path),
                'ttr': ttr_nat,
                'complexidade': compl_nat,
                'subjetividade': subj_nat
            })
            dados_sinteticos.append({
                'dominio': dominio,
                'arquivo': os.path.basename(sint_path),
                'ttr': ttr_sint,
                'complexidade': compl_sint,
                'subjetividade': subj_sint
            })

    print("\n=== 4. Estatísticas descritivas ===")
    resultados = {}
    for dominio in DOMINIOS:
        nat_dom = [d for d in dados_naturais if d['dominio'] == dominio]
        sint_dom = [d for d in dados_sinteticos if d['dominio'] == dominio]
        if not nat_dom or not sint_dom:
            print(f"  Domínio {dominio} sem dados.")
            continue

        estat_ttr_nat = estatisticas([d['ttr'] for d in nat_dom])
        estat_ttr_sint = estatisticas([d['ttr'] for d in sint_dom])
        estat_compl_nat = estatisticas([d['complexidade'] for d in nat_dom])
        estat_compl_sint = estatisticas([d['complexidade'] for d in sint_dom])
        estat_subj_nat = estatisticas([d['subjetividade'] for d in nat_dom])
        estat_subj_sint = estatisticas([d['subjetividade'] for d in sint_dom])

        resultados[dominio] = {
            'natural': {
                'ttr': estat_ttr_nat,
                'complexidade': estat_compl_nat,
                'subjetividade': estat_subj_nat,
                'n_amostras': len(nat_dom)
            },
            'sintetico': {
                'ttr': estat_ttr_sint,
                'complexidade': estat_compl_sint,
                'subjetividade': estat_subj_sint,
                'n_amostras': len(sint_dom)
            }
        }
        print(f"\n--- {dominio.upper()} ---")
        print(f"  Natural: TTR={estat_ttr_nat['media']:.3f}±{estat_ttr_nat['desvio_padrao']:.3f} | Compl={estat_compl_nat['media']:.3f}±{estat_compl_nat['desvio_padrao']:.3f} | Subj={estat_subj_nat['media']:.3f}±{estat_subj_nat['desvio_padrao']:.3f}")
        print(f"  Sintético: TTR={estat_ttr_sint['media']:.3f}±{estat_ttr_sint['desvio_padrao']:.3f} | Compl={estat_compl_sint['media']:.3f}±{estat_compl_sint['desvio_padrao']:.3f} | Subj={estat_subj_sint['media']:.3f}±{estat_subj_sint['desvio_padrao']:.3f}")

    with open(os.path.join(RESULTADOS_DIR, "resultados_metricas.json"), 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print("\n=== 5. Gerando CSV para avaliação humana ===")
    linhas = []
    for dominio, pares in amostras.items():
        for nat_path, sint_path in pares:
            nome_base = os.path.basename(nat_path)
            texto_nat = ler_texto_natural(nat_path)[:1000]
            texto_sint = ler_texto_sintetico(sint_path)[:1000]
            linhas.append({
                'dominio': dominio,
                'arquivo': nome_base,
                'tipo': 'natural',
                'texto': texto_nat,
                'fluencia': '',
                'coerencia': '',
                'realismo': '',
                'especificidade': ''
            })
            linhas.append({
                'dominio': dominio,
                'arquivo': nome_base,
                'tipo': 'sintetico',
                'texto': texto_sint,
                'fluencia': '',
                'coerencia': '',
                'realismo': '',
                'especificidade': ''
            })
    df_csv = pd.DataFrame(linhas)
    csv_path = os.path.join(RESULTADOS_DIR, "avaliacao_humana.csv")
    df_csv.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"CSV salvo em: {csv_path}")

    print("\n=== 6. Gerando gráficos e testes estatísticos ===")
    resultados_teste = {}
    for dominio in DOMINIOS:
        print(f"\n--- {dominio.upper()} ---")
        testes = gerar_graficos(dados_naturais, dados_sinteticos, dominio, RESULTADOS_DIR)
        if testes:
            resultados_teste[dominio] = testes

    with open(os.path.join(RESULTADOS_DIR, "testes_estatisticos.json"), 'w', encoding='utf-8') as f:
        json.dump(resultados_teste, f, indent=2, ensure_ascii=False)

    print("\n=== Análise concluída ===")
    print(f"Resultados salvos em: {RESULTADOS_DIR}")

if __name__ == "__main__":
    main()