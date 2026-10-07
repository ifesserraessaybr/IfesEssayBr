from google.colab import drive, userdata
import os
import re
import gc
import time
import random
import json
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from datetime import datetime

# ---------------------------------- CONFIGURAÇÃO INICIAL ----------------------------------
drive.mount('/content/drive')

# Pegar token do Hugging Face (crie um secret chamado HF_TOKEN no painel lateral)
HF_TOKEN = userdata.get('HF_TOKEN')

# Verifica GPU
assert torch.cuda.is_available(), "❌ GPU não detectada! Vá em Ambiente de execução > Alterar tipo e selecione T4 GPU."
print(f"✅ GPU: {torch.cuda.get_device_name(0)}")

# Modelo 14B
MODEL_NAME = "Qwen/Qwen2.5-14B-Instruct"

print("Carregando tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True, token=HF_TOKEN)
tokenizer.pad_token = tokenizer.eos_token

# Configuração 4-bit para caber na T4
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,
    dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True,
    token=HF_TOKEN,
)
model.eval()
print("✅ Modelo carregado!")

# ---------------------------------- FUNÇÕES AUXILIARES ----------------------------------
def set_seed(seed=None):
    if seed is None:
        seed = random.randint(0, 2**32 - 1)
    random.seed(seed)
    np.random.seed(seed % 2**32)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

# Níveis de nota
NIVEL_PROMPT = {
    "baixo": {
        "descricao": "nota abaixo de 450 pontos",
        "instrucao": """Você é um estudante com grandes dificuldades em redação.
Escreva uma redação dissertativo-argumentativa sobre o tema indicado, cometendo muitos erros:
- erros frequentes de ortografia, concordância, regência e pontuação;
- vocabulário limitado e informal;
- argumentação confusa, com contradições e fugas parciais do tema;
- estrutura textual muito deficiente (parágrafos mal divididos, ausência de introdução/conclusão claras);
- desrespeito à norma culta da língua portuguesa;
- extensão inferior a 15 linhas ou muito superior, sem controle.
Produza um texto que nitidamente receberia nota baixa (abaixo de 450) no ENEM."""
    },
    "medio": {
        "descricao": "nota entre 450 e 650 pontos",
        "instrucao": """Você é um estudante de desempenho mediano em redação.
Escreva uma redação dissertativo-argumentativa razoável sobre o tema indicado:
- apresente alguns erros gramaticais ou de pontuação, mas sem comprometer totalmente a compreensão;
- utilize vocabulário simples e alguns chavões;
- argumentação previsível, mas ainda dentro do tema;
- estrutura básica (introdução, desenvolvimento e conclusão), embora com pequenas falhas de coesão;
- a redação deve aparentar uma nota entre 450 e 650 pontos."""
    },
    "alto": {
        "descricao": "nota entre 650 e 700 pontos",
        "instrucao": """Você é um estudante com boa proficiência em redação.
Escreva uma redação dissertativo-argumentativa de qualidade sobre o tema indicado:
- bom domínio da norma culta, com poucos desvios;
- repertório sociocultural pertinente (citações, alusões históricas, dados);
- argumentação consistente e bem organizada;
- proposta de intervenção clara, ainda que genérica;
- o texto deve refletir uma nota entre 650 e 700 pontos (acima da média, mas não excepcional)."""
    },
    "excelente": {
        "descricao": "nota acima de 800 pontos",
        "instrucao": """Você é um estudante excelente, candidato à nota 1000 no ENEM.
Escreva uma redação dissertativo-argumentativa impecável sobre o tema indicado:
- domínio absoluto da norma culta, sem nenhum erro;
- repertório sociocultural sofisticado e produtivo (autores, obras, fatos históricos, legislação);
- argumentação sólida, com progressão temática impecável;
- proposta de intervenção detalhada, com agente, ação, meio e finalidade;
- o texto deve ser digno de uma nota acima de 800 pontos."""
    }
}

def extrair_comando(conteudo):
    for chave in ['comandoTematicoOriginal', 'comando_tematico']:
        if chave in conteudo:
            valor = conteudo[chave]
            if isinstance(valor, dict):
                texto = ' '.join(valor.values())
                if len(texto) > 10:
                    return texto
            if isinstance(valor, str) and len(valor) > 10:
                return valor
    if 'titulo' in conteudo and isinstance(conteudo['titulo'], str) and len(conteudo['titulo']) > 10:
        return conteudo['titulo']
    for k, v in conteudo.items():
        if isinstance(v, str) and len(v) > 20 and k != 'prompt':
            return v
    return None

