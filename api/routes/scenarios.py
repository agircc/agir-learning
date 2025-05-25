from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List
import uuid

from agir_db.db.session import get_db
from agir_db.models.scenario import Scenario
from agir_db.models.episode import Episode
from agir_db.models.state import State
from agir_db.models.state_transition import StateTransition
from agir_db.models.state_role import StateRole

router = APIRouter()

@router.get("/")
async def get_scenarios(db: Session = Depends(get_db)):
    """Get all scenarios"""
    scenarios = db.query(Scenario).all()
    return scenarios

@router.get("/{scenario_id}")
async def get_scenario(scenario_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a scenario by ID with detailed information"""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    
    # Get states for this scenario
    states = db.query(State).filter(State.scenario_id == scenario_id).all()
    
    # Get transitions for this scenario's states
    state_ids = [state.id for state in states]
    transitions = []
    
    if state_ids:
        transitions = db.query(StateTransition).options(
            joinedload(StateTransition.from_state),
            joinedload(StateTransition.to_state)
        ).filter(
            StateTransition.from_state_id.in_(state_ids)
        ).all()
    
    # Get state roles
    state_roles = []
    if state_ids:
        state_roles = db.query(StateRole).options(
            joinedload(StateRole.role)
        ).filter(
            StateRole.state_id.in_(state_ids)
        ).all()
    
    # Format the response
    formatted_states = []
    for state in states:
        state_transition_from = [t for t in transitions if t.from_state_id == state.id]
        state_transition_to = [t for t in transitions if t.to_state_id == state.id]
        state_role_list = [r for r in state_roles if r.state_id == state.id]
        
        formatted_states.append({
            "id": state.id,
            "name": state.name,
            "description": state.description,
            "data": state.data if hasattr(state, "data") else {},
            "roles": [
                {
                    "id": role.agent_role_id,
                    "name": role.role.name if role.role else "Unknown Role",
                    "agent_role": role.role.model if role.role else "Unknown Model"
                } for role in state_role_list if role
            ],
            "transitions_from": [
                {
                    "id": trans.id,
                    "description": trans.condition if trans.condition else f"Transition to {trans.to_state.name if trans.to_state else 'unknown state'}",
                    "to_state_id": trans.to_state_id,
                    "to_state_name": trans.to_state.name if trans.to_state else "Unknown"
                } for trans in state_transition_from
            ],
            "transitions_to": [
                {
                    "id": trans.id,
                    "description": trans.condition if trans.condition else f"Transition from {trans.from_state.name if trans.from_state else 'unknown state'}",
                    "from_state_id": trans.from_state_id,
                    "from_state_name": trans.from_state.name if trans.from_state else "Unknown"
                } for trans in state_transition_to
            ]
        })
    
    # Count episodes
    episodes_count = db.query(Episode).filter(Episode.scenario_id == scenario_id).count()
    
    # Construct the final response
    result = {
        "id": scenario.id,
        "name": scenario.name,
        "description": scenario.description,
        "created_at": scenario.created_at,
        "updated_at": scenario.updated_at,
        "states": formatted_states,
        "episodes_count": episodes_count
    }
    
    return result

@router.get("/{scenario_id}/episodes")
async def get_scenario_episodes(scenario_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get all episodes for a scenario"""
    # First check if scenario exists
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    
    episodes = db.query(Episode).filter(Episode.scenario_id == scenario_id).order_by(desc(Episode.created_at)).all()
    return episodes 