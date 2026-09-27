# 📊 Análise de Textos - Diversidade e Complexidade

Ferramenta simples para analisar a qualidade e complexidade de textos em português.

## 🎯 O que faz?

Analisa textos e calcula:

- **Diversidade Léxica**: Quantas palavras diferentes são usadas
- **Complexidade**: Se o vocabulário é simples ou avançado  
- **Padrões Silábicos**: Estrutura das palavras

## 🚀 Como usar?

```python
# Basta executar o script
python Codigo_IC_diversidadeLexica.py
```

O programa vai:
1. Ler arquivos JSON da pasta configurada
2. Analisar cada texto
3. Gerar relatórios com os resultados

## 📊 Resultados

### Para cada arquivo:
```
Diversidade Léxica: 85.8%  ✅ (Quanto maior, melhor)
Complexidade: 27.4% - Média  📊
Palavras Longas: 30.0%  🔤
Sílabas por Palavra: 2.97  📝
```

### Resumo geral:
- ✅ **Diversidade Alta**: Textos com vocabulário variado
- 📊 **Complexidade Média**: Nem simples, nem complicado demais
- 🔄 **Consistente**: Resultados similares entre textos

## 📁 Arquivos necessários

Coloque os arquivos JSON na pasta:
```
C:/Users/Maxine/Downloads/IC/ChatgptTurbo/
```

Estrutura do JSON:
```json
{
  "comando_tematico": {
    "texto": "Seu texto aqui..."
  }
}
```

## 💡 Ideal para

- Analisar redações e textos
- Pesquisas em linguística  
- Comparar estilos de escrita
- Estudos sobre IA e geração de texto

---

*Ferramenta desenvolvida para análise linguística computacional*
