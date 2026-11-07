"""Regras de identificacao e pontuacao (fonte unica de verdade).

Todas as expressoes operam sobre texto normalizado: MAIUSCULO e SEM ACENTO.
Ajuste aqui e documente a mudanca em references/regras-classificacao.md.
"""
from __future__ import annotations

# Termos FORTES: sozinhos ja indicam operacao de protecao veicular/patrimonial mutualista.
FORTE_VEICULAR = [
    r"PROTECAO VEICULAR", r"PROTECAO VEICULOS?", r"PROTECAO AUTOMOTIVA", r"PROTECAO AUTOMOTOR",
    r"PROTECAO DE VEICULOS", r"PROTECAO AO VEICULO", r"PROTECAO DE AUTOMOVEIS", r"PROTECAO DE MOTOS?",
    r"PROTECAO DE MOTOCICLETAS", r"PROTECAO DE CAMINHOES", r"PROTECAO DE CARGAS?",
    r"PROTECAO AUTO\b", r"AUTO PROTECAO", r"AUTOPROTECAO", r"MOTO PROTECAO", r"CAR PROTECAO",
    r"PROTECAO E ASSISTENCIA VEICULAR", r"ASSISTENCIA VEICULAR", r"BENEFICIOS? VEICULAR",
    # forma generica: "protecao a veiculos", "protecao para seu carro", "protecao dos automoveis"...
    r"PROTECAO (A |AO |AOS |DE |DO |DOS |DAS |PARA )?(SEUS? |SUAS? )?(VEICUL|AUTOMOV|AUTOMOTOR|MOTOS?\b|MOTOCICLET|CAMINH|CARROS?\b|FROTA)",
]
# Termos de CATEGORIA: associacoes de proprietarios/condutores. Pesam, mas nao bastam para classe 2.
FORTE_CATEGORIA = [
    r"PROPRIETARIOS DE (VEICULOS|AUTOMOVEIS|MOTOS|MOTOCICLETAS|CAMINHOES|CARROS)",
    r"CONDUTORES DE VEICULOS", r"PROTECAO (DE |DOS |AOS )?(MOTOCICLISTAS|CAMINHONEIROS|MOTORISTAS|CONDUTORES)",
]
FORTE_PATRIMONIAL = [
    r"PROTECAO PATRIMONIAL", r"MUTUALISTA", r"MUTUALISMO", r"SOCORROS? MUTUOS?", r"BENEFICIOS MUTUOS",
    r"AJUDA MUTUA", r"AUXILIO MUTUO", r"AUTOGESTAO", r"PROTECAO MUTUA",
    r"(GESTAO|RATEIO) DE DESPESAS", r"DESPESAS DE VEICULOS", r"RATEIO DE PREJUIZOS",
]
# Termos MEDIOS: precisam de reforco (CNAE associativo, natureza associacao, outro termo).
# Indicio de PROTECAO/BENEFICIO (necessario para ficar como "pendente" em vez de "fora do escopo")
INDICIO_PROTECAO = [
    r"CLUBE DE BENEFICIOS", r"CLUBE DO ASSOCIADO", r"ASSOCIACAO DE BENEFICIOS", r"BENEFICIOS AO ASSOCIADO",
    r"\bBENEFICIOS\b", r"PROTECAO\b", r"\bPROTEGE", r"\bPROTEC\b", r"SEGURANCA VEICULAR", r"RASTREAMENTO",
    r"ASSISTENCIA 24", r"\bAPV\b", r"SEGUROS? (AUTO|VEICULAR|DE VEICULOS)",
]
# Termos de CONTEXTO veicular (so reforcam)
CONTEXTO_VEICULAR = [
    r"CAMINHONEIROS?", r"TRANSPORTADORES", r"MOTORISTAS", r"MOTOCICLISTAS", r"MOTOTAXISTAS?",
    r"MOTOBOYS?", r"TAXISTAS?", r"CONDUTORES", r"FROTISTAS?", r"\bVEICULOS?\b", r"AUTOMOTIV",
    r"\bAUTOMOVEIS\b", r"\bAUTO\b", r"\bCAR\b", r"\bMOTOS?\b",
]
MEDIO = INDICIO_PROTECAO + CONTEXTO_VEICULAR
COMBO_PROTECAO = [r"\bPROT", r"PROTEC", r"PROTEG", r"\bBENEFICIOS?\b", r"MUTU"]
COMBO_VEICULO = [r"VEICUL", r"AUTOMOV", r"AUTOMOTOR", r"\bAUTO\b", r"\bMOTOS?\b", r"CAMINH", r"\bCARGAS?\b",
                 r"TRANSPORTADORES", r"\bCARROS?\b", r"\bTRUCK", r"FROTA",
                 r"\bAUTO(?!GESTAO|NOM|R\b|RES\b|RIDADE)", r"CAR\b", r"\bMOTO"]  # Python re (nao usado em SQL)
