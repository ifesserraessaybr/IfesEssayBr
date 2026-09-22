import os
import re
import json
import statistics
from syllable import word2syllables, stressed_syllable

def extrair_palavras(texto):
   
    if not texto or texto.strip() == "":
        return []
    return re.findall(r'\b[a-zA-ZÀ-ÿ]{3,}\b', texto.lower())

def analise_silabica_unifica(palavras):
    
    if not palavras:
        return 0, set(), 0, 0, 0
    
    total_silabas = 0
    silabas_unicas = set()
    palavras_3silabas = 0  
    palavras_4silabas = 0  
    palavras_5silabas = 0  
    
    for palavra in palavras:
        try:
            silabas = word2syllables(palavra)
            num_silabas = len(silabas)
            total_silabas += num_silabas
            silabas_unicas.update(silabas)
            
         
            if num_silabas >= 3:
                palavras_3silabas += 1
            if num_silabas >= 4:
                palavras_4silabas += 1
            if num_silabas >= 5:
                palavras_5silabas += 1
                
        except Exception:
            continue
    
    return total_silabas, silabas_unicas, palavras_3silabas, palavras_4silabas, palavras_5silabas

def diversidade_lexica(texto):
    palavras = extrair_palavras(texto)
    if not palavras:
        return 0
    return len(set(palavras)) / len(palavras)

def analise_silabica(texto):
    
    palavras = extrair_palavras(texto)
    if not palavras:
        return 0, 0, 0
    
    total_silabas, silabas_unicas, palavras_3silabas, _, _ = analise_silabica_unifica(palavras)
    
    if total_silabas == 0:
        return 0, 0, 0
    
    diversidade_silabica = len(silabas_unicas) / total_silabas
    proporcao_complexas = palavras_3silabas / len(palavras)
    silabas_por_palavra = total_silabas / len(palavras)
    
    return diversidade_silabica, proporcao_complexas, silabas_por_palavra

def complexidade_lexica(texto):
   
    palavras = extrair_palavras(texto)
    if not palavras:
        return 0, 0, 0, 0
    
    total_silabas, _, _, palavras_4silabas, palavras_5silabas = analise_silabica_unifica(palavras)
    
    
    proporcao_longas = palavras_4silabas / len(palavras)
    proporcao_muito_longas = palavras_5silabas / len(palavras)
    silabas_por_palavra = total_silabas / len(palavras)
    
    
    indice_complexidade = (proporcao_longas * 0.4 + 
                          proporcao_muito_longas * 0.3 + 
                          min(silabas_por_palavra / 8, 1) * 0.3)
    
    return indice_complexidade, proporcao_longas, proporcao_muito_longas, silabas_por_palavra

def classificar_complexidade(valor):
 
    if valor < 0.2: 
        return "Baixa"
    elif valor < 0.35: 
        return "Média"
    else: 
        return "Alta"

def complexidade_geral_dataset(resultados):
  
    scores_gerais = []
    classificacoes = {"Baixa": 0, "Média": 0, "Alta": 0}
    
    for arquivo, dados in resultados.items():
        if dados['diversidade_lexica'] > 0: 
          
            score = (dados['complexidade_lexica'] * 0.4 +
                    dados['proporcao_palavras_longas'] * 0.3 +
                    min(dados['silabas_por_palavra'] / 4, 1) * 0.2 +
                    dados['proporcao_complexas'] * 0.1)
            scores_gerais.append(score)
            
            
            classificacao = classificar_complexidade(dados['complexidade_lexica'])
            classificacoes[classificacao] += 1
    
    complexidade_media = statistics.mean(scores_gerais) if scores_gerais else 0
    classificacao_geral = classificar_complexidade(complexidade_media)
    
    return {
        'complexidade_media': complexidade_media,
        'classificacao_geral': classificacao_geral,
        'distribuicao_classificacoes': classificacoes,
        'total_avaliados': len(scores_gerais)
    }

