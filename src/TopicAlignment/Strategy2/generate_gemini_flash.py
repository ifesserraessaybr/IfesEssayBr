import os
import json
import re
import asyncio
import sys
import time
from google import genai
from google.genai import types

sys.path.append(r"C:\Users\joaqu\OneDrive\Desktop\IC")
from document import Document

PASTA_IC = r"C:\Users\joaqu\OneDrive\Desktop\IC"
PASTA_ENTRADA_JSON = PASTA_IC
PASTA_DATA = os.path.join(PASTA_IC, "data")
PASTA_SAIDA = os.path.join(PASTA_IC, "dataset_sintetico_gemini")
ARQUIVO_PROCESSADOS = os.path.join(PASTA_SAIDA, "processados.txt")

os.makedirs(PASTA_SAIDA, exist_ok=True)
MINHA_CHAVE = ""
from google.genai import Client
client = Client(api_key=MINHA_CHAVE)
SEMAFORO = asyncio.Semaphore(5)
#Prompts
PROMPT_800_1000 = (
    "Redija dissertação-argumentativa formal/rebuscada (padrão ENEM nota 800-1000) sobre '{TEMA}'. "
    "Estrutura rígida de 4 parágrafos (~30 linhas). Introdução (6-7 linhas): apresente tema, contexto e tese com 2 argumentos. "
    "Desenvolvimentos 1 e 2 (7-8 linhas cada): use conectivos interparágrafos, tópicos frasais claros e repertório sociocultural real "
    "(filosofia/sociologia/história legítimos). Conclusão (6-7 lines): conectivo conclusivo, retome tese e apresente proposta de "
    "intervenção com os 5 elements (agente, ação, meio/modo, efeito, detalhamento explícito). Respeite direitos humanos. "
    "Proibido: marcas de oralidade, repetições excessivas, inventar dados/fontes, negritos, títulos ou explicações extras."
)

PROMPT_650_800 = (
    "Redija dissertação-argumentativa comum (padrão ENEM nota 650-800) sobre '{TEMA}'. Sem título, marcações ou explicações. "
    "Use 4 parágrafos (~30 linhas). Desenvolva 2 argumentos coerentes baseados em repertório comum/superficial. Coesão aceitável. "
    "Proposta de intervenção básica. Insira intencionalmente poucos erros ocasionais de ortografia, pontuação, concordância, "
    "regência ou crase, sem invalidar o sentido do texto. Argumentação mediana com leves repetições vocabulares."
)

PROMPT_450_650 = (
    "Redija dissertação-argumentativa mediana/fraca (padrão ENEM nota 450-650) sobre '{TEMA}'. Sem título, marcações ou explicações. "
    "Use 4 parágrafos (~30 linhas). Apresente argumentos superficiais baseados no senso comum e vocabulário muito simples. "
    "Priorize estrutura expositiva em vez de argumentação densa. Insira propositalmente desvios gramaticais recorrentes e alguns "
    "erros graves de concordância, pontuação, regência e acentuação."
)

PROMPT_ABAIXO_450 = (
    "Redija dissertação-argumentativa ruim (padrão ENEM nota abaixo de 450) sobre '{TEMA}'. Sem título, marcações ou explicações. "
    "Use 4 parágrafos (~30 linhas) com linguagem precária e estrutura inadequada. Apresente ideias genéricas, redundantes e vagas. "
    "Tangencie ou fuja do tema proposto. Force recorrência de erros graves de coesão, coerência, ortografia, concordância e "
    "acentuação. Se houver proposta de intervenção, deve ser incompleta, evasiva e sem detalhes."
)

def carregar_dados_dos_temas():
    mapa_temas = {}
    arquivos = [f for f in os.listdir(PASTA_ENTRADA_JSON) if f.endswith(".json") and "_gerado" not in f and f != "prompts_extraidos.json"]
    for arquivo in arquivos:
        caminho = os.path.join(PASTA_ENTRADA_JSON, arquivo)
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
                tema = dados.get("tema", "")
                if tema:
                    mapa_temas[tema] = dados
        except Exception as e:
            print(f"[Erro Inicialização] Falha ao ler JSON {arquivo}: {e}")
    return mapa_temas

