<div align="right">
  <a href="README.pt-br.md">🇧🇷 Português</a> | <a href="README.md">🇺🇸 English</a>
</div>

# IfesEssayBr

Repositório unificado de ferramentas em Python para avaliação automática de redações desenvolvido no **IFES Campus Serra**. O projeto reúne módulos de diversidade e complexidade léxica, cálculo de métricas linguísticas, geração sintética via LLMs e análise de alinhamento temático para estudos em Processamento de Linguagem Natural (PLN).

---

## 🛠️ Instalação e Configuração

1. **Clone o repositório:**
   ```bash
   git clone [https://github.com/ifesserraessaybr/IfesEssayBr.git](https://github.com/ifesserraessaybr/IfesEssayBr.git)
   cd IfesEssayBr
   ```

2. **Crie um ambiente virtual e instale as dependências:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # No Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure as variáveis de ambiente:**
   Crie o arquivo `.env` na raiz do projeto e preencha suas chaves de API (como `GEMINI_API_KEY` e `HF_TOKEN`).

---

## 💾 Datasets do Projeto

Devido ao volume de dados, os datasets estão hospedados externamente no Google Drive. Acesse a documentação específica de cada etapa para obter os links e instruções de estruturação:

- **[Pipeline e Resultados de Análise (Strategy 1)](dataset/TopicAlignment/Strategy1/README.pt-br.md):** Redações sintéticas, alinhamentos e resultados gerados pelos modelos.
- **[Dataset Base em JSON](dataset/TopicAlignment/json_dataset/README.pt-br.md):** Base estruturada contendo os temas, comandos temáticos e textos motivadores originais.

---

## ⚙️ Arquivo de Configuração (`config.json`)

Na raiz do repositório encontra-se o arquivo [`config.json`](config.json), responsável por centralizar os diretórios de entrada, saída e hiperparâmetros dos experimentos, evitando alterações manuais diretamente no código-fonte.

### Parâmetros Disponíveis

| Script Relacionado | Chave no `config.json` | Descrição |
| :--- | :--- | :--- |
| [`generate_mistral_essays.py`](src/TopicAlignment/Strategy1/generate_mistral_essays.py) | `"generate_mistral_essays - in"` | Diretório com os JSONs originais de entrada para geração. |
| [`generate_mistral_essays.py`](src/TopicAlignment/Strategy1/generate_mistral_essays.py) | `"generate_mistral_essays - out"` | Diretório de destino das redações sintéticas geradas. |
| [`generate_mistral_alignment.py`](src/TopicAlignment/Strategy1/generate_mistral_alignment.py) | `"generate_mistral_alignment - in"` | Diretório de entrada contendo as redações sintéticas. |
| [`generate_mistral_alignment.py`](src/TopicAlignment/Strategy1/generate_mistral_alignment.py) | `"generate_mistral_alignment - out"` | Diretório de destino para salvar os alinhamentos gerados. |
| [`generate_mistral_metrics.py`](src/TopicAlignment/Strategy1/generate_mistral_metrics.py) | `"generate_mistral_metrics - grounded"` | Diretório de referência com as redações originais (base). |
| [`generate_mistral_metrics.py`](src/TopicAlignment/Strategy1/generate_mistral_metrics.py) | `"generate_mistral_metrics - synthetic_essays"` | Diretório contendo as redações sintéticas a serem avaliadas. |
| [`generate_mistral_metrics.py`](src/TopicAlignment/Strategy1/generate_mistral_metrics.py) | `"generate_mistral_metrics - results"` | Diretório de saída para os relatórios estatísticos e métricas. |
| [`inspect_dataset.py`](src/TopicAlignment/json_dataset/inspect_dataset.py) | `"inspect_dataset - in"` | Diretório com os arquivos JSON do dataset a ser inspecionado. |
| [`inspect_dataset.py`](src/TopicAlignment/json_dataset/inspect_dataset.py) | `"inspect_dataset - out"` | Caminho completo do arquivo `.txt` de relatório de auditoria. |
| [`inspect_dataset.py`](src/TopicAlignment/json_dataset/inspect_dataset.py) | `"inspect_dataset - total files"` | Quantidade de arquivos analisados na amostragem. |
| [`inspect_dataset.py`](src/TopicAlignment/json_dataset/inspect_dataset.py) | `"inspect_dataset - seed"` | Semente aleatória para reprodutibilidade da leitura. |

#### Exemplo de estrutura do `config.json`:
```json
{
    "generate_mistral_alignment - in": "dataset/TopicAlignment/Strategy1/synthetic_essays/mistral_essays",
    "generate_mistral_alignment - out": "dataset/TopicAlignment/Strategy1/mapping/mistral_mapping",

    "generate_mistral_essays - in": "dataset/TopicAlignment/json_dataset/gpt4TurboOneshot",
    "generate_mistral_essays - out": "dataset/TopicAlignment/Strategy1/synthetic_essays/mistral_essays",

    "generate_mistral_metrics - grounded": "dataset/TopicAlignment/json_dataset/gpt4TurboOneshot",
    "generate_mistral_metrics - synthetic_essays": "dataset/TopicAlignment/Strategy1/synthetic_essays/mistral_essays",
    "generate_mistral_metrics - results": "dataset/TopicAlignment/Strategy1/results/mistral_evaluations",

    "inspect_dataset - in": "dataset/TopicAlignment/json_dataset/QwenOneshot",
    "inspect_dataset - out": "dataset/TopicAlignment/json_dataset/dataset_inspection/QwenOneshot.txt",
    "inspect_dataset - total files": 285,
    "inspect_dataset - seed": 42
}
```