import os
import re
import statistics
import json
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy.stats import mannwhitneyu, bootstrap
import numpy as np

def natural_sort_key(texto):
    return [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', texto)]

def extrair_palavras(texto): #extrai as palavras e separa as consideradas e não consideradas. As consideradas são as que tem 3 ou mais letras.
    if not texto or not texto.strip():
        return [], []
    todas_palavras = re.findall(r'\b\w+\b', texto.lower())  # todas as palavras
    palavras_identificadas = [p for p in todas_palavras if re.match(r'[a-zà-ÿ]{3,}', p, re.IGNORECASE)]
    palavras_nao_identificadas = [p for p in todas_palavras if not re.match(r'[a-zà-ÿ]{3,}', p, re.IGNORECASE)]
    return palavras_identificadas, palavras_nao_identificadas

def calcular_ttr(palavras_identificadas): #calculo diversidade
    if not palavras_identificadas:
        return 0.0
    return len(set(palavras_identificadas)) / len(palavras_identificadas)

def calcular_ic(dados, func=np.mean): #calculo intervalo de confiança 95%
    dados = (np.array(dados),)
    if len(dados[0]) < 2:
        return None
    result = bootstrap(dados, func, confidence_level=0.95, n_resamples=10000, method='percentile')
    return result.confidence_interval.low, result.confidence_interval.high

def processar_data(): #processamento arquivos do data (dataset com os comandos tematicos originais)
    caminho_base = "Data"
    ttrs = []
    palavras_nao_identificadas_total = set()
    total_palavras = 0
    total_palavras_id = 0
    print("\nDataset Data - TTR e palavras não identificadas (<body> em arquivos XML com ElementTree)")
    for root, dirs, files in os.walk(caminho_base):
        for file in files:
            if "prompt" in file.lower() and file.lower().endswith(".xml"):
                arquivo_path = os.path.join(root, file)
                try:
                    tree = ET.parse(arquivo_path)
                    root_element = tree.getroot()
                    body_element = root_element.find('.//body')
                    if body_element is not None:
                        texto_body = (body_element.text or "").strip()
                        palavras_id, palavras_nao_id = extrair_palavras(texto_body)
                        total_palavras += len(palavras_id) + len(palavras_nao_id)
                        total_palavras_id += len(palavras_id)
                        palavras_nao_identificadas_total.update(palavras_nao_id)
                        ttr = calcular_ttr(palavras_id)
                        if ttr > 0:
                            nome_subpasta = os.path.basename(root)
                            print(f"Subpasta: {nome_subpasta:<30} Arquivo: {file:<30} → TTR: {ttr:.4f}")
                            ttrs.append(ttr)
                    else:
                        print(f"Arquivo {file} não contém tag <body>")
                except Exception as e:
                    print(f"Erro ao processar {arquivo_path}: {e}")

    percentual_id = (total_palavras_id / total_palavras)*100 if total_palavras > 0 else 0
    print(f"\n% Palavras identificadas Dataset Data: {percentual_id:.2f}%")
    with open("palavras_nao_identificadas_data.txt", "w", encoding="utf-8") as f_out:
        f_out.write("\n".join(sorted(palavras_nao_identificadas_total)))
    return ttrs

def processar_qwenmax(): #processamento arquivos do qwen max (dataset com os comandos tematicos sinteticos)
    pasta = "QwenMax"
    ttrs = []
    palavras_nao_identificadas_total = set()
    total_palavras = 0
    total_palavras_id = 0
    print("\nDataset QwenMax - TTR e palavras não identificadas")
    if not os.path.isdir(pasta):
        print(f"Pasta '{pasta}' não encontrada.")
        return ttrs
    arquivos = [f for f in os.listdir(pasta) if f.endswith(".json")]
    arquivos.sort(key=natural_sort_key)
    for arquivo in arquivos:
        caminho = os.path.join(pasta, arquivo)
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
            comando_tematico = dados.get("comando_tematico")
            if comando_tematico:
                texto = " ".join(comando_tematico.values()).strip()
                palavras_id, palavras_nao_id = extrair_palavras(texto)
                total_palavras += len(palavras_id) + len(palavras_nao_id)
                total_palavras_id += len(palavras_id)
                palavras_nao_identificadas_total.update(palavras_nao_id)
                ttr = calcular_ttr(palavras_id)
                if ttr > 0:
                    print(f"{arquivo:<40} → TTR: {ttr:.4f}")
                    ttrs.append(ttr)
        except Exception as e:
            print(f"Erro ao processar {caminho}: {e}")

    percentual_id = (total_palavras_id / total_palavras)*100 if total_palavras > 0 else 0
    print(f"\n% Palavras identificadas Dataset QwenMax: {percentual_id:.2f}%")
    with open("palavras_nao_identificadas_qwenmax.txt", "w", encoding="utf-8") as f_out:
        f_out.write("\n".join(sorted(palavras_nao_identificadas_total)))
    return ttrs

def plotar_ttr_boxplots(ttrs_qwenmax, ttrs_data): #blox-splot
    colors = ['#1f77b4', '#add8e6']  # azul escuro (QwenMax) e azul claro (Data)
    labels = ['QwenMax', 'Data']

    mean_qwenmax = statistics.mean(ttrs_qwenmax) if ttrs_qwenmax else 0
    std_qwenmax = statistics.stdev(ttrs_qwenmax) if len(ttrs_qwenmax) > 1 else 0
    mean_data = statistics.mean(ttrs_data) if ttrs_data else 0
    std_data = statistics.stdev(ttrs_data) if len(ttrs_data) > 1 else 0

    print(f"\nQwenMax - Média TTR: {mean_qwenmax:.4f}, Desvio padrão: {std_qwenmax:.4f}")
    print(f"Data - Média TTR: {mean_data:.4f}, Desvio padrão: {std_data:.4f}")

    fig, ax = plt.subplots(figsize=(10, 6))
    box = ax.boxplot([ttrs_qwenmax, ttrs_data], patch_artist=True, tick_labels=labels, showmeans=True,
                     meanprops={"marker":"^", "markerfacecolor":"green", "markeredgecolor":"black", "markersize":10})

    for patch, color in zip(box['boxes'], colors):
        patch.set_facecolor(color)

    legend_elements = [
        Line2D([0], [0], color=colors[0], lw=4, label='QwenMax'),
        Line2D([0], [0], color=colors[1], lw=4, label=' Data'),
        Line2D([0], [0], marker='^', color='w', label='Média', markerfacecolor='green', markeredgecolor='black', markersize=10)
    ]

    ax.legend(handles=legend_elements, loc='upper right')
    ax.set_title("Comparação do Tipo-Token Ratio (TTR)")
    ax.set_ylabel("TTR")
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    plt.show()

def main():
    ttrs_qwenmax = processar_qwenmax()
    ttrs_data = processar_data()

    # Cálculo do p-value e intervalo de confiança
    if len(ttrs_qwenmax) >= 2 and len(ttrs_data) >= 2:
        p_valor = mannwhitneyu(ttrs_qwenmax, ttrs_data, alternative='greater').pvalue
        ic_qwenmax = calcular_ic(ttrs_qwenmax)
        ic_data = calcular_ic(ttrs_data)
        print(f"\nAnálise estatística:")
        print(f"p-valor (Data > QwenMax): {p_valor:.15f}")
        print(f"Intervalo de Confiança QwenMax (95%): {ic_qwenmax}")
        print(f"Intervalo de Confiança Data (95%): {ic_data}")
    else:
        print("Dados insuficientes para análise estatística.")

    plotar_ttr_boxplots(ttrs_qwenmax, ttrs_data)

if __name__ == "__main__":
    main()
