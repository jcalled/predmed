
"""
Configuração das Macrorregiões e Regiões de Saúde do Ceará
Baseado na estrutura da SESA
"""

# Mapeamento: Região de Saúde (ADS) -> Macrorregião
MACRO_POR_REGIAO = {
    # Macro Fortaleza (Central)
    "CIR Fortaleza": "MACRO_FORTALEZA",
    "CIR Caucaia": "MACRO_FORTALEZA",
    "CIR Maracanaú": "MACRO_FORTALEZA",
    "CIR Baturité": "MACRO_FORTALEZA",
    "CIR Cascavel": "MACRO_FORTALEZA",  # Beberibe/Cascavel
    "CIR Beberibe": "MACRO_FORTALEZA",
    
    # Macro Sobral (Norte)
    "CIR Sobral": "MACRO_SOBRAL",
    "CIR Acaraú": "MACRO_SOBRAL",
    "CIR Tianguá": "MACRO_SOBRAL",
    "CIR Camocim": "MACRO_SOBRAL",
    "CIR Canindé": "MACRO_SOBRAL",
    "CIR Tauá": "MACRO_SOBRAL",
    
    # Macro Sertão Central
    "CIR Quixadá": "MACRO_SERTAO_CENTRAL",
    "CIR Quixeramobim": "MACRO_SERTAO_CENTRAL",
    
    # Macro Litoral Leste / Jaguaribe
    "CIR Aracati": "MACRO_LITORAL_LESTE",
    "CIR Limoeiro do Norte": "MACRO_LITORAL_LESTE",
    "CIR Russas": "MACRO_LITORAL_LESTE",
    
    # Macro Cariri (Sul)
    "CIR Icó": "MACRO_CARIRI",
    "CIR Iguatu": "MACRO_CARIRI",
    "CIR Brejo Santo": "MACRO_CARIRI",
    "CIR Crato": "MACRO_CARIRI",
    "CIR Juazeiro do Norte": "MACRO_CARIRI",
    
    # Regiões especiais
    "CIR Itapipoca": "MACRO_FLUTUANTE",  # Pode ir para Fortaleza ou Sobral
}

# Hierarquia de prioridade para transferência
# 1. Mesma Região (ADS)
# 2. Mesma Macrorregião
# 3. Qualquer (caso não haja opções nas anteriores)

# Regiões que compõem cada Macrorregião (para validação)
REGIOES_POR_MACRO = {
    "MACRO_FORTALEZA": [
        "CIR Fortaleza", "CIR Caucaia", "CIR Maracanaú", 
        "CIR Baturité", "CIR Beberibe", "CIR Cascavel"
    ],
    "MACRO_SOBRAL": [
        "CIR Sobral", "CIR Acaraú", "CIR Tianguá", 
        "CIR Camocim", "CIR Canindé", "CIR Tauá"
    ],
    "MACRO_SERTAO_CENTRAL": [
        "CIR Quixadá", "CIR Quixeramobim"
    ],
    "MACRO_LITORAL_LESTE": [
        "CIR Aracati", "CIR Limoeiro do Norte", "CIR Russas"
    ],
    "MACRO_CARIRI": [
        "CIR Icó", "CIR Iguatu", "CIR Brejo Santo", 
        "CIR Crato", "CIR Juazeiro do Norte"
    ],
    "MACRO_FLUTUANTE": [
        "CIR Itapipoca"
    ],
}

# Para CIR Itapipoca, definimos para quais Macros ela pode ir
MACROS_FLUTUANTES = {
    "CIR Itapipoca": ["MACRO_FORTALEZA", "MACRO_SOBRAL"]
}

def get_macro_regiao(cir: str) -> str:
    """Retorna a Macrorregião de uma CIR"""
    return MACRO_POR_REGIAO.get(cir, "MACRO_DESCONHECIDA")

def get_regioes_por_macro(macro: str) -> list:
    """Retorna lista de CIRs de uma Macrorregião"""
    return REGIOES_POR_MACRO.get(macro, [])

def pode_transferir(cir_origem: str, cir_destino: str) -> bool:
    """
    Verifica se é permitido transferir de uma CIR para outra
    Segue a hierarquia: mesma região > mesma macro > exceções
    """
    if cir_origem == cir_destino:
        return True
    
    macro_origem = get_macro_regiao(cir_origem)
    macro_destino = get_macro_regiao(cir_destino)
    
    # Se for a mesma macro, permite
    if macro_origem == macro_destino and macro_origem != "MACRO_DESCONHECIDA":
        return True
    
    # Caso especial: CIR Itapipoca (flutuante)
    if cir_origem == "CIR Itapipoca":
        return macro_destino in MACROS_FLUTUANTES["CIR Itapipoca"]
    
    if cir_destino == "CIR Itapipoca":
        return macro_origem in MACROS_FLUTUANTES["CIR Itapipoca"]
    
    return False