def calcular_correlacao(resultados):
    """Calcula correlação entre diversidade e complexidade"""
    diversidades = []
    complexidades = []
    
    for arquivo, dados in resultados.items():
        if dados['diversidade_lexica'] > 0:
            diversidades.append(dados['diversidade_lexica'])
            complexidades.append(dados['complexidade_lexica'])
    
    if len(diversidades) > 1:
        try:
            correlacao = statistics.correlation(diversidades, complexidades)
            return correlacao
        except:
            return 0
    return 0

def calcular_estatisticas(valores):
    if not valores:
        return 0, 0, 0
    
    valores_validos = [v for v in valores if v > 0]
    if not valores_validos:
        return 0, 0, 0
    
    media = statistics.mean(valores_validos)
    desvio_padrao = statistics.stdev(valores_validos) if len(valores_validos) > 1 else 0
    return media, desvio_padrao, len(valores_validos)

def buscar_pasta(pasta):
    resultados_individual = {}
    
   
    valores_diversidade = []
    valores_complexidade_lexica = []
    valores_proporcao_longas = []
    valores_diversidade_silabica = []
    valores_proporcao_complexas = []
    valores_silabas_por_palavra = []
    
    total_palavras = 0
    set_unicas_geral = set()
    arquivos_processados = 0
    arquivos_com_texto = 0

    for arquivo in os.listdir(pasta):
        if arquivo.lower().endswith(".json"):
            caminho = os.path.join(pasta, arquivo)
            try:
                with open(caminho, "r", encoding="utf-8") as arqui:
                    dados = json.load(arqui)
                
                arquivos_processados += 1
                
                if "comando_tematico" in dados and isinstance(dados["comando_tematico"], dict):
                    textos = []
                    for valor in dados["comando_tematico"].values():
                        if isinstance(valor, str):
                            textos.append(valor)
                    texto = " ".join(textos).strip()
                else:
                    texto = ""
                    print(f"Aviso: Campo 'comando_tematico' não encontrado ou inválido em {arquivo}")
                    continue
                
                if not texto:
                    print(f"Aviso: Texto vazio em {arquivo}")
                    resultados_individual[arquivo] = {
                        'diversidade_lexica': 0,
                        'complexidade_lexica': 0,
                        'proporcao_palavras_longas': 0,
                        'diversidade_silabica': 0,
                        'proporcao_complexas': 0,
                        'silabas_por_palavra': 0
                    }
                    continue
                
                arquivos_com_texto += 1
           
          
                diversidade = diversidade_lexica(texto)
                valores_diversidade.append(diversidade)
                
                complexidade, prop_longas, prop_muito_longas, silabas_palavra_cl = complexidade_lexica(texto)
                valores_complexidade_lexica.append(complexidade)
                valores_proporcao_longas.append(prop_longas)
                
                diversidade_silabica, proporcao_complexas, silabas_por_palavra = analise_silabica(texto)
                valores_diversidade_silabica.append(diversidade_silabica)
                valores_proporcao_complexas.append(proporcao_complexas)
                valores_silabas_por_palavra.append(silabas_por_palavra)
                
         
                resultados_individual[arquivo] = {
                    'diversidade_lexica': diversidade,
                    'complexidade_lexica': complexidade,
                    'proporcao_palavras_longas': prop_longas,
                    'diversidade_silabica': diversidade_silabica,
                    'proporcao_complexas': proporcao_complexas,
                    'silabas_por_palavra': silabas_por_palavra
                }

            
                palavras = extrair_palavras(texto)
                if palavras:  
                    total_palavras += len(palavras)
                    set_unicas_geral.update(palavras)
                        
            except Exception as e:
                print(f"Erro ao ler {arquivo}: {e}")
                continue

    diversidade_geral = len(set_unicas_geral) / total_palavras if total_palavras > 0 else 0
    
    
    media_lexica, desvio_lexica, arquivos_validos_lexica = calcular_estatisticas(valores_diversidade)
    media_complexidade, _, _ = calcular_estatisticas(valores_complexidade_lexica)
    media_prop_longas, _, _ = calcular_estatisticas(valores_proporcao_longas)
    media_silabica, _, _ = calcular_estatisticas(valores_diversidade_silabica)
    media_complexas, _, _ = calcular_estatisticas(valores_proporcao_complexas)
    media_silabas_palavra, _, _ = calcular_estatisticas(valores_silabas_por_palavra)
    
    
    complexidade_dataset = complexidade_geral_dataset(resultados_individual)
    correlacao_div_comp = calcular_correlacao(resultados_individual)
    
    print(f"\n=== ESTATÍSTICAS GERAIS (COMANDOS TEMÁTICOS - IA) ===")
    print(f"Total de arquivos processados: {arquivos_processados}")
    print(f"Arquivos com texto válido: {arquivos_com_texto}")
    print(f"Arquivos com diversidade > 0: {arquivos_validos_lexica}")
    
    print(f"\n--- DIVERSIDADE LÉXICA ---")
    print(f"Diversidade léxica geral: {diversidade_geral:.3f} ({diversidade_geral*100:.1f}%)")
    print(f"Média das diversidades individuais: {media_lexica:.3f} ({media_lexica*100:.1f}%)")
    print(f"Desvio padrão: {desvio_lexica:.3f}")
    
    print(f"\n--- COMPLEXIDADE LEXICAL ---")
    print(f"Complexidade lexical média: {media_complexidade:.3f} ({media_complexidade*100:.1f}%)")
    print(f"Proporção de palavras longas (4+ sílabas): {media_prop_longas:.3f} ({media_prop_longas*100:.1f}%)")
    
    print(f"\n--- COMPLEXIDADE SILÁBICA ---")
    print(f"Diversidade silábica média: {media_silabica:.3f} ({media_silabica*100:.1f}%)")
    print(f"Proporção de palavras complexas (3+ sílabas): {media_complexas:.3f} ({media_complexas*100:.1f}%)")
    print(f"Média de sílabas por palavra: {media_silabas_palavra:.2f}")
    
    print(f"\n--- ANÁLISE AVANÇADA DO DATASET ---")
    print(f"Complexidade geral do dataset: {complexidade_dataset['complexidade_media']*100:.1f}%")
    print(f"Classificação geral: {complexidade_dataset['classificacao_geral']}")
    print(f"Distribuição de complexidade: {complexidade_dataset['distribuicao_classificacoes']}")
    print(f"Correlação Diversidade-Complexidade: {correlacao_div_comp:.3f}")
    
    return (resultados_individual, diversidade_geral, media_lexica, desvio_lexica, 
            arquivos_validos_lexica, media_complexidade, media_prop_longas, 
            media_silabica, media_silabas_palavra, media_complexas,
            complexidade_dataset, correlacao_div_comp)

