"""
Cenários da meta de −40% no tempo de espera (SIMULADO).

Devolve o resultado versionado mais recente de backend/_SCRIPTS/cenarios_meta_40.py
(backend/avaliacoes/meta40/cenarios_AAAAMMDD.json). Só agregados por estabelecimento/CIR ×
especialidade; nada de pacientes. Metodologia: docs/dados/meta-40-caminho.md.

Acesso: gestores. SESA vê o estado; SMS vê só a própria CIR (recortes, CIR × especialidade e
candidatos); os blocos estaduais agregados são iguais para os dois.
"""
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from auth import require_gestor
from database import Tenant, Usuario, get_db

router = APIRouter(prefix="/meta40", tags=["meta40"])

DIR = Path(__file__).resolve().parents[1] / "avaliacoes" / "meta40"
_CACHE: dict = {}


def _ultimo() -> dict:
    arqs = sorted(DIR.glob("cenarios_*.json"))
    if not arqs:
        raise HTTPException(status_code=404, detail="Cenários ainda não gerados (rode _SCRIPTS/cenarios_meta_40.py)")
    arq = arqs[-1]
    mtime = arq.stat().st_mtime
    if _CACHE.get("arq") != arq.name or _CACHE.get("mtime") != mtime:
        _CACHE.update({"arq": arq.name, "mtime": mtime, "dados": json.loads(arq.read_text())})
    return _CACHE["dados"]


@router.get("/cenarios")
def cenarios(
    cir: Optional[str] = Query(None, description="filtra recortes por CIR (SESA)"),
    especialidade: Optional[str] = None,
    user: Usuario = Depends(require_gestor),
    db: Session = Depends(get_db),
):
    d = _ultimo()
    if user.role == "sms":
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first() if user.tenant_id else None
        cir = tenant.cir if tenant and tenant.cir else "__sem_cir__"

    def filtra(lista):
        return [r for r in lista
                if (not cir or r.get("cir") == cir) and (not especialidade or r.get("especialidade") == especialidade)]

    return {
        **{k: d[k] for k in ("versao", "gerado_em", "data_referencia", "natureza", "metodologia", "fontes",
                             "estadual", "grupos_prioridade", "sistema_simultaneo", "mapa",
                             "capacidade_necessaria_40_90d_pct_producao") if k in d},
        "escopo": "estado" if user.role == "sesa" else "cir",
        "cir_selecionada": cir,
        "recortes": filtra(d.get("recortes", [])),
        "cir_especialidade": filtra(d.get("cir_especialidade", [])),
        "candidatos_piloto": filtra(d.get("candidatos_piloto", [])),
        "aviso": "Cenários SIMULADOS com capacidade ESTIMADA. A meta de −40% não está comprovada.",
    }
