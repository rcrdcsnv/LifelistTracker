# services/data_service.py
from pathlib import Path
import pandas as pd
import json
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from db.models import (Classification, ClassificationEntry, Lifelist,
                       Observation, ObservationCustomField, CustomField, Tag)
from services.photo_manager import PhotoManager


# Pydantic models for data validation
class CustomFieldValue(BaseModel):
    field_name: str
    value: Optional[str] = None


class TagData(BaseModel):
    name: str
    category: Optional[str] = None


class PhotoData(BaseModel):
    id: Optional[int] = None
    file_name: str
    is_primary: bool = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    taken_date: Optional[datetime] = None


class ObservationData(BaseModel):
    id: Optional[int] = None
    entry_name: str
    observation_date: Optional[datetime] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tier: Optional[str] = None
    notes: Optional[str] = None
    custom_fields: List[CustomFieldValue] = Field(default_factory=list)
    tags: List[TagData] = Field(default_factory=list)
    photos: List[PhotoData] = Field(default_factory=list)


class CustomFieldDefinition(BaseModel):
    id: Optional[int] = None
    name: str
    type: str
    options: Optional[Dict[str, Any]] = None
    required: int = 0
    order: int = 0


class LifelistExportData(BaseModel):
    id: int
    name: str
    classification: Optional[str] = None
    lifelist_type_id: int
    lifelist_type: str
    tiers: List[str]
    custom_fields: List[CustomFieldDefinition] = Field(default_factory=list)
    observations: List[ObservationData] = Field(default_factory=list)


