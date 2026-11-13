<div align="right">
  <a href="README.pt-br.md">🇧🇷 Português</a> | <a href="README.md">🇺🇸 English</a>
</div>

# IfesEssayBr
Repositório unificado de ferramentas em Python para avaliação automática de redações no IFES Capus Serra. Inclui módulos de diversidade e complexidade léxica, processamento de métricas linguísticas e análise de datasets com textos do ChatGPT e da base completa para estudos em PLN.

## 💾 Datasets do Projeto

#### Devido ao tamanho dos arquivos, os datasets do projeto estão hospedados no Google Drive. Você pode conferir as instruções e links abaixo:

* [Pipeline e Resultados de Análise](dataset/TopicAlignment/Strategy1/README.pt-br.md)
* [Dataset em JSON](dataset/TopicAlignment/json_dataset/README.pt-br.md)

## ⚙️ Arquivo de configuração JSON

Na raiz do repositório, está o arquivo [config.json](config.json). Nele, você consegue configurar facilmente os caminhos de entrada e saída, sem precisar fazer isso manualmente nos códigos.

#### Os parâmetros do arquivo são:

* Caminho de entrada e saída do código [generate_mistral_alignment](src/TopicAlignment/Strategy1/generate_mistral_alignment.py)