from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from agir_db.db.session import get_db
from agir_db.models.scenario import Scenario
from agir_db.models.episode import Episode

router = APIRouter()

@router.get("/")
async def get_scenarios(db: Session = Depends(get_db)):
    """Get all scenarios"""
    scenarios = db.query(Scenario).all()
    return scenarios

@router.get("/{scenario_id}")
async def get_scenario(scenario_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a scenario by ID"""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    return scenario

@router.get("/{scenario_id}/episodes")
async def get_scenario_episodes(scenario_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get all episodes for a scenario"""
    # First check if scenario exists
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    
    episodes = db.query(Episode).filter(Episode.scenario_id == scenario_id).all()
    return episodes 