import pandas as pd
import re
from collections import Counter
from sklearn.model_selection import train_test_split

SEED = 100

#FUNÇÃO PARA TRANSFORMAR AS SENTENÇAS COM TAGS EM SENTENÇAS EM FORMATO BIO

def tag2bio(sentenca):
    if not isinstance(sentenca, str):
        return []

    # Remove completamente o conteúdo entre <correct>...</correct> (incluindo as tags)
    sent_temp = re.sub(r'<correct>.*?</correct>', '', sentenca, flags=re.IGNORECASE)

    tags = ["<wrong>", "</wrong>"]

    # ** Separação e armazenamento dos tokens **

    # Parte 1: Separação das tags <wrong> e </wrong>
    sent_temp2 = sent_temp
    for tag in tags:
        sent_temp2 = sent_temp2.replace(tag, " " + tag + " ")

    # Parte 2: Separação da pontuação
    sep_pont = ['.', ',', ';', ':', '?', '!', '(', ')', '[', ']', '{', '}', "'", '"']
    for pontuacao in sep_pont:
        sent_temp2 = sent_temp2.replace(pontuacao, " " + pontuacao + " ")

    # Parte 3: Guardar tokens separados
    sent_temp2 = re.sub(r'\s+', ' ', sent_temp2).strip()

    tokens = sent_temp2.split(' ')

    # ** Transformar para tag BIO **
    bio = []
    trecho_errado = False
    primeiro_erro = True

    for token in tokens:
        if token == "<wrong>":
            trecho_errado = True
            primeiro_erro = True
        elif token == "</wrong>":
            trecho_errado = False
        elif token not in tags:
            if trecho_errado:
                if primeiro_erro:
                    bio.append((token, "B-WRONG"))
                    primeiro_erro = False
                else:
                    bio.append((token, "I-WRONG"))
            else:
                bio.append((token, "O"))

    return bio


# ********** FUNÇÃO PARA VERIFICAR SE A FRASE CONTÉM ERRO **********

def contem_erro(sentenca_bio):
    for _, tag in sentenca_bio:
        if 'WRONG' in tag:
            return True
    return False


# ********** FUNÇÃO PARA LER OS ARQUIVOS TEST.TSV E TRAIN.TSV E TRANSFORMAR AS SENTENÇAS EM FORMATO BIO **********

def analisa_estratificacao(arquivo):
    try:
        df = pd.read_csv(arquivo, encoding='latin-1', sep='\t')
    except FileNotFoundError:
        print("Não foi possível ler os arquivos de treino e teste. Tente novamente.")
        return 1

    try:
        df['formato_bio_list'] = df['formato_bio'].apply(eval)
    except Exception as e:
        print(f"Erro ao converter 'formato_bio' em {arquivo}. Verifique o formato dos dados: {e}")
        return None, 0


# ********** FUNÇÃO PARA CALCULAR AS ESTATÍSTICAS DE CADA TOTAL E DE CADA TAG EM FORMATO BIO **********

def calcular_estatistica_bio(df):
    # 1. Extração das tags de cada token, usando cada conjunto de tokens e tags de cada sentença
    qtd_tags = []
    for token_tag in df['formato_bio']:
        for token, tag in token_tag:
            qtd_tags.append(tag)

    # 2. Contar as ocorrências de cada tag
    contagem_tags = Counter(qtd_tags)
    total_tokens = len(qtd_tags)

    # 3. Criar e exportar o DataFrame de cálculo
    df_calculo = pd.DataFrame({
        'Tipo': ['Total de Tokens', 'Tokens B-WRONG', 'Tokens I-WRONG', 'Tokens O'],
        'Quantidade': [
            total_tokens,
            contagem_tags.get('B-WRONG', 0),
            contagem_tags.get('I-WRONG', 0),
            contagem_tags.get('O', 0)]
    })

    return df_calculo


# ********** FUNÇÃO PARA ESTRUTURAR OS ARQUIVOS TRAIN E TEST BIO **********

def file_bio(df, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        # df.reset_index() para que 'index' seja numérica
        df_reset = df.reset_index()
        for index, row in df_reset.iterrows():
            sentenca_original = row['Texto']
            # O 'formato_bio' é uma string, precisamos convertê-la de volta para uma lista de tuplas.
            formato_bio = eval(row['formato_bio'])

            # Escreve o cabeçalho da sentença
            f.write(f"Sentença Original N°{index + 1}\n")  # index + 1 para começar em 1

            # Escreve cada token e sua tag, separados por tabulação (\t)
            for token, tag in formato_bio:
                f.write(f"{token}\t{tag}\n")

            f.write("\n")  # Linha em branco para separar as sentenças


def main():
    # Leitura do arquivo CSV (TSV), com suporte de acentuação
    try:
        leitura = pd.read_csv('resultado_extrair_sentenca_erro_semerro.tsv', encoding='latin-1', sep='\t')
    except FileNotFoundError:
        print("Erro na leitura do arquivo 'resultado_extrair_sentenca_erro_semerro.tsv'.")
        return

    # Aplica a transformação BIO em todas as linhas
    leitura['formato_bio'] = leitura['Texto'].apply(tag2bio)

    # Coluna temporária p/ identificar duplicações
    leitura['formato_bio_str'] = leitura['formato_bio'].astype(str)

    # Criação de um Dataframe com sentenças não repetidas
    df_unico = leitura[['Texto', 'formato_bio', 'formato_bio_str']].drop_duplicates(
        subset=['Texto', 'formato_bio_str']
    ).drop(columns=['formato_bio_str']).reset_index(drop=True)

    # ********** Cálculo da quantidade total de tags e dos tokens B, I e O. **********

    df_calculo = calcular_estatistica_bio(df_unico)

    estatistica_tokens = 'estatistica_tokens.tsv'
    df_calculo.to_csv(estatistica_tokens, sep='\t', index=False, encoding='utf-8')

    print(f"\n*** ESTATÍSTICA DOS DADOS ***")
    print(df_calculo)

    # ********** ESTRATIFICAÇÃO DOS DADOS **********
    # 1. Cria a coluna dos rótulos BIO
    df_unico['contem_erro'] = df_unico['formato_bio'].apply(contem_erro)

    # 2. Faz a divisão nos DataFrames (df_unico), com 80% do arquivo de treino e 20% de teste
    df_temp_train, df_test = train_test_split(
        df_unico,
        test_size=0.2,
        random_state=SEED,
        stratify=df_unico['contem_erro']
    )

    # 3. Divisão do arquivo de treino em 90% para treino e 10% para validação
    df_train, df_val = train_test_split(
        df_temp_train,
        test_size=0.10,
        random_state=SEED,
        stratify=df_temp_train['contem_erro']
    )

    # 1. Tamanho dos conjuntos de dados (número de frases)
    print(f"\nTotal de frases: {len(df_unico)}")
    print(f"Frases para teste (20%): {len(df_test)}")
    print(f"Frases para treinamento (90% do conjunto de treino): {len(df_train)}")
    print(f"Frases para validação (10% do conjunto de treino): {len(df_val)}")

    # Criação dos arquivos BIO (treino, validação e teste)
    df_train['formato_bio'] = df_train['formato_bio'].astype(str)
    file_bio(df_train, 'train_bio.tsv')

    df_val['formato_bio'] = df_val['formato_bio'].astype(str)
    file_bio(df_val, 'val_bio.tsv')

    df_test['formato_bio'] = df_test['formato_bio'].astype(str)
    file_bio(df_test, 'test_bio.tsv')

    print("\nOs arquivos BIO de treino, teste e validação foram gerados com sucesso!")


if __name__ == "__main__":
    main()