def listar_todos_xmls_e_calcular_faixas():
    lista_tarefas_xml = []
    if not os.path.exists(PASTA_DATA):
        return [], []
    for pasta_tema in os.listdir(PASTA_DATA):
        caminho_xml_dir = os.path.join(PASTA_DATA, pasta_tema, "xml")
        if os.path.exists(caminho_xml_dir):
            xmls = [f for f in os.listdir(caminho_xml_dir) if f.endswith(".xml") and not f.startswith("._")]
            for xml in xmls:
                lista_tarefas_xml.append({
                    "pasta_tema": pasta_tema,
                    "nome_xml": xml,
                    "caminho_completo": os.path.join(caminho_xml_dir, xml)
                })
    total_xmls = len(lista_tarefas_xml)
    print(f"[Configuração] Total de XMLs válidos detectados: {total_xmls}")
    quociente = total_xmls // 4
    resto = total_xmls % 4
    lista_faixas = [
        (quociente + resto, PROMPT_800_1000, "800_1000"),
        (quociente, PROMPT_650_800, "650_800"),
        (quociente, PROMPT_450_650, "450_650"),
        (quociente, PROMPT_ABAIXO_450, "abaixo_450")
    ]
    return lista_tarefas_xml, lista_faixas

def obter_prompt_por_indice(indice, lista_faixas):
    total = 0
    for quantidade, prompt, nome in lista_faixas:
        if indice < total + quantidade:
            return prompt, nome
        total += quantidade
    return PROMPT_ABAIXO_450, "abaixo_450"

def separar_frases(texto):
    if not texto:
        return {}
    texto = texto.replace("\n", " ")
    frases = re.split(r'(?<=[.!?]) +', texto)
    resultado = {}
    indice = 0
    for frase in frases:
        if frase.strip():
            resultado[str(indice)] = frase.strip()
            indice += 1
    return resultado

def carregar_processados():
    if not os.path.exists(ARQUIVO_PROCESSADOS):
        return set()
    with open(ARQUIVO_PROCESSADOS, "r", encoding="utf-8") as f:
        return set(linha.strip() for linea in f if (linha := linea.strip()))

def salvar_processado(identificador_unico):
    with open(ARQUIVO_PROCESSADOS, "a", encoding="utf-8") as f:
        f.write(identificador_unico + "\n")

async def chamar_gemini_unificado(prompt_instrucao, tema, texto_comando, texto_motivadores):
    prompt_final = f"""
Atue como avaliador e gerador especialista em redações ENEM. Execute obrigatoriamente as duas etapas integradas em um único JSON estruturado.

ETAPA 1: Gerar redação sintética baseada na seguinte instrução de qualidade:
{prompt_instrucao.format(TEMA=tema)}

ETAPA 2: Mapeamento Semântico. Vincule cada frase gerada às chaves correspondentes do COMANDO (C) ou MOTIVADORES (M) fornecidos abaixo.
Critério: Vinculação existe se tratarem do mesmo evento/fato na mesma situação (mesmo com palavras diferentes).

COMANDO TEMÁTICO (C):
{texto_comando}

MOTIVADORES (M):
{texto_motivadores}

Regras Mapeamento: avalie todas as frases individualmente. Atribua IDs correspondentes em listas de strings. Use null se não houver vinculação evidente.

RETORNO OBRIGATÓRIO (JSON STRICT - SEM MARKDOWN):
{{
  "texto_completo_redacao": "Texto corrido integral da redação gerada.",
  "mapeamento_frases": [
     {{
       "frase": "Texto exato da frase gerada",
       "c": ["ID"] ou null,
       "m": ["ID"] ou null
     }}
  ]
}}
"""
    async with SEMAFORO:
        for tentativa in range(10):
            try:
                response = await client.aio.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt_final,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.7
                    ),
                )
                texto_resposta = response.text.strip()
                if texto_resposta.startswith("```"):
                    texto_resposta = re.sub(r"^```json\s*|```$", "", texto_resposta, flags=re.MULTILINE).strip()
                return json.loads(texto_resposta)
                
            except Exception as e:
                erro_msg = str(e)
                tempo_espera = 15 
                
                if "429" in erro_msg or "RESOURCE_EXHAUSTED" in erro_msg:
                    match = re.search(r"retry in ([0-9.]+)\s*s", erro_msg)
                    if match:
                        tempo_espera = int(float(match.group(1))) + 5  
                    print(f"\n[Aviso Cota] Limite atingido para o tema '{tema}'. Aguardando cota por {tempo_espera}s antes de tentar novamente...")
                else:
                    print(f"[Aviso API] Tentativa {tentativa + 1} falhou para o tema '{tema}': {e}")
                
                if tentativa < 9:
                    await asyncio.sleep(tempo_espera)
        return None