# Termos NEGATIVOS: indicam fora do escopo (salvo se houver termo FORTE_VEICULAR).
NEGATIVO = [
    r"PROTECAO (AOS? |DOS? |DAS? )?ANIMA", r"PROTECAO AMBIENTAL", r"MEIO AMBIENTE", r"PROTECAO A NATUREZA",
    r"PROTECAO (A |DA |DE )?(CRIANCA|INFANCIA|ADOLESCENTE|IDOSO|MULHER|FAMILIA|MATERNIDADE|VIDA)",
    r"PROTECAO SOCIAL", r"DEFESA CIVIL", r"PROTECAO E DEFESA DO CONSUMIDOR", r"BOMBEIRO",
    r"SINDICATO", r"\bIGREJA\b", r"MINISTERIO EVANGEL", r"CONDOMINIO", r"MOTO ?CLUBE", r"MOTOCLUBE",
    r"FUTEBOL", r"ESPORTE", r"\bTIRO\b", r"CAPOEIRA", r"MORADORES", r"PAIS E MESTRES", r"APAE",
    r"ESCOLA", r"COLEGIO", r"CULTURAL", r"QUILOMBO", r"INDIGENA", r"PRODUTORES RURAIS", r"AGRICULTORES",
    r"APICULTORES", r"PESCADORES", r"ARTESAOS", r"CATADORES", r"PROTECAO RADIOLOGICA", r"PROTECAO DE DADOS",
    r"PROTECAO CATODICA", r"PROTECAO CONTRA INCENDIO", r"EQUIPAMENTOS? DE PROTECAO", r"\bEPI\b",
    r"PROTECAO DE PLANTAS", r"PROTECAO VEGETAL", r"PROTECAO E SEGURANCA DO TRABALHO",
    r"VIGILANCIA", r"SEGURANCA PRIVADA", r"PROTECAO AO CREDITO", r"PROTECAO SOLAR",
    r"\bANIMA(L|IS)\b", r"BEM.ESTAR ANIMAL", r"PATINHAS", r"\bPET\b", r"VITIMAS", r"VEICULOS ANTIGOS",
    r"CARROS ANTIGOS", r"AUTOMOVEIS ANTIGOS", r"FORMACAO DE CONDUTORES", r"AUTO ?ESCOLA", r"SAUDE SUPLEMENTAR",
    r"FUNDOS? DE PENSAO", r"PREVIDENCIA", r"SERVIDORES", r"MILITARES", r"POLICIAIS", r"APOSENTADOS",
    r"FUNERA", r"PECULIO", r"\bTRACAO ANIMAL\b", r"CEMITERIO", r"MOTOGRUPO", r"MOTOCICLISMO", r"TRILHEIROS",
    r"JIPEIROS", r"OFF ?ROAD", r"\bRALLY\b", r"ORFAOS", r"\bSAUDE\b", r"HOSPITAL", r"DEFICIENTES?",
    r"DEPENDENTES QUIMICOS", r"CONDENADOS", r"\bAPAC\b", r"ADOLESCENTE", r"FLORESTA", r"PATRIMONIO PUBLICO",
    r"CRISTA", r"RECUPERANDOS", r"VULNERAVE", r"INFANCIA", r"AMBIENTAL", r"LOTEAMENTO", r"\bVALE DO\b",
    r"FUNCIONARIOS", r"HABITACIONA", r"\bRURAL\b", r"\bRIO\b", r"\bAGUAS\b", r"BIODIVERSIDADE", r"\bPETS\b", r"PROPRIEDADE INTELECTUAL",
    r"CRIMES", r"PLANETA VERDE", r"INCENDIO", r"SUSTENTAV", r"\bRIO [A-Z]+\b$", r"\bDRONES?\b", r"\bENERGIA\b", r"PRESOS", r"EGRESSOS", r"PATRIMONIO (HISTORICO|CULTURAL)", r"MANANCIA", r"NASCENTES", r"\bRIOS?\b DE ",
]

# CNAEs (7 digitos). O 9499500 e ponto de partida, nao classificador.
CNAE_ASSOCIATIVO = {"9499500"}
CNAE_RELACIONADOS = {
    "6520100": "Seguros nao-vida (declaracao comum em APVs)",
    "6629100": "Atividades auxiliares de seguros",
    "6622300": "Corretores e agentes de seguros",
    "5229002": "Servicos de reboque de veiculos",
    "8020001": "Monitoramento de sistemas de seguranca / rastreamento",
    "4520001": "Manutencao mecanica de veiculos",
    "7490104": "Intermediacao e agenciamento de servicos",
    "9430800": "Atividades associativas de defesa de direitos sociais",
    "9412099": "Outras atividades associativas profissionais",
    "8299799": "Outras atividades de servicos prestados a empresas",
}

NATUREZA_ASSOCIACAO = {"3999": "Associacao Privada"}
NATUREZA_COOPERATIVA = {"2143": "Cooperativa", "2330": "Cooperativas de Consumo"}

