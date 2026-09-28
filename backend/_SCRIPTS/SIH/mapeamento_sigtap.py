"""
Mapeamento automático de especialidades usando a estrutura SIGTAP
Baseado nos subgrupos oficiais do SUS
Fonte: http://sigtap.datasus.gov.br/
"""

# Mapeamento de subgrupos SIGTAP para especialidades
SUBGRUPO_PARA_ESPECIALIDADE = {
    # GRUPO 02 - PROCEDIMENTOS COM FINALIDADE DIAGNÓSTICA
    "0201": "RADIOLOGIA",
    "0202": "RADIOLOGIA",
    "0203": "RADIOLOGIA",
    "0204": "RADIOLOGIA",
    "0205": "RADIOLOGIA",
    "0206": "RADIOLOGIA",
    "0207": "MEDICINA_NUCLEAR",
    "0208": "ENDOSCOPIA",
    "0209": "ENDOSCOPIA",
    "0210": "CARDIOLOGIA",
    "0211": "NEUROLOGIA",
    "0212": "CARDIOLOGIA",
    "0213": "NEUROLOGIA",
    "0214": "OFTALMOLOGIA",
    "0215": "OTORRINO",
    
    # GRUPO 03 - PROCEDIMENTOS CLÍNICOS
    "0301": "CLINICA_MEDICA",
    "0302": "FISIOTERAPIA",
    "0303": "FONOAUDIOLOGIA",
    "0304": "TERAPIA_OCUPACIONAL",
    "0305": "PSICOLOGIA",
    "0306": "NUTRICAO",
    "0307": "ASSISTENCIA_SOCIAL",
    "0308": "ENFERMAGEM",
    "0309": "ODONTOLOGIA",
    "0310": "NEFROLOGIA",
    "0311": "ONCOLOGIA",
    "0312": "ONCOLOGIA",
    "0313": "HEMATOLOGIA",
    "0314": "NEUROLOGIA",
    "0315": "NEUROLOGIA",
    
    # GRUPO 04 - PROCEDIMENTOS CIRÚRGICOS
    "0401": "CIRURGIA_DIGESTIVA",
    "0402": "CIRURGIA_CARDIOVASCULAR",
    "0403": "NEUROCIRURGIA",
    "0404": "CIRURGIA_TORACICA",
    "0405": "CIRURGIA_ORTOPEDICA",
    "0406": "CIRURGIA_UROLOGICA",
    "0407": "CIRURGIA_DIGESTIVA",
    "0408": "CIRURGIA_GINECOLOGICA",
    "0409": "CIRURGIA_OFTALMOLOGICA",
    "0410": "CIRURGIA_OTORRINO",
    "0411": "CIRURGIA_MAXILOFACIAL",
    "0412": "CIRURGIA_PLASTICA",
    "0413": "MASTOLOGIA",
    "0414": "CIRURGIA_PEDIATRICA",
    "0415": "CIRURGIA_VASCULAR",
    "0416": "TRANSPLANTES",
    "0417": "ANESTESIOLOGIA",
    
    # GRUPO 05 - TRANSPLANTES
    "0501": "TRANSPLANTES",
    "0502": "TRANSPLANTES",
    "0503": "TRANSPLANTES",
}

# Mapeamento para especialidades do PREDMED
PREDMED_PARA_SUBGRUPO = {
    "CIR DIGESTIVA": ["0401", "0407"],
    "CARDIOVASCULAR": ["0402", "0210", "0212"],
    "NEUROLOGIA": ["0403", "0211", "0213", "0314"],
    "ORTOPEDIA": ["0405", "0204", "0205", "0206"],
    "UROLOGIA": ["0406"],
    "GINECOLOGIA": ["0408"],
    "OFTALMOLOGIA": ["0409", "0214"],
    "OTORRINO": ["0410", "0215"],
    "ONCOLOGIA": ["0311", "0312", "0413"],
    "PEDIATRIA": ["0414"],
    "CIRURGIA GERAL": ["0401", "0407", "0411", "0412"],
}

# Exceções manuais (apenas para casos ambíguos)
EXCECOES_CONHECIDAS = {
    "0407010016": "UROLOGIA",  # Prostatectomia
    "0407020012": "UROLOGIA",  # Nefrectomia
    "0407030019": "UROLOGIA",  # Cirurgia de bexiga
    "0407040015": "UROLOGIA",  # Ureterolitotomia
    "0407050011": "UROLOGIA",  # Cirurgia de testículo
}

def extrair_especialidade_do_procedimento(codigo_procedimento: str) -> list:
    """
    Extrai especialidades a partir do código SIGTAP
    Retorna lista de especialidades compatíveis
    """
    if not codigo_procedimento or len(codigo_procedimento) < 6:
        return ["OUTROS"]
    
    # Limpa o código (remove pontuação)
    codigo_limpo = codigo_procedimento.replace(".", "").replace("-", "").replace("/", "")
    
    # Verifica exceções primeiro
    if codigo_limpo in EXCECOES_CONHECIDAS:
        return [EXCECOES_CONHECIDAS[codigo_limpo]]
    
    # Extrai grupo e subgrupo (primeiros 4 dígitos)
    grupo_subgrupo = codigo_limpo[:4]
    
    # Mapeia para especialidade base
    especialidade_base = SUBGRUPO_PARA_ESPECIALIDADE.get(grupo_subgrupo, "OUTROS")
    
    # Mapeia para especialidade PREDMED
    for predmed, subgrupos in PREDMED_PARA_SUBGRUPO.items():
        if grupo_subgrupo in subgrupos:
            return [predmed]
    
    return [especialidade_base]

def extrair_especialidades_do_nome_procedimento(nome_procedimento: str) -> list:
    """
    Fallback: extrai especialidades do nome do procedimento usando palavras-chave
    """
    if not nome_procedimento:
        return []
    
    nome = nome_procedimento.upper()
    especialidades = []
    
    KEYWORDS = {
        "ORTOPEDIA": ["ORTOPED", "FRATURA", "ARTROPLASTIA", "JOELHO", "QUADRIL", "COLUNA", "OSS", "FEMUR", "TIBIA"],
        "OFTALMOLOGIA": ["OFTALM", "OLHO", "CATARATA", "GLAUCOMA", "RETINA", "CORNEA", "VISAO", "FACECTOMIA"],
        "CARDIOLOGIA": ["CARDI", "CORACAO", "CARDIOVASCULAR", "VASCULAR", "MARCA PASSO", "VALVA"],
        "CIRURGIA GERAL": ["HERNIA", "VESICULA", "APENDICE", "COLECIST", "HEMORROIDA"],
        "UROLOGIA": ["UROLOG", "RIM", "PROSTATA", "BEXIGA", "TESTICULO", "NEFRECTOMIA"],
        "GINECOLOGIA": ["GINECO", "OBSTET", "UTERO", "OVARIO", "MAMA", "MASTECTOMIA", "HISTERECTOMIA"],
        "NEUROLOGIA": ["NEURO", "CEREBRO", "CRANIO", "NEUROCIRURGIA", "COLUNA VERTEBRAL"],
        "DIGESTIVA": ["DIGESTIVA", "ESOFAGO", "ESTOMAGO", "INTESTINO", "COLON", "GASTRO"],
        "ONCOLOGIA": ["ONCO", "CANCER", "TUMOR", "NEOPLASIA", "QUIMIO", "RADIO"],
        "PEDIATRIA": ["PEDIAT", "INFANTIL", "CRIANCA"],
    }
    
    for esp, palavras in KEYWORDS.items():
        if any(palavra in nome for palavra in palavras):
            especialidades.append(esp)
    
    return especialidades