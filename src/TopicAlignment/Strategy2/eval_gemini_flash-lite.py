import os
import random
import math
import re
import time
import json
import sys
import subprocess

def verificar_e_instalar_dependencias():
    """Verifica se matplotlib e seaborn estão instalados; se não, instala automaticamente."""
    dependencias = ["matplotlib", "seaborn"]
    faltando = []
    
    for lib in dependencias:
        try:
            __import__(lib)
        except ImportError:
            faltando.append(lib)
            
    if faltando:
        print(f"[Ambiente] Bibliotecas faltando detectadas: {faltando}")
        print("[Ambiente] Tentando instalar dependências automaticamente... Por favor, aguarde.")
        try:
            # Executa o pip install silenciosamente no terminal do Windows
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + faltando)
            print("[Ambiente] Todas as dependências foram instaladas com sucesso!\n")
        except Exception as e:
            print(f"[Erro Ambiente] Não foi possível instalar automaticamente. Erro: {e}")
            print("[Erro Ambiente] Por favor, abra o CMD e digite: pip install matplotlib seaborn")
            sys.exit(1)

# Executa a checagem ANTES de importar o pipeline e as ferramentas de gráfico
verificar_e_instalar_dependencias()

# Agora os imports avançados estão seguros contra erros de 'ModuleNotFoundError'
from transformers import pipeline
import matplotlib.pyplot as plt
import seaborn as sns

# Semente
random.seed(42)

# --- Caminhos Ajustados para a pasta Flash Lite ---
ARQUIVO_TXT_PROGRESSO = "progresso_subjetividade_flash_lite.txt"
ARQUIVO_RELATORIO_FINAL = "relatorio_final_flash_lite.txt"
CAMINHO_PASTA = r"C:\Users\joaqu\OneDrive\Desktop\IC\dataset_sintetico_flash_lite"

# Inicialização do pipeline de classificação de estilo
analisador_subjetividade = pipeline(
    "text-classification", 
    model="cffl/bert-base-styleclassification-subjective-neutral"
)

def extrair_texto(campo_redacao):
    """Trata o campo do JSON para unificar o texto de forma ordenada."""
    if isinstance(campo_redacao, dict):
        frases_ordenadas = [campo_redacao[chave] for chave in sorted(campo_redacao.keys(), key=lambda x: int(x) if x.isdigit() else x)]
        return " ".join(frases_ordenadas)
    elif isinstance(campo_redacao, list):
        return " ".join(str(item) for item in campo_redacao)
    return str(campo_redacao)

def tokenizar(texto):
    """Remove pontuação, passa para minúsculo e divide o texto em palavras (tokens)."""
    if not texto:
        return []
    texto_limpo = re.sub(r'[^\w\s]', '', texto.lower())
    return texto_limpo.split()

def obtener_dados_subjetividade(texto):
    """Calcula a métrica de subjetividade de 0 a 1 e retorna o valor e o texto formatado."""
    if not texto.strip():
        return 0.0, "Subjetividade: 0.0000 (Sem conteúdo)"
    
    # Pausa de segurança 
    time.sleep(0.5)
    
    texto_seguro = texto[:1200]
    
    resultado = analisador_subjetividade(texto_seguro, truncation=True)[0]
    rotulo_original = resultado["label"]
    score_original = resultado["score"]
    
    if rotulo_original == "SUBJECTIVE":
        subjetividade_continua = score_original
        texto_formatado = f"Subjetividade: {subjetividade_continua:.4f}"
    else:
        subjetividade_continua = 1.0 - score_original
        texto_formatado = f"Subjetividade: {subjetividade_continua:.4f} (Neutralidade: {score_original:.4f})"
        
    return subjetividade_continua, texto_formatado

def calcular_metricas_lexicais(campo_redacao):
    """Calcula as métricas léxicas básicas (TTR e Complexidade)."""
    texto = extrair_texto(campo_redacao)
    tokens = tokenizar(texto)
    types = set(tokens)
    
    ttr = len(types) / len(tokens) if tokens else 0
    complexas = [w for w in tokens if len(w) > 6]
    complexidade = len(complexas) / len(tokens) if tokens else 0
    
    return texto, ttr, complexidade

