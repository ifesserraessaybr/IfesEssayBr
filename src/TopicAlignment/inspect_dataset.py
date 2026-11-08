import json
import random
from pathlib import Path

def carregar_configuracao():  
    """
    Carrega as configurações do arquivo config.json.
    
    Returns:
        dict: Dicionário contendo as configurações carregadas.
    """
    BASE_DIR = Path(__file__).resolve().parents[2]
    ARQUIVO_CONFIG = BASE_DIR / "config.json"

    if not ARQUIVO_CONFIG.exists():
        raise FileNotFoundError(f"Erro: arquivo de configuração não encontrado em: {ARQUIVO_CONFIG}")

    with ARQUIVO_CONFIG.open("r", encoding="utf-8") as arq:
        CONFIG = json.load(arq)
    
    return CONFIG


def ler_arquivos_json_aleatorios(diretorio, quantidade=30, semente=42):
    """
    Lê aleatoriamente arquivos JSON de um diretório e retorna todos os atributos.
    
    Args:
        diretorio: Caminho do diretório contendo os arquivos JSON
        quantidade: Número de arquivos a serem lidos (padrão: 30)
        semente: Semente para reprodutibilidade (padrão: 42)
    
    Returns:
        Lista de dicionários com todos os dados dos arquivos
    """
    # Define a semente para garantir reprodutibilidade
    random.seed(semente)
    
    # Lista todos os arquivos JSON no diretório
    arquivos_json = list(Path(diretorio).glob('*.json'))
    
    if len(arquivos_json) == 0:
        print(f"ERRO: Nenhum arquivo JSON encontrado no diretório: {diretorio}")
        return []
    
    print(f"Total de arquivos JSON encontrados: {len(arquivos_json)}")
    
    if len(arquivos_json) < quantidade:
        print(f"Aviso: Apenas {len(arquivos_json)} arquivos disponíveis. Lendo todos.")
        quantidade = len(arquivos_json)
    
    # Seleciona aleatoriamente os arquivos
    arquivos_selecionados = random.sample(arquivos_json, quantidade)
    
    resultados = []
    
    # Processa cada arquivo
    for arquivo in arquivos_selecionados:
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            
            # Adiciona o nome do arquivo aos dados
            resultado = {
                'nome_arquivo': arquivo.name,
                'dados': dados
            }
            resultados.append(resultado)
            
        except json.JSONDecodeError as e:
            print(f"ERRO ao decodificar JSON em {arquivo.name}: {e}")
        except Exception as e:
            print(f"ERRO ao processar {arquivo.name}: {e}")
    
    return resultados


def imprimir_atributos(resultados, arquivo_saida='saida.txt'):
    """Imprime todos os atributos de cada arquivo no console e em arquivo."""
    
    # Abre o arquivo para escrita
    with open(arquivo_saida, 'w', encoding='utf-8') as f:
        # Cabeçalho
        cabecalho = f"\n{'='*100}\nIMPRIMINDO ATRIBUTOS DE {len(resultados)} ARQUIVOS\n{'='*100}\n"
        print(cabecalho)
        f.write(cabecalho)
        
        for i, item in enumerate(resultados, 1):
            # Título do arquivo
            titulo = f"\n{'█'*100}\nARQUIVO {i}: {item['nome_arquivo']}\n{'█'*100}\n\n"
            print(titulo)
            f.write(titulo)
            
            dados = item['dados']
            
            # Imprime cada atributo
            for chave, valor in dados.items():
                atributo_titulo = f"[{chave}]:\n"
                print(atributo_titulo, end='')
                f.write(atributo_titulo)
                
                # Imprime o valor
                valor_formatado = formatar_valor(valor, nivel=1)
                print(valor_formatado)
                f.write(valor_formatado + '\n')
                print()
                f.write('\n')
    
    print(f"\n{'='*100}")
    print(f"✓ Saída salva em: {arquivo_saida}")
    print(f"{'='*100}\n")


def formatar_valor(valor, nivel=0):
    """Formata um valor de forma recursiva e retorna como string."""
    indentacao = "  " * nivel
    linhas = []
    
    if isinstance(valor, dict):
        for k, v in valor.items():
            if isinstance(v, (dict, list)):
                linhas.append(f"{indentacao}{k}:")
                linhas.append(formatar_valor(v, nivel + 1))
            else:
                linhas.append(f"{indentacao}{k}: {v}")
    
    elif isinstance(valor, list):
        for idx, item in enumerate(valor):
            if isinstance(item, (dict, list)):
                linhas.append(f"{indentacao}[{idx}]:")
                linhas.append(formatar_valor(item, nivel + 1))
            else:
                linhas.append(f"{indentacao}[{idx}]: {item}")
    
    else:
        # Valor primitivo (string, número, boolean, null)
        linhas.append(f"{indentacao}{valor}")
    
    return '\n'.join(linhas)


def imprimir_valor(valor, nivel=0):
    """Imprime um valor de forma recursiva e formatada."""
    indentacao = "  " * nivel
    
    if isinstance(valor, dict):
        for k, v in valor.items():
            if isinstance(v, (dict, list)):
                print(f"{indentacao}{k}:")
                imprimir_valor(v, nivel + 1)
            else:
                print(f"{indentacao}{k}: {v}")
    
    elif isinstance(valor, list):
        for idx, item in enumerate(valor):
            if isinstance(item, (dict, list)):
                print(f"{indentacao}[{idx}]:")
                imprimir_valor(item, nivel + 1)
            else:
                print(f"{indentacao}[{idx}]: {item}")
    
    else:
        # Valor primitivo (string, número, boolean, null)
        print(f"{indentacao}{valor}")


def main():
    # Carrega configurações do JSON
    config = carregar_configuracao()
    if not config:
        return

    # Extrai configurações do JSON
    diretorio_entrada = config.get("inspect_dataset - in")
    arquivo_saida = config.get("inspect_dataset - out", "saida.txt")
    quantidade_arquivos = config.get('inspect_dataset - total files', 30)
    semente = config.get('inspect_dataset - seed', 42) # Altere a semente para diferentes seleções aleatórias
    
    print(f"\n{'='*100}")
    print(f"LEITOR DE ARQUIVOS JSON ALEATÓRIOS")
    print(f"{'='*100}")
    print(f"Diretório: {diretorio_entrada}")
    print(f"Quantidade: {quantidade_arquivos} arquivos")
    print(f"Semente: {semente}")
    print(f"{'='*100}\n")
    
    # Lê os arquivos
    resultados = ler_arquivos_json_aleatorios(diretorio_entrada, quantidade_arquivos, semente)
    
    if not resultados:
        print("\nNenhum arquivo foi processado.")
        return
    
    # Imprime todos os atributos (no console e em arquivo)
    imprimir_atributos(resultados, arquivo_saida)
    
    # Retorna os resultados
    return resultados


if __name__ == "__main__":
    dados = main()