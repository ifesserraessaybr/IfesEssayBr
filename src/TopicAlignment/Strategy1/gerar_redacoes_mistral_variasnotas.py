import os
import json
import time
import random
from datetime import datetime
import requests

# ============================================================
# CONFIGURAÇÕES - ALTERE AQUI!
# ============================================================
api_key = os.getenv("MISTRAL_API_KEY")   # <--- sua chave
PASTA_ENTRADA = r"C:\Users\AdminUser\Documents\IC\gpt4TurboOneshot"   # pasta com JSONs originais
PASTA_SAIDA   = r"C:\Users\AdminUser\Documents\IC\redacoesSinteticas"
MODELO = "open-mistral-nemo"

# Faixas de nota que serão geradas (a faixa "excelente" acima de 800 não é gerada,
# pois você já possui esses exemplos)
FAIXAS = {
    "baixa": {
        "pasta": "baixa",                # subpasta de saída
        "descricao": "uma redação que seria avaliada com nota entre 0 e 450 pontos. "
                     "Apresente MUITOS erros de gramática, ortografia, pontuação, falta de coesão, "
                     "argumentação fraca ou inexistente, fuga parcial do tema, parágrafos desconexos e "
                     "extensão muito reduzida (máximo 12 linhas). O texto deve parecer de um aluno com graves dificuldades.",
        "temperatura": 0.95
    },
    "media": {
        "pasta": "media",
        "descricao": "uma redação de nível médio, nota entre 450 e 650 pontos. "
                     "Deve ter uma estrutura básica (introdução, desenvolvimento, conclusão) com argumentos razoáveis, "
                     "mas pode conter alguns erros gramaticais leves, repetições, argumentos superficiais ou "
                     "desvios pontuais do tema. Extensão entre 18 e 25 linhas.",
        "temperatura": 0.8
    },
    "alta": {
        "pasta": "alta",
        "descricao": "uma redação de bom nível, nota entre 650 e 700 pontos. "
                     "Linguagem culta com raros deslizes, argumentação consistente, boa progressão temática, "
                     "proposta de intervenção pertinente. Extensão de 25 a 30 linhas.",
        "temperatura": 0.7
    }
    # "excelente" (acima de 800) não será gerada aqui, pois você já dispõe dessas redações.
}

# ============================================================
# Ângulos argumentativos (mantidos)
# ============================================================
ANGULOS = [
    "com ênfase no papel da educação sexual nas escolas",
    "destacando os desafios das políticas públicas de saúde",
    "discutindo o impacto do preconceito e do estigma social",
    "analisando a responsabilidade da mídia na conscientização",
    "focando na importância do acesso a preservativos e testagem",
    "explorando a influência da cultura digital na percepção de risco entre os jovens",
    "defendendo a necessidade de campanhas permanentes de prevenção"
]

# ============================================================
# Criação do prompt adaptado à faixa de nota
# ============================================================
def criar_prompt(comando, angulo, faixa_info):
    descricao = faixa_info["descricao"]
    return f"""Você é um especialista em redação do ENEM. Escreva exatamente {descricao}

Tema: {comando}
Ângulo argumentativo a ser utilizado: {angulo}

A redação deve ser dissertativo-argumentativa, em português, SEM incluir asteriscos, "tópico frasal" ou indicações de parágrafos.
Forneça apenas o texto da redação."""

# ============================================================
# Geração via API Mistral
# ============================================================
def gerar_redacao_api(comando, angulo, faixa_info):
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = criar_prompt(comando, angulo, faixa_info)
    
    payload = {
        "model": MODELO,
        "messages": [
            {"role": "system", "content": "Você é um assistente que escreve redações do ENEM com o nível de qualidade solicitado."},
            {"role": "user", "content": prompt}
        ],
        "temperature": faixa_info["temperatura"],
        "top_p": 0.9,
        "max_tokens": 2000
    }
    
    try:
        resposta = requests.post(url, json=payload, headers=headers, timeout=120)
        if resposta.status_code == 200:
            dados = resposta.json()
            return dados["choices"][0]["message"]["content"].strip()
        else:
            print(f"  ❌ Erro HTTP {resposta.status_code}: {resposta.text}")
            return "[ERRO NA API]"
    except Exception as e:
        print(f"  ❌ Exceção: {e}")
        return "[ERRO NA API]"

# ============================================================
# Extrair comando temático do JSON (mantida)
# ============================================================
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

# ============================================================
# Ler arquivos JSON
# ============================================================
def ler_jsons(diretorio):
    dados = []
    if not os.path.exists(diretorio):
        print(f"❌ Pasta não encontrada: {diretorio}")
        return dados
    for arquivo in os.listdir(diretorio):
        if not arquivo.endswith('.json'):
            continue
        caminho = os.path.join(diretorio, arquivo)
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                conteudo = json.load(f)
            dados.append({'arquivo': arquivo, 'conteudo': conteudo})
        except Exception as e:
            print(f"Erro em {arquivo}: {e}")
    return dados

# ============================================================
# Processamento principal (agora gera para todas as faixas)
# ============================================================
def processar_todos(entrada, saida):
    arquivos = ler_jsons(entrada)
    print(f"📁 Encontrados {len(arquivos)} arquivos na pasta {entrada}")
    
    if not arquivos:
        print("⚠️ Nenhum arquivo JSON encontrado. Verifique o caminho.")
        return

    for idx, item in enumerate(arquivos):
        print(f"\n[{idx+1}/{len(arquivos)}] {item['arquivo']}")
        
        comando = extrair_comando(item['conteudo'])
        if not comando:
            print("  ⚠️ Comando não encontrado. Pulando.")
            continue
        
        print(f"  Tema: {comando[:100]}...")
        
        # Para cada faixa de nota (exceto excelente)
        for chave, info in FAIXAS.items():
            pasta_faixa = os.path.join(saida, info["pasta"])
            os.makedirs(pasta_faixa, exist_ok=True)
            
            angulo = random.choice(ANGULOS)
            print(f"  🎯 Gerando faixa '{chave}' | ângulo: {angulo}")
            
            inicio = time.time()
            redacao = gerar_redacao_api(comando, angulo, info)
            tempo = time.time() - inicio
            print(f"     ⏱️ {tempo:.1f}s - {len(redacao)} caracteres")
            
            base = os.path.splitext(item['arquivo'])[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_base = f"{base}_{chave}_{timestamp}"
            
            # Salvar JSON com metadados
            with open(os.path.join(pasta_faixa, f"{nome_base}.json"), 'w', encoding='utf-8') as f:
                json.dump({
                    "original": item['arquivo'],
                    "comando": comando,
                    "angulo": angulo,
                    "faixa": chave,
                    "nota_esperada": info["descricao"][:50] + "...",
                    "redacao": redacao,
                    "modelo": MODELO,
                    "temperatura": info["temperatura"],
                    "tempo": tempo
                }, f, ensure_ascii=False, indent=2)
            
            # Salvar TXT
            with open(os.path.join(pasta_faixa, f"{nome_base}.txt"), 'w', encoding='utf-8') as f:
                f.write(redacao)
            
            print(f"     💾 Salvo em {info['pasta']}/{nome_base}.txt")
    
    print("\n✅ Todas as faixas geradas!")

# ============================================================
if __name__ == "__main__":
    processar_todos(PASTA_ENTRADA, PASTA_SAIDA)