def calcular_estatisticas(valores):
    """Calcula média, desvio padrão e mediana de uma lista de números."""
    if not valores:
        return 0, 0, 0
    n = len(valores)
    media = sum(valores) / n
    
    valores_ordenados = sorted(valores)
    if n % 2 == 1:
        mediana = valores_ordenados[n // 2]
    else:
        mediana = (valores_ordenados[(n // 2) - 1] + valores_ordenados[n // 2]) / 2
        
    variancia = sum((x - media) ** 2 for x in valores) / n
    desvio_padrao = math.sqrt(variancia)
    
    return media, desvio_padrao, mediana

def carregar_progresso_txt():
    """Carrega o histórico do TXT estruturado por pipe (|) para um dicionário na memória."""
    progresso = {}
    if os.path.exists(ARQUIVO_TXT_PROGRESSO):
        with open(ARQUIVO_TXT_PROGRESSO, 'r', encoding='utf-8') as f:
            for linha in f:
                linha = linha.strip()
                if not linha:
                    continue
                partes = linha.split('|')
                if len(partes) == 9:
                    nome_arq, ttr_o, comp_o, sub_o, txt_sub_o, ttr_s, comp_s, sub_s, txt_sub_s = partes
                    progresso[nome_arq] = {
                        "ttr_original": float(ttr_o),
                        "complexidade_original": float(comp_o),
                        "subjetividade_original": float(sub_o),
                        "texto_subjetividade_original": txt_sub_o,
                        "ttr_sintetica": float(ttr_s),
                        "complexidade_sintetica": float(comp_s),
                        "subjetividade_sintetica": float(sub_s),
                        "texto_subjetividade_sintetica": txt_sub_s
                    }
    return progresso

def salvar_linha_progresso_txt(nome_arq, dados):
    """Adiciona uma nova linha de sucesso no final do arquivo TXT (append)."""
    with open(ARQUIVO_TXT_PROGRESSO, 'a', encoding='utf-8') as f:
        linha = f"{nome_arq}|{dados['ttr_original']}|{dados['complexidade_original']}|{dados['subjetividade_original']}|{dados['texto_subjetividade_original']}|{dados['ttr_sintetica']}|{dados['complexidade_sintetica']}|{dados['subjetividade_sintetica']}|{dados['texto_subjetividade_sintetica']}\n"
        f.write(linha)

def gerar_boxplots_comparativos(ttr_orig, ttr_sint, comp_orig, comp_sint, sub_orig, sub_sint):
    """Gera, exibe na tela e salva gráficos Boxplot comparativos para o ambiente local."""
    print("\n[Gráficos] Gerando Boxplots comparativos...")
    
    sns.set_theme(style="whitegrid")
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('Comparação de Métricas: Redações Originais vs. Flash Lite', fontsize=16, fontweight='bold')
    
    # 1. Boxplot para Diversidade Lexical (TTR)
    sns.boxplot(data=[ttr_orig, ttr_sint], ax=axes[0], palette="Set2")
    axes[0].set_title('Diversidade Lexical (TTR)')
    axes[0].set_xticklabels(['Original', 'Flash Lite'])
    
    # 2. Boxplot para Complexidade Léxica
    sns.boxplot(data=[comp_orig, comp_sint], ax=axes[1], palette="Pastel1")
    axes[1].set_title('Complexidade Léxica (> 6 letras)')
    axes[1].set_xticklabels(['Original', 'Flash Lite'])
    
    # 3. Boxplot para Subjetividade
    sns.boxplot(data=[sub_orig, sub_sint], ax=axes[2], palette="Accent")
    axes[2].set_title('Métrica de Subjetividade')
    axes[2].set_xticklabels(['Original', 'Flash Lite'])
    
    plt.tight_layout()
    
    nome_grafico = os.path.join(CAMINHO_PASTA, "boxplot_comparativo_flash_lite.png")
    plt.savefig(nome_grafico, dpi=300)
    print(f"[Gráficos] Gráfico Boxplot salvo com sucesso em: {nome_grafico}")
    
    plt.show()

# --- Fluxo Principal Executado pelo Geany ---

progresso_atual = carregar_progresso_txt()
pares_redacoes = []

if not os.path.exists(CAMINHO_PASTA):
    print(f"Erro: O caminho '{CAMINHO_PASTA}' não foi encontrado.")
    exit()

arquivos = [f for f in os.listdir(CAMINHO_PASTA) if f.endswith('.json')]

for arquivo in arquivos:
    caminho_arquivo = os.path.join(CAMINHO_PASTA, arquivo)
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            original = dados.get("redacao_original", "")
            sintetica = dados.get("redacao_gerada", "")
            
            if original or sintetica:
                pares_redacoes.append({
                    "arquivo": arquivo,
                    "original": original,
                    "sintetica": sintetica
                })
    except Exception as e:
        print(f"Erro ao ler o arquivo {arquivo}: {e}")

arquivos_com_erro = []

print("\nIniciando processamento das redações...")
for idx, par in enumerate(pares_redacoes, start=1):
    nome_arq = par["arquivo"]
    
    print(f"Processando arquivo pendente [{idx}/{len(pares_redacoes)}]: {nome_arq}")
    
    if nome_arq in progresso_atual:
        continue
        
    try:
        texto_orig, ttr_orig, comp_orig = calcular_metricas_lexicais(par["original"])
        texto_sint, ttr_sint, comp_sint = calcular_metricas_lexicais(par["sintetica"])
        
        sub_orig, txt_sub_orig = obtener_dados_subjetividade(texto_orig)
        sub_sint, txt_sub_sint = obtener_dados_subjetividade(texto_sint)
        
        novos_dados = {
            "ttr_original": ttr_orig,
            "complexidade_original": comp_orig,
            "subjetividade_original": sub_orig,
            "texto_subjetividade_original": txt_sub_orig,
            "ttr_sintetica": ttr_sint,
            "complexidade_sintetica": comp_sint,
            "subjetividade_sintetica": sub_sint,
            "texto_subjetividade_sintetica": txt_sub_sint
        }
        
        progresso_atual[nome_arq] = novos_dados
        salvar_linha_progresso_txt(nome_arq, novos_dados)
        
    except Exception as e:
        print(f"  [Erro] Falha ao processar o arquivo {nome_arq}. Mantido na lista de pendentes. Detalhe: {e}")
        arquivos_com_erro.append(nome_arq)

total_arquivos_pasta = len(pares_redacoes)
total_processados_sucesso = len(progresso_atual)

if total_processados_sucesso < total_arquivos_pasta:
    print("\n" + "="*60)
    print("AVISO: O PROCESSAMENTO AINDA NÃO FOI TOTALMENTE CONCLUÍDO.")
    print(f"Sucesso: {total_processados_sucesso} de {total_arquivos_pasta} arquivos registrados no TXT.")
    print(f"Arquivos que falharam nesta rodada: {len(arquivos_com_erro)}")
    print("Execute o script novamente para processar apenas os que faltam.")
    print("="*60)
else:
    print("\n[OK] 100% dos arquivos processados! Gerando arquivo de relatório completo...")
    
    tamanho_grupo = 15
    pares_ordenados_com_dados = []
    for par in pares_redacoes:
        nome_arq = par["arquivo"]
        dados_calculados = progresso_atual[nome_arq]
        pares_ordenados_com_dados.append({
            "arquivo": nome_arq,
            **dados_calculados
        })
        
    random.shuffle(pares_ordenados_com_dados)
    grupos = [pares_ordenados_com_dados[i:i + tamanho_grupo] for i in range(0, len(pares_ordenados_com_dados), tamanho_grupo)]
    
    todas_ttr_originais = []
    todas_comp_originais = []
    todas_sub_originais = []
    todas_ttr_sinteticas = []
    todas_comp_sinteticas = []
    todas_sub_sinteticas = []

    with open(ARQUIVO_RELATORIO_FINAL, 'w', encoding='utf-8') as f_rel:
        
        def imprimir_e_salvar(texto):
            print(texto)
            f_rel.write(texto + "\n")

        imprimir_e_salvar("#"*80)
        imprimir_e_salvar("Resultados da Análise Léxica e de Estilo (Original versus Flash Lite)")
        imprimir_e_salvar("#"*80)

        for idx, group in enumerate(grupos, start=1):
            imprimir_e_salvar(f"\nGrupo {idx} ({len(group)} pares)")
            
            grupo_ttr_originais = []
            grupo_comp_originais = []
            grupo_sub_originais = []
            grupo_ttr_sinteticas = []
            grupo_comp_sinteticas = []
            grupo_sub_sinteticas = []
            
            # --- IMPRESSÃO DETALHADA PAR POR PAR DENTRO DO GRUPO ---
            for j, par in enumerate(group, start=1):
                imprimir_e_salvar(f"Par {j} - Nome do Arquivo: {par['arquivo']}")
                imprimir_e_salvar(f"  Redação Original  - Diversidade Lexical (TTR): {par['ttr_original']:.4f} / Complexidade Léxica: {par['complexidade_original']:.4f} / {par['texto_subjetividade_original']}")
                imprimir_e_salvar(f"  Redação Sintética - Diversidade Lexical (TTR): {par['ttr_sintetica']:.4f} / Complexidade Léxica: {par['complexidade_sintetica']:.4f} / {par['texto_subjetividade_sintetica']}")
                
                grupo_ttr_originais.append(par['ttr_original'])
                grupo_comp_originais.append(par['complexidade_original'])
                grupo_sub_originais.append(par['subjetividade_original'])
                
                grupo_ttr_sinteticas.append(par['ttr_sintetica'])
                grupo_comp_sinteticas.append(par['complexidade_sintetica'])
                grupo_sub_sinteticas.append(par['subjetividade_sintetica'])
                
                todas_ttr_originais.append(par['ttr_original'])
                todas_comp_originais.append(par['complexidade_original'])
                todas_sub_originais.append(par['subjetividade_original'])
                
                todas_ttr_sinteticas.append(par['ttr_sintetica'])
                todas_comp_sinteticas.append(par['complexidade_sintetica'])
                todas_sub_sinteticas.append(par['subjetividade_sintetica'])
            
            med_ttr_o, dp_ttr_o, medn_ttr_o = calcular_estatisticas(grupo_ttr_originais)
            med_comp_o, dp_comp_o, medn_comp_o = calcular_estatisticas(grupo_comp_originais)
            med_sub_o, dp_sub_o, medn_sub_o = calcular_estatisticas(grupo_sub_originais)
            
            med_ttr_s, dp_ttr_s, medn_ttr_s = calcular_estatisticas(grupo_ttr_sinteticas)
            med_comp_s, dp_comp_s, medn_comp_s = calcular_estatisticas(grupo_comp_sinteticas)
            med_sub_s, dp_sub_s, medn_sub_s = calcular_estatisticas(grupo_sub_sinteticas)
            
            imprimir_e_salvar(f"\nEstatísticas do Grupo {idx}:")
            imprimir_e_salvar(f"  Média da Diversidade Lexical (Original / Sintética): {med_ttr_o:.4f} / {med_ttr_s:.4f}")
            imprimir_e_salvar(f"  Desvio Padrão da Diversidade Lexical (Original / Sintética): {dp_ttr_o:.4f} / {dp_ttr_s:.4f}")
            imprimir_e_salvar(f"  Mediana da Diversidade Lexical (Original / Sintética): {medn_ttr_o:.4f} / {medn_ttr_s:.4f}")
            imprimir_e_salvar(f"  Média da Complexidade Léxica (Original / Sintética): {med_comp_o:.4f} / {med_comp_s:.4f}")
            imprimir_e_salvar(f"  Desvio Padrão da Complexidade Léxica (Original / Sintética): {dp_comp_o:.4f} / {dp_comp_s:.4f}")
            imprimir_e_salvar(f"  Mediana da Complexidade Léxica (Original / Sintética): {medn_comp_o:.4f} / {medn_comp_s:.4f}")
            imprimir_e_salvar(f"  Média da Subjetividade (Original / Sintética): {med_sub_o:.4f} / {med_sub_s:.4f}")
            imprimir_e_salvar(f"  Desvio Padrão da Subjetividade (Original / Sintética): {dp_sub_o:.4f} / {dp_sub_s:.4f}")
            imprimir_e_salvar(f"  Mediana da Subjetividade (Original / Sintética): {medn_sub_o:.4f} / {medn_sub_s:.4f}")

        g_med_ttr_o, g_dp_ttr_o, g_medn_ttr_o = calcular_estatisticas(todas_ttr_originais)
        g_med_comp_o, g_dp_comp_o, g_medn_comp_o = calcular_estatisticas(todas_comp_originais)
        g_med_sub_o, g_dp_sub_o, g_medn_sub_o = calcular_estatisticas(todas_sub_originais)

        g_med_ttr_s, g_dp_ttr_s, g_medn_ttr_s = calcular_estatisticas(todas_ttr_sinteticas)
        g_med_comp_s, g_dp_comp_s, g_medn_comp_s = calcular_estatisticas(todas_comp_sinteticas)
        g_med_sub_s, g_dp_sub_s, g_medn_sub_s = calcular_estatisticas(todas_sub_sinteticas)

        imprimir_e_salvar("\n" + "="*80)
        imprimir_e_salvar("Estatísticas Globais (Todas as Redações Analisadas - Flash Lite)")
        imprimir_e_salvar("="*80)
        imprimir_e_salvar(f"Média da Diversidade Lexical Total (Original / Sintética): {g_med_ttr_o:.4f} / {g_med_ttr_s:.4f}")
        imprimir_e_salvar(f"Desvio Padrão da Diversidade Lexical Total (Original / Sintética): {g_dp_ttr_o:.4f} / {g_dp_ttr_s:.4f}")
        imprimir_e_salvar(f"Mediana da Diversidade Lexical Total (Original / Sintética): {g_medn_ttr_o:.4f} / {g_medn_ttr_s:.4f}")
        imprimir_e_salvar(f"Média da Complexidade Léxica Total (Original / Sintética): {g_med_comp_o:.4f} / {g_med_comp_s:.4f}")
        imprimir_e_salvar(f"Desvio Padrão da Complexidade Léxica Total (Original / Sintética): {g_dp_comp_o:.4f} / {g_dp_comp_s:.4f}")
        imprimir_e_salvar(f"Mediana da Complexidade Léxica Total (Original / Sintética): {g_medn_comp_o:.4f} / {g_medn_comp_s:.4f}")
        imprimir_e_salvar(f"Média da Subjetividade Total (Original / Sintética): {g_med_sub_o:.4f} / {g_med_sub_s:.4f}")
        imprimir_e_salvar(f"Desvio Padrão da Subjetividade Total (Original / Sintética): {g_dp_sub_o:.4f} / {g_dp_sub_s:.4f}")
        imprimir_e_salvar(f"Mediana da Subjetividade Total (Original / Sintética): {g_medn_sub_o:.4f} / {g_medn_sub_s:.4f}")

    print(f"\n[SUCESSO] O relatório compacto foi salvo em: {os.path.abspath(ARQUIVO_RELATORIO_FINAL)}")
    
    # Executa a plotagem gráfica ao final
    gerar_boxplots_comparativos(
        todas_ttr_originais, todas_ttr_sinteticas,
        todas_comp_originais, todas_comp_sinteticas,
        todas_sub_originais, todas_sub_sinteticas
    )

if __name__ == "__main__":
    # O pipeline já foi carregado globalmente no topo
    pass
