from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import analytics as a
from ..auth import require_admin
from ..db import get_db

router = APIRouter(prefix="/api/admin", tags=["admin"])


def filters(district: str | None = None, income_bracket: str | None = None, period: str | None = None,
            include_simulated: bool = True) -> a.Filters:
    if period not in (None, "", "all", "7d", "30d", "90d"):
        raise HTTPException(422, "period must be one of all, 7d, 30d, 90d")
    return a.Filters(district, income_bracket, period, include_simulated)


@router.get("/overview")
def overview(f: a.Filters = Depends(filters), db: Session = Depends(get_db), _: str = Depends(require_admin)):
    return a.overview(db, f)


@router.get("/concerns")
def concerns(f: a.Filters = Depends(filters), db: Session = Depends(get_db), _: str = Depends(require_admin)):
    return a.concerns(db, f)


@router.get("/resistance-by-district")
def resistance(f: a.Filters = Depends(filters), db: Session = Depends(get_db), _: str = Depends(require_admin)):
    return a.resistance_by_district(db, f)


@router.get("/sentiment-shift")
def sentiment(f: a.Filters = Depends(filters), db: Session = Depends(get_db), _: str = Depends(require_admin)):
    return a.sentiment_shift(db, f)


@router.get("/funnel")
def funnel(f: a.Filters = Depends(filters), db: Session = Depends(get_db), _: str = Depends(require_admin)):
    return a.funnel(db, f)


@router.get("/alignment-gaps")
def alignment_gaps(f: a.Filters = Depends(filters), db: Session = Depends(get_db), _: str = Depends(require_admin)):
    return a.alignment_gaps(db, f)


@router.get("/evidence-gaps")
def evidence_gaps(f: a.Filters = Depends(filters), db: Session = Depends(get_db), _: str = Depends(require_admin)):
    return a.evidence_gaps(db, f)


@router.get("/data-quality")
def data_quality(db: Session = Depends(get_db), _: str = Depends(require_admin)):
    return a.data_quality(db)


@router.get("/export.csv")
def export(f: a.Filters = Depends(filters), pin: str | None = Query(None), x_role_pin: str | None = Header(None),
           db: Session = Depends(get_db)):
    # A download link cannot send headers, so the PIN may also come as ?pin= (demo-grade auth).
    require_admin(x_role_pin or pin)
    return Response(a.export_csv(db, f), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="samvaad_district_summary.csv"'})