# Pesos do score de confianca (0-100). Documentados em references/regras-classificacao.md
PESOS = {
    "forte_veicular": 45,
    "forte_patrimonial": 35,
    "forte_categoria": 25,
    "combinacao_protecao_veiculo": 25,  # PROTECAO/PROTEGE/BENEFICIO + VEICULO/AUTO/MOTO/CARGA no mesmo nome
    "medio": 10,            # por termo, maximo 2 termos
    "cnae_principal_9499": 15,
    "cnae_secundario_9499": 8,
    "cnae_relacionado": 7,  # maximo 1
    "natureza_associacao": 15,
    "email_termo_setor": 5,
    "negativo": -60,
    "cooperativa": -20,     # cooperativa nao e associacao PPM (LC 213/2025); fica para revisao
    "nao_associacao": -25,  # sociedade empresaria: possivel administradora/consultoria/corretora
}

# Evidencias externas que elevam/ajustam a classificacao (aplicadas em normalizar_dados.py)
EXTERNO = {
    "site_confirma_setor": 25,     # site oficial (vinculado ao CNPJ) descreve protecao veicular
    "site_confirma_cnpj": 10,      # site cita o CNPJ ou a razao social
    "susep_cadastrada": 30,        # certidao/consulta SUSEP oficial confirma cadastro
}

# Sinais comerciais procurados no site institucional (somente quando o site esta vinculado ao CNPJ)
SINAIS_SITE = {
    "protecao_veicular": [r"PROTECAO VEICULAR", r"PROTECAO AUTOMOTIVA", r"PROTECAO (DO |DE |PARA )?(SEU )?(VEICULO|CARRO|MOTO|CAMINHAO)",
                          r"COTACAO (DO |DE )?(SEU )?(VEICULO|CARRO|MOTO)", r"TABELA FIPE", r"\bFIPE\b"],
    "protecao_patrimonial": [r"PROTECAO PATRIMONIAL", r"MUTUALIS", r"SOCORRO MUTUO", r"RATEIO"],
    "assistencia_24h": [r"ASSISTENCIA 24", r"24 ?HORAS", r"GUINCHO", r"REBOQUE"],
    "vistoria": [r"VISTORIA"],
    "sinistro": [r"SINISTRO", r"COMUNICAR? (UM |O )?EVENTO", r"ACIONAMENTO", r"INDENIZA"],
    "oficinas": [r"OFICINAS? (CREDENCIADAS?|PARCEIRAS?|REFERENCIADAS?)", r"REDE CREDENCIADA", r"PRESTADORES"],
    "rastreamento": [r"RASTREAMENTO", r"RASTREADOR"],
    "area_associado": [r"AREA DO ASSOCIADO", r"PORTAL DO ASSOCIADO", r"APP DO ASSOCIADO", r"BAIXE (O|NOSSO) APP",
                       r"2A VIA (DO |DE )?BOLETO", r"SEGUNDA VIA"],
}
# Indicios de software de gestao (aparecem em links/scripts do site). So registrar; nao inferir contrato.
SOFTWARE_HINTS = {
    "hinova": r"HINOVA", "sga": r"SGA ?(WEB|HINOVA)|SGAWEB", "ileva": r"\bILEVA\b", "powercrm": r"POWER ?CRM",
    "voxel": r"VOXEL", "infocar": r"INFOCAR", "segsoft": r"SEGSOFT", "aditivo": r"\bADITIVO ?(APP|SISTEMA)",
    "wordpress": r"WP-CONTENT", "wix": r"WIXSTATIC|WIX\.COM", "rd_station": r"RDSTATION|RD STATION",
}

FREE_MAIL = {"GMAIL.COM", "HOTMAIL.COM", "OUTLOOK.COM", "YAHOO.COM", "YAHOO.COM.BR", "BOL.COM.BR", "UOL.COM.BR",
             "TERRA.COM.BR", "IG.COM.BR", "LIVE.COM", "ICLOUD.COM", "GLOBO.COM", "R7.COM", "MSN.COM",
             "HOTMAIL.COM.BR", "OUTLOOK.COM.BR", "GMAIL.COM.BR", "ZIPMAIL.COM.BR", "OI.COM.BR", "YMAIL.COM"}

CLASSES = {
    1: "Confirmada como atuante em protecao veicular",
    2: "Provavel associacao de protecao veicular",
    3: "Associacao de protecao patrimonial sem confirmacao do segmento veicular",
    4: "Entidade fora do escopo",
    5: "Pendente de verificacao",
}

SUSEP_STATUS = {
    "nao_verificado": "Nao verificado (consulta oficial ainda nao realizada)",
    "cadastrada_em_regularizacao": "Cadastrada na SUSEP, status 'Em regularizacao' (evidencia oficial)",
    "regular": "Regular perante a SUSEP (evidencia oficial explicita)",
    "nao_consta_oficial": "Certidao/consulta oficial informa que NAO consta cadastro (requer analise juridica)",
    "nao_foi_possivel": "Nao foi possivel verificar (fonte indisponivel/ambigua)",
}


def regex_any(termos: list[str]) -> str:
    return "(" + "|".join(termos) + ")"