def gerar_redacao(comando, nivel, max_new_tokens=900):
    if nivel not in NIVEL_PROMPT:
        raise ValueError("Nível inválido")
    temp_map = {"baixo": 0.9, "medio": 0.8, "alto": 0.7, "excelente": 0.6}
    temperature = temp_map[nivel]
    set_seed()

    instrucao = NIVEL_PROMPT[nivel]["instrucao"]
    prompt = f"""{instrucao}

Tema: {comando}

Escreva a redação completa, em português, sem incluir indicações como "tópico frasal", "Introdução:" ou asteriscos. Apenas o texto da redação."""

    messages = [{"role": "user", "content": prompt}]
    full_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(full_prompt, return_tensors="pt", truncation=True, max_length=4096).to("cuda")

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=True,
            top_p=0.9,
            repetition_penalty=1.2,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    generated = outputs[0][inputs["input_ids"].shape[1]:]
    redacao = tokenizer.decode(generated, skip_special_tokens=True).strip()
    redacao = re.sub(r'[^\x00-\x7FáàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇ.,;:!?\-\s\n]', '', redacao)
    if not redacao or len(redacao) < 50:
        redacao = "[ERRO de geração]"
    return redacao

# ---------------------------------- CAMINHOS E LEITURA DOS ARQUIVOS ----------------------------------
PASTA_ENTRADA = "/content/drive/MyDrive/IC/gpt4TurboOneshot"          # pasta com os JSONs dos temas
PASTA_SAIDA   = "/content/drive/MyDrive/IC/redacoesSinteticas_variadas"  # destino das redações

# Cria as subpastas de saída
for nivel in NIVEL_PROMPT.keys():
    os.makedirs(os.path.join(PASTA_SAIDA, nivel), exist_ok=True)

# Lista os arquivos JSON
arquivos = []
for nome in os.listdir(PASTA_ENTRADA):
    if nome.endswith('.json'):
        caminho = os.path.join(PASTA_ENTRADA, nome)
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                conteudo = json.load(f)
            # CORREÇÃO: era 'conteuado', agora é 'conteudo'
            arquivos.append({'arquivo': nome, 'conteudo': conteudo})
        except json.JSONDecodeError as e:
            print(f"⚠️ Arquivo ignorado (JSON inválido): {nome} → {e}")
        except Exception as e:
            print(f"⚠️ Erro ao ler {nome}: {e}")

print(f"📂 {len(arquivos)} arquivos válidos encontrados.\n")

# ---------------------------------- LOOP PRINCIPAL (COMEÇANDO DO 54º) ----------------------------------
# Define o índice de corte (53 primeiros já foram gerados)
INICIO = 53

for idx, item in enumerate(arquivos[INICIO:], start=INICIO):
    print(f"[{idx+1}/{len(arquivos)}] Tema: {item['arquivo']}")
    comando = extrair_comando(item['conteudo'])
    if not comando:
        print("  ⚠️ Comando não encontrado. Pulando.")
        continue

    print(f"  Comando (150 chars): {comando[:150]}...")

    for nivel in NIVEL_PROMPT.keys():
        print(f"    → gerando nível '{nivel}' ...", end=" ")
        inicio = time.time()
        redacao = gerar_redacao(comando, nivel)
        tempo = time.time() - inicio
        print(f"{len(redacao)} caracteres em {tempo:.1f}s")

        base = os.path.splitext(item['arquivo'])[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_base = f"{base}_{nivel}_{timestamp}"
        pasta_nivel = os.path.join(PASTA_SAIDA, nivel)

        with open(os.path.join(pasta_nivel, f"{nome_base}.json"), 'w', encoding='utf-8') as f:
            json.dump({
                "original": item['arquivo'],
                "comando": comando,
                "nivel": nivel,
                "nota_simulada": NIVEL_PROMPT[nivel]["descricao"],
                "redacao": redacao,
                "modelo": MODEL_NAME,
                "tempo": tempo
            }, f, ensure_ascii=False, indent=2)

        with open(os.path.join(pasta_nivel, f"{nome_base}.txt"), 'w', encoding='utf-8') as f:
            f.write(redacao)

    # Libera memória após cada tema
    gc.collect()
    torch.cuda.empty_cache()

print("\n✅ Todas as redações restantes foram geradas e organizadas por nível!")