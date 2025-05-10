# db/repositories.py
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Tuple
from .models import (Lifelist, LifelistType, LifelistTier, LifelistTypeTier)


class LifelistRepository:
    """Repository for Lifelist operations"""

    @staticmethod
    def get_lifelist_types(session: Session) -> List[LifelistType]:
        """Get all available lifelist types"""
        return session.query(LifelistType).order_by(LifelistType.name).all()

    @staticmethod
    def get_lifelist_type(session: Session, type_id: int) -> Optional[LifelistType]:
        """Get a specific lifelist type by ID"""
        return session.query(LifelistType).filter(LifelistType.id == type_id).first()

    @staticmethod
    def get_lifelist_type_by_name(session: Session, type_name: str) -> Optional[LifelistType]:
        """Get a specific lifelist type by name"""
        return session.query(LifelistType).filter(LifelistType.name == type_name).first()

    @staticmethod
    def get_default_tiers_for_type(session: Session, type_id: int) -> List[str]:
        """Get default tier names for a lifelist type"""
        tiers = session.query(LifelistTypeTier).filter(
            LifelistTypeTier.lifelist_type_id == type_id
        ).order_by(LifelistTypeTier.tier_order).all()

        return [tier.tier_name for tier in tiers]

    @staticmethod
    def create_lifelist(session: Session, name: str, lifelist_type_id: int,
                        classification: Optional[str] = None) -> Optional[int]:
        """Create a new lifelist"""
        try:
            lifelist = Lifelist(
                name=name,
                lifelist_type_id=lifelist_type_id,
                classification=classification
            )
            session.add(lifelist)
            session.flush()  # To get the ID

            # Set up default tiers
            default_tiers = LifelistRepository.get_default_tiers_for_type(session, lifelist_type_id)
            for i, tier_name in enumerate(default_tiers):
                session.add(LifelistTier(
                    lifelist_id=lifelist.id,
                    tier_name=tier_name,
                    tier_order=i
                ))

            return lifelist.id
        except Exception as e:
            session.rollback()
            print(f"Error creating lifelist: {e}")
            return None

    @staticmethod
    def get_lifelists(session: Session) -> List[Tuple]:
        """Get all lifelists with their type information"""
        query = session.query(
            Lifelist.id,
            Lifelist.name,
            Lifelist.classification,
            LifelistType.name.label('type_name')
        ).outerjoin(LifelistType).order_by(Lifelist.name)

        return [(row.id, row.name, row.classification, row.type_name) for row in query.all()]

    @staticmethod
    def get_lifelist(session: Session, lifelist_id: int) -> Optional[Tuple]:
        """Get a specific lifelist by ID"""
        query = session.query(
            Lifelist.id,
            Lifelist.name,
            Lifelist.classification,
            Lifelist.lifelist_type_id,
            LifelistType.name.label('type_name')
        ).outerjoin(LifelistType).filter(Lifelist.id == lifelist_id)

        row = query.first()
        if row:
            return (row.id, row.name, row.classification, row.lifelist_type_id, row.type_name)
        return None

    @staticmethod
    def delete_lifelist(session: Session, lifelist_id: int) -> bool:
        """Delete a lifelist by ID"""
        lifelist = session.query(Lifelist).filter(Lifelist.id == lifelist_id).first()
        if lifelist:
            session.delete(lifelist)
            return True
        return False

    @staticmethod
    def get_lifelist_tiers(session: Session, lifelist_id: int) -> List[str]:
        """Get tiers for a lifelist"""
        tiers = session.query(LifelistTier).filter(
            LifelistTier.lifelist_id == lifelist_id
        ).order_by(LifelistTier.tier_order).all()

        if tiers:
            return [tier.tier_name for tier in tiers]

        # If no custom tiers defined, get default tiers based on lifelist type
        lifelist = session.query(Lifelist).filter(Lifelist.id == lifelist_id).first()
        if lifelist and lifelist.lifelist_type_id:
            return LifelistRepository.get_default_tiers_for_type(session, lifelist.lifelist_type_id)

        return ["owned", "wanted"]  # Fallback

    @staticmethod
    def set_lifelist_tiers(session: Session, lifelist_id: int, tiers: List[str]) -> bool:
        """Set custom tiers for a lifelist"""
        # Delete existing tiers
        session.query(LifelistTier).filter(LifelistTier.lifelist_id == lifelist_id).delete()

        # Add new tiers
        for i, tier_name in enumerate(tiers):
            session.add(LifelistTier(
                lifelist_id=lifelist_id,
                tier_name=tier_name,
                tier_order=i
            ))

        return True