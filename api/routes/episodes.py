from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
import uuid

from agir_db.db.session import get_db
from agir_db.models.episode import Episode
from agir_db.models.step import Step

router = APIRouter()

@router.get("/")
async def get_episodes(db: Session = Depends(get_db)):
    """Get all episodes"""
    episodes = db.query(Episode).all()
    return episodes

@router.get("/{episode_id}")
async def get_episode(episode_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get an episode by ID"""
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episode not found")
    return episode

@router.get("/{episode_id}/steps")
async def get_episode_steps(episode_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get all steps for an episode"""
    # First check if episode exists
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episode not found")
    
    steps = db.query(Step).filter(Step.episode_id == episode_id).order_by(Step.created_at).all()
    return steps 