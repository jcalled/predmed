"""
Score de priorização clínica — regras v0.1 (PROPOSTA, pendente de revisão clínica e jurídica; B34).

Apoio à decisão: o score ordena e explica; não substitui a regulação nem o julgamento clínico.
Cada ponto tem um critério visível para o gestor. Pesos em um só lugar para revisão.

Critérios (máximo 100):
- Classificação SWALIS (até 40): A1 40, A2 32, B 24, C 12, D 4; ausente 12 com alerta.
- Tempo de espera (até 30): proporcional aos dias desde a solicitação, saturando em 2 anos.
- Mandado judicial (+15).
- Oncologia (+10): especialidade ONCOLOGIA ou procedimento oncológico/maligno.
  Alerta quando a espera passa de 60 dias (referência: Lei 12.732/2012 — o prazo legal
  conta do diagnóstico, não da solicitação; aqui é só um sinal para revisão).
- Cardiovascular com SWALIS A1/A2 (+5).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

VERSAO_REGRAS = "v0.1 (proposta — pendente de validação clínica)"

PONTOS_SWALIS = {
    "Categoria A1": 40,
    "Categoria A2": 32,
    "Categoria B": 24,
    "Categoria C": 12,
    "Categoria D": 4,
}
PONTOS_SWALIS_AUSENTE = 12
MAX_PONTOS_ESPERA = 30
DIAS_SATURACAO_ESPERA = 730
PONTOS_JUDICIAL = 15
PONTOS_ONCOLOGIA = 10
PONTOS_CARDIO_GRAVE = 5
DIAS_REFERENCIA_ONCOLOGIA = 60

_TERMOS_ONCOLOGICOS = ("ONCOLOGIA", "MALIGN")


@dataclass
class ResultadoScore:
    score: int
    componentes: list[dict] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)


def eh_oncologico(especialidade: Optional[str], procedimento: Optional[str]) -> bool:
    esp = (especialidade or "").upper()
    proc = (procedimento or "").upper()
    return esp == "ONCOLOGIA" or any(t in proc for t in _TERMOS_ONCOLOGICOS)


def dias_desde(data_iso: Optional[str], hoje: date) -> Optional[int]:
    if not data_iso:
        return None
    try:
        return max((hoje - date.fromisoformat(data_iso[:10])).days, 0)
    except ValueError:
        return None


def calcular_score(
    *,
    classif_swalis: Optional[str],
    data_insercao: Optional[str],
    data_confiavel: Optional[bool],
    judicializado: bool,
    especialidade: Optional[str],
    procedimento: Optional[str],
    hoje: date,
) -> ResultadoScore:
    comp: list[dict] = []
    alertas: list[str] = []

    # SWALIS
    if classif_swalis in PONTOS_SWALIS:
        comp.append({"criterio": "SWALIS", "pontos": PONTOS_SWALIS[classif_swalis],
                     "detalhe": classif_swalis})
    else:
        comp.append({"criterio": "SWALIS", "pontos": PONTOS_SWALIS_AUSENTE,
                     "detalhe": "não informada (pontuação neutra)"})
        alertas.append("Classificação SWALIS não informada")

    # Tempo de espera
    dias = dias_desde(data_insercao, hoje)
    if dias is None:
        alertas.append("Sem data de solicitação")
    else:
        pontos = round(MAX_PONTOS_ESPERA * min(dias, DIAS_SATURACAO_ESPERA) / DIAS_SATURACAO_ESPERA)
        comp.append({"criterio": "Tempo de espera", "pontos": pontos, "detalhe": f"{dias} dias"})
        if data_confiavel is False:
            alertas.append("Data de solicitação a confirmar (numeração antiga)")

    # Judicialização
    if judicializado:
        comp.append({"criterio": "Mandado judicial", "pontos": PONTOS_JUDICIAL, "detalhe": "sim"})

    # Oncologia
    if eh_oncologico(especialidade, procedimento):
        comp.append({"criterio": "Oncologia", "pontos": PONTOS_ONCOLOGIA, "detalhe": "caso oncológico"})
        if dias is not None and dias > DIAS_REFERENCIA_ONCOLOGIA:
            alertas.append(f"Oncologia com mais de {DIAS_REFERENCIA_ONCOLOGIA} dias de espera "
                           "(referência Lei 12.732/2012)")

    # Cardiovascular grave
    if (especialidade or "").upper() == "CARDIOVASCULAR" and classif_swalis in ("Categoria A1", "Categoria A2"):
        comp.append({"criterio": "Cardiovascular grave", "pontos": PONTOS_CARDIO_GRAVE,
                     "detalhe": "cardiovascular com SWALIS A1/A2"})

    score = min(sum(c["pontos"] for c in comp), 100)
    return ResultadoScore(score=score, componentes=comp, alertas=alertas)
