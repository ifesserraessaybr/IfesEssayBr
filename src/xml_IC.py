from pathlib import Path
import xml.etree.ElementTree as ET

pasta_principal = Path("WSR")

descricoes = [
    "Demonstrar domínio da norma culta da língua escrita.",
    "Compreender a proposta da redação e aplicar conceito das várias áreas de conhecimento para desenvolver o tema, dentro dos limites estruturais do texto dissertativo-argumentativo.",
    "Selecionar, relacionar, organizar e interpretar informações, fatos, opiniões e argumentos em defesa de um ponto de vista.",
    "Demonstrar conhecimento dos mecanismos linguísticos necessários para a construção da argumentação.",
    "Elaborar a proposta de solução para o problema abordado, mostrando respeito aos valores humanos e considerando a diversidade sociocultural."
]


def gerar_xml(arquivo):
    caminho_xml = arquivo.with_suffix(".xml")

    if not caminho_xml.exists():
        texto = arquivo.read_text(encoding="utf-8-sig")

        if not texto.strip():
            print(f"Arquivo vazio: {arquivo}")
            return

        essay = ET.Element("essay")
        skills = ET.SubElement(essay, "skills")

        for descricao in descricoes:
            skill = ET.SubElement(skills, "skill")
            ET.SubElement(skill, "desc").text = descricao
            ET.SubElement(skill, "grade")

        ET.SubElement(essay, "finalgrade")
        ET.SubElement(essay, "title")
        ET.SubElement(essay, "body").text = texto
        ET.SubElement(essay, "generalcomment")

        specificaspects = ET.SubElement(essay, "specificaspects")

        for numero in range(1, 6):
            competencia = ET.SubElement(
                specificaspects, f"competencia{numero}"
            )
            ET.SubElement(competencia, "generalcomment")

        arvore = ET.ElementTree(essay)
        ET.indent(arvore, space="    ")

        arvore.write(
            caminho_xml,
            encoding="utf-8",
            xml_declaration=True
        )

        print(f"gerado: {caminho_xml}")


if pasta_principal.is_dir():
    for arquivo in pasta_principal.rglob("*.txt"):
        gerar_xml(arquivo)
else:
    print("não encontrada")