class DataService:
    """Service for importing and exporting lifelist data"""

    def __init__(self, photo_manager: PhotoManager):
        """
        Initialize the data service

        Args:
            photo_manager: PhotoManager instance for handling photos
        """
        self.photo_manager = photo_manager

    def export_lifelist(self, session: Session, lifelist_id: int,
                        export_path: Union[str, Path], include_photos: bool = True,
                        batch_size: int = 100, progress_callback=None) -> bool:
        """Export lifelist using chunked processing for memory efficiency"""
        try:
            export_path = Path(export_path)
            export_path.mkdir(parents=True, exist_ok=True)

            # Get lifelist metadata
            lifelist_data = self._get_lifelist_metadata(session, lifelist_id)
            if not lifelist_data:
                return False

            # Create photos directory
            photos_dir = export_path / "photos"
            if include_photos:
                photos_dir.mkdir(exist_ok=True)

            # Export using streaming JSON
            json_path = export_path / f"{lifelist_data['name']}.json"

            with open(json_path, 'w') as f:
                # Write header
                f.write('{\n')
                f.write(f'  "metadata": {json.dumps(lifelist_data, indent=2)},\n')
                f.write('  "observations": [\n')

                # Export observations in chunks
                offset = 0
                is_first = True
                total_exported = 0

                while True:
                    # Get chunk of observations
                    observations = session.query(Observation).filter(
                        Observation.lifelist_id == lifelist_id
                    ).offset(offset).limit(batch_size).all()

                    if not observations:
                        break

                    for obs in observations:
                        # Serialize observation
                        obs_data = self._serialize_observation(obs, include_photos, photos_dir)

                        # Write to file
                        if not is_first:
                            f.write(',\n')
                        f.write(f'    {json.dumps(obs_data)}')
                        is_first = False
                        total_exported += 1

                    # Clear session cache to free memory
                    session.expire_all()
                    offset += batch_size

                    # Update progress
                    if progress_callback:
                        progress_callback(total_exported)

                # Write footer
                f.write('\n  ]\n}')

            return True

        except Exception as e:
            print(f"Export error: {e}")
            return False

    def _get_lifelist_metadata(self, session: Session, lifelist_id: int) -> Optional[Dict]:
        """Get lifelist metadata for export"""
        from db.repositories import LifelistRepository

        lifelist = LifelistRepository.get_lifelist(session, lifelist_id)
        if not lifelist:
            return None

        # Get tiers
        tiers = LifelistRepository.get_lifelist_tiers(session, lifelist_id)

        # Get custom fields
        custom_fields = session.query(CustomField).filter(
            CustomField.lifelist_id == lifelist_id
        ).order_by(CustomField.display_order).all()

        fields_data = []
        for field in custom_fields:
            field_options = field.field_options
            if isinstance(field_options, str):
                field_options = json.loads(field_options)

            fields_data.append({
                'id': field.id,
                'name': field.field_name,
                'type': field.field_type,
                'options': field_options,
                'required': 1 if field.is_required else 0,
                'order': field.display_order
            })

        # Get lifelist type name
        from db.models import LifelistType
        lifelist_type = session.query(LifelistType).filter(
            LifelistType.id == lifelist[3]
        ).first()

        return {
            'id': lifelist[0],
            'name': lifelist[1],
            'classification': lifelist[2],
            'lifelist_type_id': lifelist[3],
            'lifelist_type': lifelist_type.name if lifelist_type else None,
            'tiers': tiers,
            'custom_fields': fields_data
        }

    def _serialize_observation(self, obs, include_photos, photos_dir):
        """Serialize single observation to dictionary"""
        obs_data = {'id': obs.id, 'entry_name': obs.entry_name,
                    'observation_date': obs.observation_date.isoformat() if obs.observation_date else None,
                    'location': obs.location, 'latitude': obs.latitude, 'longitude': obs.longitude, 'tier': obs.tier,
                    'notes': obs.notes, 'custom_fields': [
                {'field_name': cf.field.field_name, 'value': cf.value}
                for cf in obs.custom_fields
            ], 'tags': [
                {'name': tag.name, 'category': tag.category}
                for tag in obs.tags
            ], 'photos': []}

        # Add relationships

        # Handle photos with copying
        for photo in obs.photos:
            photo_data = self._serialize_photo(photo)

            if include_photos and photo.file_path:
                self._copy_photo_safely(photo.file_path, photos_dir, photo_data['file_name'])

            obs_data['photos'].append(photo_data)

        return obs_data

    def _serialize_photo(self, photo) -> Dict:
        """Serialize photo to dictionary"""
        return {
            'id': photo.id,
            'file_name': Path(photo.file_path).name,
            'is_primary': photo.is_primary,
            'latitude': photo.latitude,
            'longitude': photo.longitude,
            'taken_date': photo.taken_date.isoformat() if photo.taken_date else None
        }

    def _copy_photo_safely(self, source_path: str, photos_dir: Path, filename: str):
        """Safely copy photo file"""
        try:
            source = Path(source_path)
            if source.exists():
                dest = photos_dir / filename
                shutil.copy2(source, dest)
        except Exception as e:
            print(f"Failed to copy photo {source_path}: {e}")

    def import_lifelist(self, session: Session, json_path: Union[str, Path],
                        photos_dir: Optional[Union[str, Path]] = None) -> Tuple[bool, str]:
        """
        Import a lifelist from a JSON file

        Args:
            session: Database session
            json_path: Path to the JSON file
            photos_dir: Optional directory containing photos

        Returns:
            (success, message) tuple
        """
        try:
            json_path = Path(json_path)

            # Load and validate JSON data
            with open(json_path, 'r') as f:
                data = json.load(f)

            lifelist_data = LifelistExportData.model_validate(data)

            # Check if lifelist name already exists
            existing = session.query(Lifelist).filter(
                Lifelist.name == lifelist_data.name
            ).first()

            if existing:
                return False, f"Lifelist '{lifelist_data.name}' already exists"

            # Create the lifelist
            lifelist = Lifelist(
                name=lifelist_data.name,
                lifelist_type_id=lifelist_data.lifelist_type_id,
                classification=lifelist_data.classification
            )
            session.add(lifelist)
            session.flush()  # To get ID

            # Add tiers
            for i, tier_name in enumerate(lifelist_data.tiers):
                lifelist.tiers.append(Lifelist.tiers(
                    tier_name=tier_name,
                    tier_order=i
                ))

            # Add custom fields
            field_id_mapping = {}  # Map old IDs to new IDs
            for field_def in lifelist_data.custom_fields:
                custom_field = CustomField(
                    lifelist_id=lifelist.id,
                    field_name=field_def.name,
                    field_type=field_def.type,
                    field_options=field_def.options,
                    is_required=bool(field_def.required),
                    display_order=field_def.order
                )
                session.add(custom_field)
                session.flush()

                if field_def.id is not None:
                    field_id_mapping[field_def.id] = custom_field.id

            # Add observations
            for obs_data in lifelist_data.observations:
                observation = Observation(
                    lifelist_id=lifelist.id,
                    entry_name=obs_data.entry_name,
                    observation_date=obs_data.observation_date,
                    location=obs_data.location,
                    latitude=obs_data.latitude,
                    longitude=obs_data.longitude,
                    tier=obs_data.tier,
                    notes=obs_data.notes
                )
                session.add(observation)
                session.flush()

                # Add custom field values
                for cf_value in obs_data.custom_fields:
                    # Find the field by name
                    field = next((f for f in lifelist.custom_fields
                                  if f.field_name == cf_value.field_name), None)

                    if field and cf_value.value:
                        observation.custom_fields.append(ObservationCustomField(
                            field_id=field.id,
                            value=cf_value.value
                        ))

                # Add tags
                for tag_data in obs_data.tags:
                    # Find or create tag
                    tag = session.query(Tag).filter(
                        Tag.name == tag_data.name
                    ).first()

                    if not tag:
                        tag = Tag(
                            name=tag_data.name,
                            category=tag_data.category
                        )
                        session.add(tag)
                        session.flush()

                    observation.tags.append(tag)

                # Add photos if photos_dir is provided
                if photos_dir:
                    photos_dir = Path(photos_dir)
                    for photo_data in obs_data.photos:
                        photo_path = photos_dir / photo_data.file_name
                        if photo_path.exists():
                            self.photo_manager.store_photo(
                                session,
                                observation.id,
                                photo_path,
                                is_primary=photo_data.is_primary
                            )

            session.commit()
            return True, f"Successfully imported lifelist '{lifelist_data.name}'"

        except Exception as e:
            session.rollback()
            return False, f"Error importing lifelist: {str(e)}"

    def import_classification(self, session: Session, lifelist_id: int,
                              name: str, file_path: Union[str, Path],
                              field_mappings: Dict[str, str],
                              version: Optional[str] = None,
                              source: Optional[str] = None) -> Tuple[bool, int]:
        """
        Import a classification from a CSV file

        Args:
            session: Database session
            lifelist_id: ID of the lifelist to add classification to
            name: Name of the classification
            file_path: Path to the CSV file
            field_mappings: Dictionary mapping database fields to CSV columns
            version: Optional version information
            source: Optional source information

        Returns:
            (success, count) tuple
        """
        try:
            # Create the classification
            classification = Classification(
                lifelist_id=lifelist_id,
                name=name,
                version=version,
                source=source,
                is_active=False  # Will be set active if it's the first classification
            )
            session.add(classification)
            session.flush()

            # Check if this should be the active classification
            active_classification = session.query(Classification).filter(
                Classification.lifelist_id == lifelist_id,
                Classification.is_active == True
            ).first()

            if not active_classification:
                classification.is_active = True

            # Read CSV with pandas
            df = pd.read_csv(file_path)

            # Process each row
            count = 0
            for _, row in df.iterrows():
                entry_data = {}

                # Map CSV fields to database fields
                for db_field, csv_field in field_mappings.items():
                    if csv_field and csv_field in df.columns:
                        value = row[csv_field]
                        if pd.notna(value):
                            entry_data[db_field] = str(value)

                # Check if we have at least a name
                if "name" in entry_data and entry_data["name"]:
                    # Collect additional data (unmapped columns)
                    additional_data = {
                        column: str(row[column])
                        for column in df.columns
                        if column not in field_mappings.values()
                        and pd.notna(row[column])
                    }
                    # Add the entry
                    entry = ClassificationEntry(
                        classification_id=classification.id,
                        name=entry_data.get("name"),
                        alternate_name=entry_data.get("alternate_name"),
                        parent_id=entry_data.get("parent_id"),
                        category=entry_data.get("category"),
                        code=entry_data.get("code"),
                        rank=entry_data.get("rank"),
                        is_custom=False,
                        additional_data=additional_data if additional_data else None
                    )
                    session.add(entry)
                    count += 1

            session.commit()
            return True, count

        except Exception as e:
            session.rollback()
            print(f"Error importing classification: {e}")
            return False, 0