async def processar_redacao_xml(info_xml, indice_atual, lista_faixas, dados_do_tema):
    nome_xml = info_xml["nome_xml"]
    pasta_tema = info_xml["pasta_tema"]
    caminho_xml = info_xml["caminho_completo"]
    
    frases_comando = dados_do_tema.get("comando_tematico", {}).get("frases", {})
    frases_motivadores = dados_do_tema.get("textos_motivadores", {}).get("frases", {})
    
    texto_comando = "\n".join([f"{i}: {frase}" for i, frase in frases_comando.items()])
    texto_motivadores = "\n".join([f"{i}: {frase}" for i, frase in frases_motivadores.items()])
    
    prompt_escolhido, nome_faixa = obter_prompt_por_indice(indice_atual, lista_faixas)
    
    print(f"[Processando] {pasta_tema} -> {nome_xml} | Faixa: {nome_faixa}")

    redacao_original_fatiada = {}
    try:
        doc = Document(caminho_xml)
        doc.read()
        texto_original = doc.get_body()
        redacao_original_fatiada = separar_frases(texto_original)
    except Exception as e:
        print(f"[Erro XML] Falha ao processar {nome_xml}: {e}")

    resultado_llm = await chamar_gemini_unificado(prompt_escolhido, pasta_tema, texto_comando, texto_motivadores)
    
    if resultado_llm:
        try:
            lista_mapeamento = resultado_llm.get("mapeamento_frases", [])
            redacao_gerada_fatiada = {}
            mapeamento_frases_final = {}
            
            for idx, item in enumerate(lista_mapeamento):
                frase_texto = item.get("frase", "").strip()
                if frase_texto:
                    ch_idx = str(idx)
                    redacao_gerada_fatiada[ch_idx] = frase_texto
                    mapeamento_frases_final[ch_idx] = {
                        "comando_tematico": item.get("c"),
                        "textos_motivadores": item.get("m")
                    }
            
            dados_saida = {
                "tema": pasta_tema,
                "comando_tematico": dados_do_tema.get("comando_tematico", {}),
                "textos_motivadores": dados_do_tema.get("textos_motivadores", {}),
                "prompt": prompt_escolhido,
                "redacao_original": redacao_original_fatiada,
                "redacao_gerada": redacao_gerada_fatiada,
                "mapeamento_frases": mapeamento_frases_final
            }
            
            nome_saida = nome_xml.replace(".xml", "_gerado.json")
            caminho_saida = os.path.join(PASTA_SAIDA, nome_saida)
            
            with open(caminho_saida, "w", encoding="utf-8") as f:
                json.dump(dados_saida, f, ensure_ascii=False, indent=2)
                
            salvar_processado(f"{pasta_tema}/{nome_xml}")
            print(f"[Sucesso] Gravado: {nome_saida}")
            
            return True
        except Exception as e:
            print(f"[Erro Escrita] Falha no JSON final de {nome_xml}: {e}")
            return False
    else:
        print(f"[Falha Crítica] Sem resposta após retentativas para {nome_xml}")
        return False

async def main():
    print("Carregando base de dados dos temas...")
    mapa_temas = carregar_dados_dos_temas()
    
    print("Mapeando arquivos XML...")
    lista_xmls, lista_faixas_dinamicas = listar_todos_xmls_e_calcular_faixas()
    
    arquivos_processados = carregar_processados()
    
    tarefas = []
    indice_ficticio = len(arquivos_processados)
    
    for info_xml in lista_xmls:
        id_unico = f"{info_xml['pasta_tema']}/{info_xml['nome_xml']}"
        if id_unico in arquivos_processados:
            continue
            
        dados_tema_vinculado = mapa_temas.get(info_xml['pasta_tema'])
        if not dados_tema_vinculado:
            continue
            
        tarefa = asyncio.create_task(
            processar_redacao_xml(info_xml, indice_ficticio, lista_faixas_dinamicas, dados_tema_vinculado)
        )
        tarefas.append(tarefa)
        indice_ficticio += 1
        
    if tarefas:
        print(f"Iniciando processamento acelerado de {len(tarefas)} redações XML...")
        await asyncio.gather(*tarefas)
        print("\nProcessamento completo!")
    else:
        print("Todas as redações já foram processadas.")

if __name__ == "__main__":
    asyncio.run(main())