def main():
    pasta = "C:/Users/Maxine/Downloads/IC/ChatgptTurbo"
    
    (resultados, diversidade_geral, media, desvio_padrao, arquivos_validos,
     complexidade, props_longas, silabica, silabas_palavra, complexas,
     complexidade_dataset, correlacao) = buscar_pasta(pasta)

    resultados_dir = "C:/Users/Maxine/Downloads/IC/Resultados"
    os.makedirs(resultados_dir, exist_ok=True)

    resultados_separados = os.path.join(resultados_dir, "Resultados_Separados.txt")
    resultado_dataSet = os.path.join(resultados_dir, "Resultado_dataSet.txt")

    with open(resultados_separados, "w", encoding="utf-8") as arqui:
        arqui.write("DIVERSIDADE LÉXICA, COMPLEXIDADE LEXICAL E ANÁLISE SILÁBICA - RESULTADOS INDIVIDUAIS\n")
        arqui.write("=" * 90 + "\n")
        for nome, valores in resultados.items():
            if valores['diversidade_lexica'] > 0:  
                classificacao = classificar_complexidade(valores['complexidade_lexica'])
                arqui.write(f"{nome}:\n")
                arqui.write(f"  Diversidade Léxica: {valores['diversidade_lexica']:.3f} ({valores['diversidade_lexica']*100:.1f}%)\n")
                arqui.write(f"  Complexidade Lexical: {valores['complexidade_lexica']:.3f} ({valores['complexidade_lexica']*100:.1f}%) - {classificacao}\n")
                arqui.write(f"  Palavras Longas (4+ sílabas): {valores['proporcao_palavras_longas']:.3f} ({valores['proporcao_palavras_longas']*100:.1f}%)\n")
                arqui.write(f"  Diversidade Silábica: {valores['diversidade_silabica']:.3f} ({valores['diversidade_silabica']*100:.1f}%)\n")
                arqui.write(f"  Palavras Complexas (3+ sílabas): {valores['proporcao_complexas']:.3f} ({valores['proporcao_complexas']*100:.1f}%)\n")
                arqui.write(f"  Sílabas por Palavra: {valores['silabas_por_palavra']:.2f}\n")
                arqui.write("\n")
        
        arqui.write("=" * 90 + "\n")
        arqui.write(f"ESTATÍSTICAS GERAIS:\n")
        arqui.write(f"Diversidade Léxica Média: {media*100:.1f}%\n")
        arqui.write(f"Desvio Padrão: {desvio_padrao*100:.1f}%\n")
        arqui.write(f"Complexidade Léxica Média: {complexidade*100:.1f}%\n")
        arqui.write(f"Proporção de palavras longas (4+ sílabas): {props_longas*100:.1f}%\n")
        arqui.write(f"Diversidade silábica média: {silabica*100:.1f}%\n")
        arqui.write(f"Proporção de palavras complexas (3+ sílabas): {complexas*100:.1f}%\n")
        arqui.write(f"Média de sílabas por palavra: {silabas_palavra:.2f}\n")
        arqui.write(f"Diversidade de todo dataset: {diversidade_geral*100:.1f}%\n")
        arqui.write(f"Arquivos válidos: {arquivos_validos}\n")
        
 
        arqui.write(f"\n--- ANÁLISE AVANÇADA ---\n")
        arqui.write(f"Complexidade geral do dataset: {complexidade_dataset['complexidade_media']*100:.1f}%\n")
        arqui.write(f"Classificação geral: {complexidade_dataset['classificacao_geral']}\n")
        arqui.write(f"Distribuição de complexidade: {complexidade_dataset['distribuicao_classificacoes']}\n")
        arqui.write(f"Correlação Diversidade-Complexidade: {correlacao:.3f}\n")

    with open(resultado_dataSet, "w", encoding="utf-8") as arqui:
        arqui.write("DIVERSIDADE LÉXICA, COMPLEXIDADE LEXICAL E COMPLEXIDADE SILÁBICA - COMANDOS TEMÁTICOS (IA)\n")
        arqui.write("=" * 80 + "\n")
        arqui.write(f"Diversidade Léxica Média: {media*100:.1f}%\n")
        arqui.write(f"Desvio Padrão: {desvio_padrao*100:.1f}%\n")
        arqui.write(f"Complexidade Léxica Média: {complexidade*100:.1f}%\n")
        arqui.write(f"Proporção de palavras longas (4+ sílabas): {props_longas*100:.1f}%\n")
        arqui.write(f"Diversidade silábica média: {silabica*100:.1f}%\n")
        arqui.write(f"Proporção de palavras complexas (3+ sílabas): {complexas*100:.1f}%\n")
        arqui.write(f"Média de sílabas por palavra: {silabas_palavra:.2f}\n")
        arqui.write(f"Diversidade de todo dataset: {diversidade_geral*100:.1f}%\n")
        arqui.write(f"Total de Arquivos: {len(resultados)}\n")
        arqui.write(f"Arquivos Válidos: {arquivos_validos}\n")
        
  
        arqui.write(f"\n--- COMPLEXIDADE GERAL ---\n")
        arqui.write(f"Score de Complexidade: {complexidade_dataset['complexidade_media']:.3f}\n")
        arqui.write(f"Classificação: {complexidade_dataset['classificacao_geral']}\n")
        arqui.write(f"Correlação Diver-Complex: {correlacao:.3f}\n")

if __name__ == "__main__":
    main()