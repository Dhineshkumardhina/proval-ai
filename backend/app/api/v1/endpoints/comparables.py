"""Comparable transaction deed endpoints."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, UserSession
from app.models.valuation import ValuationCaseModel
from app.models.property import PropertyRecord

router = APIRouter()


@router.get(
    "",
    response_model=List[Dict[str, Any]],
    summary="Search Comparable Deeds",
    description="Query comparable property deeds by metro city, locality or parent case. Requires authentication.",
)
def search_comparables(
    city: Optional[str] = Query(default=None, description="Metro City filter"),
    case_id: Optional[str] = Query(default=None, description="Filter comparables linked to case"),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """Retrieve comparable properties."""
    query = db.query(ValuationCaseModel).join(PropertyRecord)
    if case_id:
        query = query.filter(ValuationCaseModel.id == case_id)
    if city:
        query = query.filter(PropertyRecord.city == city)

    cases = query.limit(limit).all()
    all_comps = []
    seen_ids = set()

    for c in cases:
        for comp in (c.comparables or []):
            comp_id = comp.get("id")
            if comp_id and comp_id not in seen_ids:
                seen_ids.add(comp_id)
                all_comps.append(comp)

    return all_comps[:limit]

