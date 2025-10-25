"""FastAPI routes for orchestrating the autonomous marketing crew."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.crews.marketing.crew import MarketingCrew

router = APIRouter()
crew = MarketingCrew()


class RunCampaignRequest(BaseModel):
    week: int
    year: Optional[int] = None


@router.post("/api/v1/marketing/run-campaign", status_code=status.HTTP_200_OK)
def run_campaign(payload: RunCampaignRequest) -> Dict[str, Any]:
    try:
        report = crew.orchestrate_weekly_cycle(payload.week, year=payload.year)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"status": "completed", "report": report}


@router.get("/api/v1/marketing/report/{week}")
def get_report(week: int, year: Optional[int] = Query(None)) -> Dict[str, Any]:
    iso_year = year or datetime.utcnow().isocalendar().year
    path = crew.reports_root / f"{iso_year}-{week:02d}.json"
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {"week": week, "year": iso_year, "report": payload}


@router.get("/api/v1/marketing/insights")
def get_insights() -> Dict[str, Any]:
    insights = crew.latest_insights()
    if not insights:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No insights available")
    return {"insights": insights}
