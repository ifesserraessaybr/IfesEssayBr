import os
import re
import glob
import json
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import statistics
from scipy.stats import mannwhitneyu, bootstrap
import numpy as np

def word2syllables(word): #separa em silabas
    pattern = r'[^aeiouáéíóúâêîôûãõü]+[aeiouáéíóúâêîôûãõü]+|[aeiouáéíóúâêîôûãõü]+'
    return re.findall(pattern, word, re.IGNORECASE)

def minha_tokenizacao(texto): #tokenização e extração das palavras consideradas, que são as com mais de 3 letras.
    tokens = re.findall(r'\b[\wáéíóúâêîôûãõçü]+\b', texto, re.UNICODE)
    tokens_filtrados = [t for t in tokens if len(t) >= 3]
    return tokens_filtrados

def complexidade_lexical(tokens): #calculo complexidade lexical
    if not tokens:
        return 0
    total_silabas = sum(len(word2syllables(token.lower())) for token in tokens)
    return total_silabas / len(tokens)

def processar_texto(texto): 
    tokens = minha_tokenizacao(texto)
    return complexidade_lexical(tokens)

def natural_key(string_):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', string_)]

def calcular_ic(dados, func=np.mean): #intervalo de confiança 95%
    dados = (np.array(dados),)
    if len(dados[0]) < 2:
        return None
    result = bootstrap(dados, func, confidence_level=0.95, n_resamples=10000, method='percentile', random_state=1)
    return result.confidence_interval.low, result.confidence_interval.high

def processar_dataset_qwenmax(caminho_pasta): #processamento qwenmax (dataset com os comandos tematicos sinteticos)
    comp_lexs = []
    arquivos_json = glob.glob(os.path.join(caminho_pasta, '*.json'))
    arquivos_json.sort(key=natural_key)
    print(f"Processando {len(arquivos_json)} arquivos QwenMax...")
    for arquivo in arquivos_json:
        with open(arquivo, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        if not isinstance(dados, list):
            dados = [dados]
        for item in dados:
            texto_gerado = item.get("comando_tematico", {})
            texto = " ".join(texto_gerado.values()) if texto_gerado else ""
            comp_lex = processar_texto(texto)
            print(f"{os.path.basename(arquivo)} → Complexidade lexical: {comp_lex:.4f}")
            comp_lexs.append(comp_lex)
    return comp_lexs

def processar_dataset_data(caminho_base): #processamento data (dataset com os comandos tematicos originais)
    comp_lexs = []
    arquivos_processados = 0
    print(f"Processando arquivos do Dataset Data em {caminho_base}...")
    for root, dirs, files in os.walk(caminho_base):
        for file in files:
            if "prompt" in file.lower() and file.lower().endswith(".xml"):
                caminho_arquivo = os.path.join(root, file)
                nome_subpasta = os.path.basename(root)
                try:
                    from xml.etree import ElementTree as ET
                    tree = ET.parse(caminho_arquivo)
                    root_element = tree.getroot()
                    body_element = root_element.find('.//body')
                    if body_element is not None:
                        texto = (body_element.text or "").strip()
                        comp_lex = processar_texto(texto)
                        print(f"{file} (Subpasta: {nome_subpasta}) → Complexidade lexical: {comp_lex:.4f}")
                        comp_lexs.append(comp_lex)
                        arquivos_processados += 1
                    else:
                        print(f"Arquivo {file} não contém tag <body>")
                except Exception as e:
                    print(f"Erro ao processar {caminho_arquivo}: {e}")
    print(f"Total de arquivos Data processados: {arquivos_processados}")
    return comp_lexs

def plotar_boxplots(comp_lex_qwenmax, comp_lex_data): #box-splot
    colors = ['#1f77b4', '#add8e6']
    labels = ['QwenMax', 'Dataset Data']

    mean_qwenmax = statistics.mean(comp_lex_qwenmax) if comp_lex_qwenmax else 0
    std_qwenmax = statistics.stdev(comp_lex_qwenmax) if len(comp_lex_qwenmax) > 1 else 0
    mean_data = statistics.mean(comp_lex_data) if comp_lex_data else 0
    std_data = statistics.stdev(comp_lex_data) if len(comp_lex_data) > 1 else 0

    print(f"\nQwenMax - Média: {mean_qwenmax:.4f}, Desvio padrão: {std_qwenmax:.4f}")
    print(f"Dataset Data - Média: {mean_data:.4f}, Desvio padrão: {std_data:.4f}")

    fig, ax = plt.subplots(figsize=(10, 6))
    box = ax.boxplot([comp_lex_qwenmax, comp_lex_data], patch_artist=True, labels=labels, showmeans=True,
                     meanprops={"marker":"o", "markerfacecolor":"green", "markeredgecolor":"black"})

    for patch, color in zip(box['boxes'], colors):
        patch.set_facecolor(color)

    legend_elements = [
        Line2D([0], [0], color=colors[0], lw=4, label='QwenMax'),
        Line2D([0], [0], color=colors[1], lw=4, label='Dataset Data'),
        Line2D([0], [0], marker='o', color='w', label='Média', markerfacecolor='green', markeredgecolor='black', markersize=10)
    ]

    ax.legend(handles=legend_elements, loc='upper right')
    ax.set_title("Comparação da Complexidade Lexical")
    ax.set_ylabel("Média de Sílabas por Palavra")
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    plt.show()

def main():
    caminho_qwenmax = "QwenMax"
    caminho_data = "Data"
    comp_lex_qwenmax = processar_dataset_qwenmax(caminho_qwenmax)
    comp_lex_data = processar_dataset_data(caminho_data)

    # Cálculo do p-value e intervalo de confiança
    if len(comp_lex_qwenmax) >= 2 and len(comp_lex_data) >= 2:
        p_valor = mannwhitneyu(comp_lex_qwenmax, comp_lex_data, alternative='greater').pvalue
        ic_qwenmax = calcular_ic(comp_lex_qwenmax)
        ic_data = calcular_ic(comp_lex_data)
        print(f"\nAnálise estatística:")
        print(f"p-valor (Data > QwenMax): {p_valor:.37f}")
        print(f"Intervalo de Confiança QwenMax (95%): {ic_qwenmax}")
        print(f"Intervalo de Confiança Data (95%): {ic_data}")
    else:
        print("Dados insuficientes para análise estatística.")

    plotar_boxplots(comp_lex_qwenmax, comp_lex_data)

if __name__ == "__main__":
    main()
