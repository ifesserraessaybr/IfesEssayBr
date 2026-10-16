<div align="right">
  <a href="README.pt-br.md">🇧🇷 Português</a> | <a href="README.md">🇺🇸 English</a>
</div>

# IfesEssayBr
Repositório unificado de ferramentas em Python para avaliação automática de redações no IFES Capus Serra. Inclui módulos de diversidade e complexidade léxica, processamento de métricas linguísticas e análise de datasets com textos do ChatGPT e da base completa para estudos em PLN.

## 💾 Datasets do Projeto

Devido ao tamanho dos arquivos, os datasets do projeto estão hospedados no Google Drive e divididos por etapa de processamento.

> 📝 **Nota:** O dataset original de redações era disponibilizado em formato `.xml`. Para viabilizar os pipelines de processamento e entrada nos modelos de linguagem (LLMs), os dados foram convertidos e estruturados em formato `.json` (disponibilizados nos itens 4 a 7 abaixo).

---

### 📂 Pipeline e Resultados de Análise (Strategy 1)

1. **Mapeamento de Coerência**
   * 🔗 **[Clique aqui para baixar a Pasta 1 (Google Drive)](https://drive.google.com/file/d/1sywv1hoAXYsZch_JDWJ8r0MGJCgQPiYp/view?usp=sharing)**
   * **Caminho de destino local:**
     `dataset/TopicAlignment/Strategy1/mapping/`

2. **Redações Sintéticas Geradas**
   * 🔗 **[Clique aqui para baixar a Pasta 2 (Google Drive)](https://drive.google.com/file/d/1ECh7Ti3c9BL5gRxKcUn6s0lj1-g0vFyX/view?usp=sharing)**
   * **Caminho de destino local:**
     `dataset/TopicAlignment/Strategy1/synthetic_essays/`

3. **Resultados e Métricas**
   * 🔗 **[Clique aqui para baixar a Pasta 3 (Google Drive)](https://drive.google.com/file/d/1gpnxy5HC_hJZMeOEGqdGJ6V2MNDCmM7i/view?usp=sharing)**
   * **Caminho de destino local:**
     `dataset/TopicAlignment/Strategy1/results/`

---

### 📄 Datasets Temáticos de Entrada (JSONs Convertidos)


4. **GPT-4 Turbo**
   * 🔗 **[Clique aqui para baixar a Pasta 4 (Google Drive)](https://drive.google.com/file/d/1Cf5w2c3K124RhtFsUr8tes64zFFC0F5v/view?usp=sharing)**
   * **Caminho de destino local:**
     `dataset/TopicAlignment/json_dataset/gpt4Turbo/`

5. **GPT-4 Turbo (One-Shot)**
   * 🔗 **[Clique aqui para baixar a Pasta 5 (Google Drive)](https://drive.google.com/file/d/1tixbXh8cUeoBGYLXRCW2FocIWbC9IjCE/view?usp=sharing)**
   * **Caminho de destino local:**
     `dataset/TopicAlignment/json_dataset/gpt4TurboOneshot/`
  
6. **Qwen Max**
   * 🔗 **[Clique aqui para baixar a Pasta 6 (Google Drive)](https://drive.google.com/file/d/1okoEOPiMLWv0cWF2j_-0Jb7MX3CqqBXT/view?usp=sharing)**
   * **Caminho de destino local:**
     `dataset/TopicAlignment/json_dataset/QwenMax/`

7. **Qwen (One-Shot)**
   * 🔗 **[Clique aqui para baixar a Pasta 7 (Google Drive)](https://drive.google.com/file/d/1XfqxEERPLMz9wyivJfojx8zzmT2qKT6T/view?usp=sharing)**
   * **Caminho de destino local:**
     `dataset/TopicAlignment/json_dataset/QwenOneshot/`