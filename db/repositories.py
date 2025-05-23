# db/repositories.py
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, or_, desc
from typing import List, Optional, Dict, Any, Tuple
from .models import (Lifelist, LifelistType, LifelistTier, LifelistTypeTier,
                     Observation, Photo, Tag, CustomField, ObservationCustomField,
                     Classification, ClassificationEntry, TagHierarchy, Equipment, ObservationEquipment)
import json


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
            return row.id, row.name, row.classification, row.lifelist_type_id, row.type_name
        return None

    @staticmethod
    def delete_lifelist(session: Session, lifelist_id: int) -> bool:
        """Delete a lifelist by ID"""
        if (
            lifelist := session.query(Lifelist)
            .filter(Lifelist.id == lifelist_id)
            .first()
        ):
            session.delete(lifelist)
            return True
        return False

    @staticmethod
    def get_lifelist_tiers(session: Session, lifelist_id: int) -> List[str]:
        """Get tiers for a lifelist without including special tiers like 'Undetermined'"""
        if (
            tiers := session.query(LifelistTier)
            .filter(LifelistTier.lifelist_id == lifelist_id)
            .order_by(LifelistTier.tier_order)
            .all()
        ):
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


class ObservationRepository:
    """Repository for Observation operations"""

    @staticmethod
    def get_observation(session: Session, observation_id: int) -> Optional[Observation]:
        """Get a specific observation by ID"""
        return session.query(Observation).filter(Observation.id == observation_id).first()

    @staticmethod
    def get_observations(session: Session, lifelist_id: int,
                         tier: Optional[str] = None,
                         entry_name: Optional[str] = None,
                         search_text: Optional[str] = None,
                         tag_ids: Optional[List[int]] = None) -> List[Observation]:
        """
        Get observations with optional filtering

        Args:
            session: Database session
            lifelist_id: ID of the lifelist
            tier: Optional tier to filter by
            entry_name: Optional entry name to filter by
            search_text: Optional text to search in name, location, and notes
            tag_ids: Optional list of tag IDs to filter by

        Returns:
            List of matching observations
        """
        query = session.query(Observation).filter(Observation.lifelist_id == lifelist_id)

        # Apply filters
        if tier:
            query = query.filter(Observation.tier == tier)

        if entry_name:
            query = query.filter(Observation.entry_name == entry_name)

        if search_text:
            search_pattern = f"%{search_text}%"
            query = query.filter(
                or_(
                    Observation.entry_name.ilike(search_pattern),
                    Observation.location.ilike(search_pattern),
                    Observation.notes.ilike(search_pattern)
                )
            )

        if tag_ids:
            for tag_id in tag_ids:
                query = query.filter(Observation.tags.any(id=tag_id))

        # Order by date (most recent first)
        query = query.order_by(desc(Observation.observation_date))

        return query.all()

    @staticmethod
    def get_observations_batch(session: Session, lifelist_id: int,
                               offset: int = 0, limit: int = 50,
                               tier: Optional[str] = None,
                               search_text: Optional[str] = None,
                               tag_ids: Optional[List[int]] = None,
                               sort_by: str = 'date_desc') -> List[Dict]:
        """Get batch of observations with metadata only (no lazy loading)"""
        query = session.query(
            Observation.id,
            Observation.entry_name,
            Observation.observation_date,
            Observation.location,
            Observation.tier,
            Observation.lifelist_id
        ).filter(Observation.lifelist_id == lifelist_id)

        # Apply filters
        if tier:
            if tier == "Undetermined":
                # Special case for undetermined tier - match observations with tier not in the list of valid tiers
                valid_tiers = LifelistRepository.get_lifelist_tiers(session, lifelist_id)
                query = query.filter(
                    or_(
                        ~Observation.tier.in_(valid_tiers),  # Not in valid tiers
                        Observation.tier == "Undetermined"  # Explicitly marked as Undetermined
                    )
                )
            else:
                query = query.filter(Observation.tier == tier)

        if search_text:
            search_pattern = f"%{search_text}%"
            query = query.filter(or_(
                Observation.entry_name.ilike(search_pattern),
                Observation.location.ilike(search_pattern),
                Observation.notes.ilike(search_pattern)
            ))
        if tag_ids:
            for tag_id in tag_ids:
                query = query.filter(Observation.tags.any(id=tag_id))

        # Apply sorting
        if sort_by == 'date_desc':
            query = query.order_by(desc(Observation.observation_date))
        elif sort_by == 'name_asc':
            query = query.order_by(Observation.entry_name)

        # Apply offset and limit
        query = query.offset(offset).limit(limit)

        results = query.all()

        # Convert to plain dictionaries (detached from session)
        observations = []
        observations.extend(
            {
                'id': row.id,
                'entry_name': row.entry_name,
                'date': row.observation_date,
                'location': row.location,
                'tier': row.tier,
                'lifelist_id': row.lifelist_id,
                'photo_id': None,  # Populated separately if needed
            }
            for row in results
        )
        return observations

    @staticmethod
    def count_observations(session: Session, lifelist_id: int,
                           tier: Optional[str] = None,
                           search_text: Optional[str] = None,
                           tag_ids: Optional[List[int]] = None) -> int:
        """Count total observations with filters"""
        query = session.query(func.count(Observation.id)).filter(Observation.lifelist_id == lifelist_id)

        # Apply same filters as get_observations_batch
        if tier: query = query.filter(Observation.tier == tier)
        if search_text:
            search_pattern = f"%{search_text}%"
            query = query.filter(or_(
                Observation.entry_name.ilike(search_pattern),
                Observation.location.ilike(search_pattern),
                Observation.notes.ilike(search_pattern)
            ))
        if tag_ids:
            for tag_id in tag_ids:
                query = query.filter(Observation.tags.any(id=tag_id))

        return query.scalar()

    @staticmethod
    def get_observation_with_eager_loading(session: Session, observation_id: int) -> Optional[Dict]:
        """Get single observation with all relationships eagerly loaded"""
        observation = session.query(Observation).options(
            selectinload(Observation.photos).load_only(Photo.id, Photo.file_path, Photo.is_primary),
            selectinload(Observation.custom_fields).options(
                selectinload(ObservationCustomField.field).load_only(CustomField.field_name)
            ),
            selectinload(Observation.tags).load_only(Tag.name, Tag.category),
            selectinload(Observation.lifelist)
        ).filter(Observation.id == observation_id).first()

        if not observation:
            return None

        # Convert to dictionary to detach from session
        return {
            'id': observation.id,
            'entry_name': observation.entry_name,
            'observation_date': observation.observation_date,
            'location': observation.location,
            'latitude': observation.latitude,
            'longitude': observation.longitude,
            'tier': observation.tier,
            'notes': observation.notes,
            'lifelist_id': observation.lifelist_id,
            'custom_fields': [
                {'field_name': cf.field.field_name, 'value': cf.value}
                for cf in observation.custom_fields
            ],
            'tags': [
                {'name': tag.name, 'category': tag.category}
                for tag in observation.tags
            ],
            'photos': [
                {'id': photo.id, 'file_path': photo.file_path, 'is_primary': photo.is_primary}
                for photo in observation.photos
            ]
        }

    @staticmethod
    def get_observations_with_coordinates_for_display(session: Session, lifelist_id: int,
                                                      tier: Optional[str] = None,
                                                      entry_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get observations with coordinates as dictionaries"""
        query = session.query(Observation).filter(
            Observation.lifelist_id == lifelist_id,
            Observation.latitude.isnot(None),
            Observation.longitude.isnot(None)
        )

        # Apply additional filters
        if tier:
            query = query.filter(Observation.tier == tier)

        if entry_name:
            query = query.filter(Observation.entry_name == entry_name)

        # Extract data while session is active
        result = []
        result.extend(
            {
                'id': obs.id,
                'entry_name': obs.entry_name,
                'observation_date': obs.observation_date,
                'location': obs.location,
                'latitude': obs.latitude,
                'longitude': obs.longitude,
                'tier': obs.tier,
                'notes': obs.notes,
                'lifelist_id': obs.lifelist_id,
            }
            for obs in query.all()
        )
        return result

    @staticmethod
    def get_observations_with_custom_fields(session: Session, lifelist_id: int) -> List[Dict[str, Any]]:
        """Get observations with their custom fields as dictionaries"""
        from sqlalchemy.orm import joinedload

        observations = session.query(Observation).filter(
            Observation.lifelist_id == lifelist_id
        ).options(
            joinedload(Observation.custom_fields).joinedload(ObservationCustomField.field)
        ).all()

        result = []
        for obs in observations:
            # Extract basic observation data
            obs_data = {
                'id': obs.id,
                'entry_name': obs.entry_name,
                'observation_date': obs.observation_date,
                'location': obs.location,
                'latitude': obs.latitude,
                'longitude': obs.longitude,
                'tier': obs.tier,
                'notes': obs.notes,
                'lifelist_id': obs.lifelist_id,
                'custom_fields': []
            }

            # Extract custom fields
            for cf in obs.custom_fields:
                obs_data['custom_fields'].append({
                    'field_id': cf.field_id,
                    'field_name': cf.field.field_name,
                    'value': cf.value
                })

            result.append(obs_data)

        return result

    @staticmethod
    def get_unique_entries(session: Session, lifelist_id: int) -> List[str]:
        """Get unique entry names for a lifelist"""
        query = session.query(Observation.entry_name).filter(
            Observation.lifelist_id == lifelist_id
        ).distinct().order_by(Observation.entry_name)

        return [row.entry_name for row in query.all()]

    @staticmethod
    def create_observation(session: Session, lifelist_id: int, entry_name: str,
                           tier: Optional[str] = None,
                           observation_date: Optional[Any] = None,
                           location: Optional[str] = None,
                           latitude: Optional[float] = None,
                           longitude: Optional[float] = None,
                           notes: Optional[str] = None) -> Optional[int]:
        """Create a new observation"""
        try:
            observation = Observation(
                lifelist_id=lifelist_id,
                entry_name=entry_name,
                tier=tier,
                observation_date=observation_date,
                location=location,
                latitude=latitude,
                longitude=longitude,
                notes=notes
            )

            session.add(observation)
            session.flush()  # To get the ID

            return observation.id
        except Exception as e:
            print(f"Error creating observation: {e}")
            return None

    @staticmethod
    def update_observation(session: Session, observation_id: int,
                           entry_name: Optional[str] = None,
                           tier: Optional[str] = None,
                           observation_date: Optional[Any] = None,
                           location: Optional[str] = None,
                           latitude: Optional[float] = None,
                           longitude: Optional[float] = None,
                           notes: Optional[str] = None) -> bool:
        """Update an existing observation"""
        try:
            observation = session.query(Observation).filter(
                Observation.id == observation_id
            ).first()

            if not observation:
                return False

            # Update fields
            if entry_name is not None:
                observation.entry_name = entry_name

            if tier is not None:
                observation.tier = tier

            if observation_date is not None:
                observation.observation_date = observation_date

            if location is not None:
                observation.location = location

            if latitude is not None:
                observation.latitude = latitude

            if longitude is not None:
                observation.longitude = longitude

            if notes is not None:
                observation.notes = notes

            return True
        except Exception as e:
            print(f"Error updating observation: {e}")
            return False

    @staticmethod
    def delete_observation(session: Session, observation_id: int) -> bool:
        """Delete an observation by ID"""
        try:
            observation = session.query(Observation).filter(
                Observation.id == observation_id
            ).first()

            if not observation:
                return False

            session.delete(observation)
            return True
        except Exception as e:
            print(f"Error deleting observation: {e}")
            return False

    @staticmethod
    def set_observation_custom_fields(session: Session, observation_id: int,
                                      field_values: Dict[int, str]) -> bool:
        """
        Set custom field values for an observation

        Args:
            session: Database session
            observation_id: ID of the observation
            field_values: Dictionary mapping field IDs to values

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get observation
            observation = session.query(Observation).filter(
                Observation.id == observation_id
            ).first()

            if not observation:
                return False

            # Delete existing values
            session.query(ObservationCustomField).filter(
                ObservationCustomField.observation_id == observation_id
            ).delete(synchronize_session='fetch')

            # Add new values
            for field_id, value in field_values.items():
                if value:  # Only add non-empty values
                    custom_field = ObservationCustomField(
                        observation_id=observation_id,
                        field_id=field_id,
                        value=value
                    )
                    session.add(custom_field)

            return True
        except Exception as e:
            print(f"Error setting custom fields: {e}")
            return False

    @staticmethod
    def get_observation_tiers_counts(session: Session, lifelist_id: int) -> Dict[str, int]:
        """Get counts of observations by tier"""
        query = session.query(
            Observation.tier,
            func.count(Observation.id).label('count')
        ).filter(
            Observation.lifelist_id == lifelist_id
        ).group_by(Observation.tier)

        return {row.tier or 'None': row.count for row in query.all()}

    @staticmethod
    def get_observations_by_entry(session: Session, lifelist_id: int, entry_name: str) -> List[Observation]:
        """Get all observations for a specific entry"""
        return session.query(Observation).filter(
            Observation.lifelist_id == lifelist_id,
            Observation.entry_name == entry_name
        ).order_by(desc(Observation.observation_date)).all()

    @staticmethod
    def get_observation_for_display(session: Session, observation_id: int) -> Dict[str, Any]:
        """Get complete observation data ready for display in UI.
        All data is extracted to basic Python types while the session is active."""

        from db.models import Observation, ObservationCustomField
        from sqlalchemy.orm import joinedload

        # Load observation with all relationships eagerly loaded
        if (
            observation := session.query(Observation)
            .filter_by(id=observation_id)
            .options(
                joinedload(Observation.photos),
                joinedload(Observation.custom_fields).joinedload(
                    ObservationCustomField.field
                ),
                joinedload(Observation.tags),
            )
            .first()
        ):
            # Extract all needed data while session is still active
            return {
                'id': observation.id,
                'entry_name': observation.entry_name,
                'observation_date': observation.observation_date,
                'location': observation.location,
                'latitude': observation.latitude,
                'longitude': observation.longitude,
                'tier': observation.tier,
                'notes': observation.notes,
                'lifelist_id': observation.lifelist_id,
                'custom_fields': [
                    {
                        'field_id': cf.field_id,
                        'field_name': cf.field.field_name,
                        'value': cf.value
                    }
                    for cf in observation.custom_fields
                ],
                'tags': [
                    {
                        'id': tag.id,
                        'name': tag.name,
                        'category': tag.category
                    }
                    for tag in observation.tags
                ],
                'photos': [
                    {
                        'id': photo.id,
                        'file_path': photo.file_path,
                        'is_primary': photo.is_primary
                    }
                    for photo in observation.photos
                ]
            }
        else:
            return None


class PhotoRepository:
    """Repository for Photo operations"""

    @staticmethod
    def get_photo(session: Session, photo_id: int) -> Optional[Photo]:
        """Get a photo by ID"""
        return session.query(Photo).filter(Photo.id == photo_id).first()

    @staticmethod
    def get_observation_photos(session: Session, observation_id: int) -> List[Photo]:
        """Get all photos for an observation"""
        return session.query(Photo).filter(
            Photo.observation_id == observation_id
        ).order_by(Photo.is_primary.desc()).all()

    @staticmethod
    def get_entry_photos(session: Session, lifelist_id: int, entry_name: str,
                         primary_only: bool = False) -> List[Photo]:
        """
        Get photos for a specific entry across all observations

        Args:
            session: Database session
            lifelist_id: ID of the lifelist
            entry_name: Name of the entry
            primary_only: Whether to return only primary photos

        Returns:
            List of photos
        """
        query = session.query(Photo).join(Observation).filter(
            Observation.lifelist_id == lifelist_id,
            Observation.entry_name == entry_name
        )

        if primary_only:
            query = query.filter(Photo.is_primary == True)

        query = query.order_by(Photo.is_primary.desc())

        return query.all()

    @staticmethod
    def get_observation_photos_for_display(session: Session, observation_id: int) -> List[Dict[str, Any]]:
        """Get photos for an observation as dictionaries"""
        photos = session.query(Photo).filter(
            Photo.observation_id == observation_id
        ).order_by(Photo.is_primary.desc()).all()

        # Convert to dictionaries
        result = []
        result.extend(
            {
                'id': photo.id,
                'file_path': photo.file_path,
                'is_primary': photo.is_primary,
                'latitude': photo.latitude,
                'longitude': photo.longitude,
                'taken_date': photo.taken_date,
                'width': photo.width,
                'height': photo.height,
            }
            for photo in photos
        )
        return result

    @staticmethod
    def delete_photo_by_id(session: Session, photo_id: int) -> bool:
        """Delete a photo by ID"""
        photo = session.query(Photo).filter_by(id=photo_id).first()
        if not photo:
            return False

        # Use photo manager to delete file
        from services.photo_manager import PhotoManager
        photo_manager = PhotoManager()
        return photo_manager.delete_photo(session, photo)

    @staticmethod
    def update_photo(session: Session, photo_id: int, is_primary: bool = None) -> bool:
        """Update photo properties"""
        photo = session.query(Photo).filter_by(id=photo_id).first()
        if not photo:
            return False

        # Update primary status if specified
        if is_primary is not None and photo.is_primary != is_primary:
            if is_primary:
                # Reset other primary photos for this observation's entry
                observation = session.query(Observation).filter_by(
                    id=photo.observation_id
                ).first()

                if observation:
                    # Get all observations for this entry
                    entry_observations = session.query(Observation.id).filter(
                        Observation.lifelist_id == observation.lifelist_id,
                        Observation.entry_name == observation.entry_name
                    ).all()

                    obs_ids = [obs.id for obs in entry_observations]

                    # Reset primary flag on all photos for this entry
                    session.query(Photo).filter(
                        Photo.observation_id.in_(obs_ids),
                        Photo.id != photo.id
                    ).update({"is_primary": False}, synchronize_session='fetch')

            # Set primary status
            photo.is_primary = is_primary

        return True

    @staticmethod
    def create_photo(session: Session, observation_id: int, file_path: str,
                     is_primary: bool = False, latitude: Optional[float] = None,
                     longitude: Optional[float] = None, taken_date: Optional[Any] = None,
                     width: Optional[int] = None, height: Optional[int] = None) -> Optional[int]:
        """Create a new photo record"""
        try:
            # If this is primary, reset other photos for the same entry
            if is_primary:
                observation = session.query(Observation).filter(
                    Observation.id == observation_id
                ).first()

                if observation:
                    # Get all observations for this entry
                    entry_observations = session.query(Observation.id).filter(
                        Observation.lifelist_id == observation.lifelist_id,
                        Observation.entry_name == observation.entry_name
                    ).all()

                    obs_ids = [obs.id for obs in entry_observations]

                    # Reset primary flag on other photos
                    session.query(Photo).filter(
                        Photo.observation_id.in_(obs_ids),
                        Photo.is_primary == True
                    ).update({"is_primary": False}, synchronize_session='fetch')

            # Create photo record
            photo = Photo(
                observation_id=observation_id,
                file_path=file_path,
                is_primary=is_primary,
                latitude=latitude,
                longitude=longitude,
                taken_date=taken_date,
                width=width,
                height=height
            )

            session.add(photo)
            session.flush()  # To get the ID

            return photo.id
        except Exception as e:
            print(f"Error creating photo: {e}")
            return None

    @staticmethod
    def set_primary_photo(session: Session, photo_id: int) -> bool:
        """Set a photo as the primary photo for its entry"""
        try:
            photo = session.query(Photo).filter(Photo.id == photo_id).first()

            if not photo:
                return False

            # Get observation
            observation = session.query(Observation).filter(
                Observation.id == photo.observation_id
            ).first()

            if not observation:
                return False

            # Get all observations for this entry
            entry_observations = session.query(Observation.id).filter(
                Observation.lifelist_id == observation.lifelist_id,
                Observation.entry_name == observation.entry_name
            ).all()

            obs_ids = [obs.id for obs in entry_observations]

            # Reset primary flag on all photos for this entry
            session.query(Photo).filter(
                Photo.observation_id.in_(obs_ids)
            ).update({"is_primary": False}, synchronize_session='fetch')

            # Set this photo as primary
            photo.is_primary = True

            return True
        except Exception as e:
            print(f"Error setting primary photo: {e}")
            return False

    @staticmethod
    def delete_photo(session: Session, photo_id: int) -> bool:
        """Delete a photo record"""
        try:
            photo = session.query(Photo).filter(Photo.id == photo_id).first()

            if not photo:
                return False

            session.delete(photo)
            return True
        except Exception as e:
            print(f"Error deleting photo: {e}")
            return False


class EquipmentRepository:
    """Repository for Equipment operations"""

    @staticmethod
    def get_equipment(session: Session, equipment_id: int) -> Optional[Equipment]:
        """Get specific equipment by ID"""
        return session.query(Equipment).filter(Equipment.id == equipment_id).first()

    @staticmethod
    def get_all_equipment(session: Session) -> List[Equipment]:
        """Get all equipment"""
        return session.query(Equipment).order_by(Equipment.name).all()

    @staticmethod
    def get_all_equipment_for_display(session: Session) -> List[Dict[str, Any]]:
        """Get all equipment as dictionaries"""
        equipment = session.query(Equipment).order_by(Equipment.name).all()

        result = []
        result.extend(
            {
                'id': eq.id,
                'name': eq.name,
                'type': eq.type,
                'aperture': eq.aperture,
                'focal_length': eq.focal_length,
                'focal_ratio': eq.focal_ratio,
                'sensor_type': eq.sensor_type,
                'pixel_size': eq.pixel_size,
                'resolution': eq.resolution,
                'details': eq.details,
                'purchase_date': eq.purchase_date,
                'notes': eq.notes,
            }
            for eq in equipment
        )
        return result

    @staticmethod
    def get_equipment_by_type(session: Session, equipment_type: str) -> List[Equipment]:
        """Get equipment by type"""
        return session.query(Equipment).filter(Equipment.type == equipment_type).order_by(Equipment.name).all()

    @staticmethod
    def create_equipment(session: Session, name: str, equipment_type: str,
                         specs: Optional[Dict[str, Any]] = None,
                         notes: Optional[str] = None,
                         aperture: Optional[float] = None,
                         focal_length: Optional[float] = None,
                         focal_ratio: Optional[float] = None,
                         sensor_type: Optional[str] = None,
                         pixel_size: Optional[float] = None,
                         resolution: Optional[str] = None,
                         details: Optional[str] = None,
                         purchase_date: Optional[Any] = None) -> Optional[int]:
        """Create new equipment"""
        try:
            equipment = Equipment(
                name=name,
                type=equipment_type,
                specs=specs,
                notes=notes,
                aperture=aperture,
                focal_length=focal_length,
                focal_ratio=focal_ratio,
                sensor_type=sensor_type,
                pixel_size=pixel_size,
                resolution=resolution,
                details=details,
                purchase_date=purchase_date
            )
            session.add(equipment)
            session.flush()  # To get the ID
            return equipment.id
        except Exception as e:
            print(f"Error creating equipment: {e}")
            return None

    @staticmethod
    def update_equipment(session: Session, equipment_id: int, **kwargs) -> bool:
        """Update equipment properties"""
        try:
            equipment = session.query(Equipment).filter(Equipment.id == equipment_id).first()
            if not equipment:
                return False

            # Update provided fields
            for key, value in kwargs.items():
                if hasattr(equipment, key):
                    setattr(equipment, key, value)

            return True
        except Exception as e:
            print(f"Error updating equipment: {e}")
            return False

    @staticmethod
    def delete_equipment(session: Session, equipment_id: int) -> bool:
        """Delete equipment"""
        try:
            equipment = session.query(Equipment).filter(Equipment.id == equipment_id).first()
            if not equipment:
                return False

            session.delete(equipment)
            return True
        except Exception as e:
            print(f"Error deleting equipment: {e}")
            return False

    @staticmethod
    def get_observation_equipment(session: Session, observation_id: int) -> List[Equipment]:
        """Get equipment used for an observation"""
        return session.query(Equipment).join(
            ObservationEquipment, ObservationEquipment.equipment_id == Equipment.id
        ).filter(
            ObservationEquipment.observation_id == observation_id
        ).all()

    @staticmethod
    def set_observation_equipment(session: Session, observation_id: int, equipment_ids: List[int]) -> bool:
        """Set equipment used for an observation"""
        try:
            # Remove existing equipment
            session.query(ObservationEquipment).filter(
                ObservationEquipment.observation_id == observation_id
            ).delete(synchronize_session='fetch')

            # Add new equipment
            for equipment_id in equipment_ids:
                obs_equipment = ObservationEquipment(
                    observation_id=observation_id,
                    equipment_id=equipment_id
                )
                session.add(obs_equipment)

            return True
        except Exception as e:
            print(f"Error setting observation equipment: {e}")
            return False

    @staticmethod
    def get_observation_equipment_for_display(session: Session, observation_id: int) -> List[Dict[str, Any]]:
        """Get equipment for an observation as dictionaries"""
        result = []

        equipment_items = session.query(Equipment).join(
            ObservationEquipment, ObservationEquipment.equipment_id == Equipment.id
        ).filter(
            ObservationEquipment.observation_id == observation_id
        ).all()

        result.extend(
            {
                'id': eq.id,
                'name': eq.name,
                'type': eq.type,
                'aperture': eq.aperture,
                'focal_length': eq.focal_length,
                'focal_ratio': eq.focal_ratio,
                'sensor_type': eq.sensor_type,
                'pixel_size': eq.pixel_size,
                'resolution': eq.resolution,
                'details': eq.details,
                'purchase_date': eq.purchase_date,
                'notes': eq.notes,
            }
            for eq in equipment_items
        )
        return result


class CustomFieldRepository:
    """Repository for CustomField operations"""

    @staticmethod
    def get_custom_fields_by_lifelist(session: Session, lifelist_id: int) -> List[Dict[str, Any]]:
        """Get custom fields for a lifelist as dictionaries"""
        fields = session.query(CustomField).filter_by(
            lifelist_id=lifelist_id
        ).order_by(CustomField.display_order).all()

        result = []
        for field in fields:
            # Convert field_options to Python object if it's a string
            options = field.field_options
            if isinstance(options, str):
                try:
                    options = json.loads(options)
                except (json.JSONDecodeError, TypeError):
                    options = None

            result.append({
                'id': field.id,
                'lifelist_id': field.lifelist_id,
                'field_name': field.field_name,
                'field_type': field.field_type,
                'field_options': options,
                'is_required': field.is_required,
                'display_order': field.display_order
            })

        return result

    @staticmethod
    def get_field_by_name(session: Session, lifelist_id: int, field_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific custom field by name"""
        field = session.query(CustomField).filter_by(
            lifelist_id=lifelist_id,
            field_name=field_name
        ).first()

        if not field:
            return None

        # Convert field_options to Python object if it's a string
        options = field.field_options
        if isinstance(options, str):
            try:
                options = json.loads(options)
            except (json.JSONDecodeError, TypeError):
                options = None

        return {
            'id': field.id,
            'lifelist_id': field.lifelist_id,
            'field_name': field.field_name,
            'field_type': field.field_type,
            'field_options': options,
            'is_required': field.is_required,
            'display_order': field.display_order
        }

class TagRepository:
    """Repository for Tag operations"""

    @staticmethod
    def get_tag(session: Session, tag_id: int) -> Optional[Tag]:
        """Get a tag by ID"""
        return session.query(Tag).filter(Tag.id == tag_id).first()

    @staticmethod
    def get_tag_by_name(session: Session, tag_name: str) -> Optional[Tag]:
        """Get a tag by name"""
        return session.query(Tag).filter(Tag.name == tag_name).first()

    @staticmethod
    def get_tags(session: Session) -> List[Tag]:
        """Get all tags"""
        return session.query(Tag).order_by(Tag.category, Tag.name).all()

    @staticmethod
    def get_tags_by_category(session: Session) -> Dict[Optional[str], List[Tag]]:
        """
        Get tags grouped by category

        Returns:
            Dictionary mapping category names to lists of tags
        """
        tags = session.query(Tag).order_by(Tag.category, Tag.name).all()

        result = {}
        for tag in tags:
            category = tag.category
            if category not in result:
                result[category] = []
            result[category].append(tag)

        return result

    @staticmethod
    def get_observation_tags(session: Session, observation_id: int) -> List[Tag]:
        """Get tags for an observation"""
        observation = session.query(Observation).filter(
            Observation.id == observation_id
        ).first()

        return observation.tags if observation else []

    @staticmethod
    def create_tag(session: Session, name: str, category: Optional[str] = None) -> Optional[int]:
        """Create a new tag"""
        try:
            # Check if tag already exists
            if existing := session.query(Tag).filter(Tag.name == name).first():
                return existing.id

            # Create new tag
            tag = Tag(
                name=name,
                category=category
            )

            session.add(tag)
            session.flush()  # To get the ID

            return tag.id
        except Exception as e:
            print(f"Error creating tag: {e}")
            return None

    @staticmethod
    def update_tag(session: Session, tag_id: int, name: Optional[str] = None,
                   category: Optional[str] = None) -> bool:
        """Update an existing tag"""
        try:
            tag = session.query(Tag).filter(Tag.id == tag_id).first()

            if not tag:
                return False

            if name is not None:
                tag.name = name

            if category is not None:
                tag.category = category

            return True
        except Exception as e:
            print(f"Error updating tag: {e}")
            return False

    @staticmethod
    def update_observation_tags(session: Session, observation_id: int, tag_data: List[Dict[str, str]]) -> bool:
        """Update an observation's tags using a DTO-based approach"""
        # Get the observation
        observation = session.query(Observation).filter_by(id=observation_id).first()
        if not observation:
            return False

        # Clear existing tags
        observation.tags = []

        # Add new tags
        for tag_info in tag_data:
            name = tag_info.get("name")
            category = tag_info.get("category")

            if not name:
                continue

            # Find or create tag
            tag = session.query(Tag).filter_by(name=name).first()

            if not tag:
                tag = Tag(
                    name=name,
                    category=category
                )
                session.add(tag)
                session.flush()

            # Add to observation
            observation.tags.append(tag)

        return True

    @staticmethod
    def delete_tag(session: Session, tag_id: int) -> bool:
        """Delete a tag"""
        try:
            tag = session.query(Tag).filter(Tag.id == tag_id).first()

            if not tag:
                return False

            session.delete(tag)
            return True
        except Exception as e:
            print(f"Error deleting tag: {e}")
            return False

    @staticmethod
    def set_observation_tags(session: Session, observation_id: int, tag_ids: List[int]) -> bool:
        """Set tags for an observation"""
        try:
            observation = session.query(Observation).filter(
                Observation.id == observation_id
            ).first()

            if not observation:
                return False

            # Get tags
            tags = session.query(Tag).filter(Tag.id.in_(tag_ids)).all()

            # Set tags
            observation.tags = tags

            return True
        except Exception as e:
            print(f"Error setting observation tags: {e}")
            return False

    @staticmethod
    def get_tag_hierarchy(session: Session, tag_id: int) -> Tuple[List[Tag], List[Tag]]:
        """
        Get parent and child tags for a tag

        Returns:
            Tuple of (parent_tags, child_tags)
        """
        # Get parent tags
        parent_query = session.query(Tag).join(
            TagHierarchy, TagHierarchy.parent_tag_id == Tag.id
        ).filter(
            TagHierarchy.tag_id == tag_id
        ).order_by(Tag.name)

        parent_tags = parent_query.all()

        # Get child tags
        child_query = session.query(Tag).join(
            TagHierarchy, TagHierarchy.tag_id == Tag.id
        ).filter(
            TagHierarchy.parent_tag_id == tag_id
        ).order_by(Tag.name)

        child_tags = child_query.all()

        return parent_tags, child_tags


class ClassificationRepository:
    """Repository for Classification operations"""

    @staticmethod
    def get_classification(session: Session, classification_id: int) -> Optional[Classification]:
        """Get a classification by ID"""
        return session.query(Classification).filter(
            Classification.id == classification_id
        ).first()

    @staticmethod
    def get_classifications(session: Session, lifelist_id: int) -> List[Classification]:
        """Get all classifications for a lifelist"""
        return session.query(Classification).filter(
            Classification.lifelist_id == lifelist_id
        ).order_by(Classification.name).all()

    @staticmethod
    def get_active_classification(session: Session, lifelist_id: int) -> Optional[Classification]:
        """Get the active classification for a lifelist"""
        return session.query(Classification).filter(
            Classification.lifelist_id == lifelist_id,
            Classification.is_active == True
        ).first()

    @staticmethod
    def create_classification(session: Session, lifelist_id: int, name: str,
                              version: Optional[str] = None, source: Optional[str] = None,
                              description: Optional[str] = None,
                              is_active: bool = False) -> Optional[int]:
        """Create a new classification"""
        try:
            # If this is first classification for the lifelist, make it active
            if not is_active:
                existing = session.query(Classification).filter(
                    Classification.lifelist_id == lifelist_id,
                    Classification.is_active == True
                ).first()

                if not existing:
                    is_active = True

            # Create classification
            classification = Classification(
                lifelist_id=lifelist_id,
                name=name,
                version=version,
                source=source,
                description=description,
                is_active=is_active
            )

            session.add(classification)
            session.flush()  # To get the ID

            return classification.id
        except Exception as e:
            print(f"Error creating classification: {e}")
            return None

    @staticmethod
    def set_active_classification(session: Session, lifelist_id: int, classification_id: int) -> bool:
        """Set a classification as active for a lifelist"""
        try:
            # Reset current active classification
            session.query(Classification).filter(
                Classification.lifelist_id == lifelist_id,
                Classification.is_active == True
            ).update({"is_active": False}, synchronize_session='fetch')

            # Set new active classification
            classification = session.query(Classification).filter(
                Classification.id == classification_id
            ).first()

            if not classification:
                return False

            classification.is_active = True

            return True
        except Exception as e:
            print(f"Error setting active classification: {e}")
            return False

    @staticmethod
    def delete_classification(session: Session, classification_id: int) -> bool:
        """Delete a classification"""
        try:
            classification = session.query(Classification).filter(
                Classification.id == classification_id
            ).first()

            if not classification:
                return False

            # Cannot delete active classification
            if classification.is_active:
                return False

            session.delete(classification)
            return True
        except Exception as e:
            print(f"Error deleting classification: {e}")
            return False

    @staticmethod
    def get_entries(session: Session, classification_id: int) -> List[ClassificationEntry]:
        """Get all entries for a classification"""
        return session.query(ClassificationEntry).filter(
            ClassificationEntry.classification_id == classification_id
        ).order_by(ClassificationEntry.name).all()

    @staticmethod
    def count_entries(session: Session, classification_id: int) -> int:
        """Count entries in a classification"""
        return session.query(ClassificationEntry).filter(
            ClassificationEntry.classification_id == classification_id
        ).count()

    @staticmethod
    def search_entries(session: Session, classification_id: int, search_text: str) -> List[ClassificationEntry]:
        """Search entries in a classification"""
        search_pattern = f"%{search_text}%"

        return session.query(ClassificationEntry).filter(
            ClassificationEntry.classification_id == classification_id,
            or_(
                ClassificationEntry.name.ilike(search_pattern),
                ClassificationEntry.alternate_name.ilike(search_pattern),
                ClassificationEntry.category.ilike(search_pattern),
                ClassificationEntry.code.ilike(search_pattern)
            )
        ).order_by(ClassificationEntry.name).all()

    @staticmethod
    def create_entry(session: Session, classification_id: int, name: str,
                     alternate_name: Optional[str] = None, parent_id: Optional[int] = None,
                     category: Optional[str] = None, code: Optional[str] = None,
                     rank: Optional[str] = None, is_custom: bool = False,
                     additional_data: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """Create a new classification entry"""
        try:
            entry = ClassificationEntry(
                classification_id=classification_id,
                name=name,
                alternate_name=alternate_name,
                parent_id=parent_id,
                category=category,
                code=code,
                rank=rank,
                is_custom=is_custom,
                additional_data=additional_data
            )

            session.add(entry)
            session.flush()  # To get the ID

            return entry.id
        except Exception as e:
            print(f"Error creating classification entry: {e}")
            return None