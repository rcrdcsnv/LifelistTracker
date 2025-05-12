# services/photo_manager.py
from pathlib import Path
from PIL import Image
import shutil
from typing import Optional, Union
from utils.cache import LRUCache
from utils.image import extract_exif_data
from db.models import Photo, Observation
from sqlalchemy.orm import Session


class PhotoManager:
    """Manages photo storage, retrieval, and caching"""

    def __init__(self, base_path: Union[str, Path] = "storage", cache_size: int = 100):
        """
        Initialize the photo manager

        Args:
            base_path: Base directory for photo storage
            cache_size: Maximum number of images to cache in memory
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.image_cache = LRUCache[str, Image.Image](cache_size)

        # Create standard thumbnail sizes
        self.thumbnail_sizes = {
            "xs": (60, 60),  # Tiny thumbnail for tables/lists
            "sm": (100, 100),  # Small thumbnail
            "md": (300, 200),  # Medium thumbnail for galleries
            "lg": (600, 400)  # Large thumbnail for primary view
        }

    def get_photo_path(self, lifelist_id: int, observation_id: int,
                       photo_id: int, filename: str) -> Path:
        """Get the path where an original photo should be stored"""
        photo_dir = self._get_photo_directory(lifelist_id, observation_id)
        return photo_dir / "original" / f"{photo_id}_{filename}"

    def get_thumbnail_path(self, lifelist_id: int, observation_id: int,
                           photo_id: int, size: str = "sm") -> Path:
        """Get the path where a thumbnail should be stored"""
        if size not in self.thumbnail_sizes:
            size = "sm"

        photo_dir = self._get_photo_directory(lifelist_id, observation_id)
        return photo_dir / "thumbnails" / f"{photo_id}_{size}.jpg"

    def _get_photo_directory(self, lifelist_id: int, observation_id: int) -> Path:
        """Get the directory structure for a photo"""
        directory = self.base_path / f"lifelist_{lifelist_id}" / f"observation_{observation_id}"
        # Ensure directories exist
        (directory / "original").mkdir(parents=True, exist_ok=True)
        (directory / "thumbnails").mkdir(parents=True, exist_ok=True)
        return directory

    def store_photo(self, session: Session, observation_id: int, file_path: Union[str, Path],
                    is_primary: bool = False) -> Optional[Photo]:
        """
        Store a photo for an observation without creating duplicates

        Args:
            session: Database session
            observation_id: ID of the observation
            file_path: Path to the photo file
            is_primary: Whether this is the primary photo for the entry

        Returns:
            Photo object if successful, None otherwise
        """
        try:
            # Get the observation to determine lifelist_id
            observation = session.query(Observation).filter(
                Observation.id == observation_id
            ).first()

            if not observation:
                return None

            # Check if this file is already stored for this observation
            file_path = Path(file_path)
            existing_photos = session.query(Photo).filter(
                Photo.observation_id == observation_id
            ).all()

            for existing_photo in existing_photos:
                if Path(existing_photo.file_path).name == file_path.name:
                    # Update primary status if needed
                    if is_primary != existing_photo.is_primary:
                        existing_photo.is_primary = is_primary
                    return existing_photo

            # Extract EXIF data
            lat, lon, taken_date = extract_exif_data(file_path)

            # Create Photo record
            photo = Photo(
                observation_id=observation_id,
                file_path="",  # Will be updated after saving the file
                is_primary=is_primary,
                latitude=lat,
                longitude=lon,
                taken_date=taken_date
            )

            session.add(photo)
            session.flush()  # To get the ID

            # If this is primary, reset others
            if is_primary:
                # Reset is_primary for other photos of the same entry
                entry_observations = session.query(Observation.id).filter(
                    Observation.lifelist_id == observation.lifelist_id,
                    Observation.entry_name == observation.entry_name
                ).all()

                obs_ids = [obs.id for obs in entry_observations]

                session.query(Photo).filter(
                    Photo.observation_id.in_(obs_ids),
                    Photo.id != photo.id
                ).update({"is_primary": False}, synchronize_session='fetch')

            # Copy the file to storage location
            filename = file_path.name
            dest_path = self.get_photo_path(
                observation.lifelist_id, observation_id, photo.id, filename
            )

            # Ensure directory exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy the file
            shutil.copy2(file_path, dest_path)

            # Update the file_path in the database
            photo.file_path = str(dest_path)

            # Create thumbnails
            with Image.open(file_path) as img:
                photo.width = img.width
                photo.height = img.height

                for size_name, dimensions in self.thumbnail_sizes.items():
                    thumb_path = self.get_thumbnail_path(
                        observation.lifelist_id, observation_id, photo.id, size_name
                    )
                    img_copy = img.copy()
                    img_copy.thumbnail(dimensions)
                    img_copy.save(thumb_path, "JPEG", quality=85)

            return photo

        except Exception as e:
            print(f"Error storing photo: {e}")
            return None

    def get_photo_thumbnail(self, lifelist_id: int, observation_id: int,
                            photo_id: int, size: str = "sm") -> Optional[Image.Image]:
        """
        Get a photo thumbnail, using cache if available

        Args:
            lifelist_id: ID of the lifelist
            observation_id: ID of the observation
            photo_id: ID of the photo
            size: Size of the thumbnail ("xs", "sm", "md", "lg")

        Returns:
            PIL Image if successful, None otherwise
        """
        cache_key = f"{lifelist_id}_{observation_id}_{photo_id}_{size}"

        # Check cache first
        if cached_image := self.image_cache.get(cache_key):
            return cached_image

        # Load from disk
        try:
            thumb_path = self.get_thumbnail_path(lifelist_id, observation_id, photo_id, size)
            if not thumb_path.exists():
                return None

            image = Image.open(thumb_path)
            # Store in cache
            self.image_cache.put(cache_key, image)
            return image
        except Exception as e:
            print(f"Error loading thumbnail: {e}")
            return None

    def delete_photo(self, session: Session, photo: Photo) -> bool:
        """
        Delete a photo and all its thumbnails

        Args:
            session: Database session
            photo: Photo object to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get observation for lifelist_id
            observation = session.query(Observation).filter(
                Observation.id == photo.observation_id
            ).first()

            if not observation:
                return False

            # Delete thumbnails
            for size in self.thumbnail_sizes:
                thumb_path = self.get_thumbnail_path(
                    observation.lifelist_id, photo.observation_id, photo.id, size
                )
                if thumb_path.exists():
                    thumb_path.unlink()

            # Delete original
            if photo.file_path:
                original_path = Path(photo.file_path)
                if original_path.exists():
                    original_path.unlink()

            # Remove from database
            session.delete(photo)

            # Clean up caches
            for size in self.thumbnail_sizes:
                cache_key = f"{observation.lifelist_id}_{photo.observation_id}_{photo.id}_{size}"
                if cache_key in self.image_cache:
                    # Remove from cache
                    self.image_cache.cache.pop(cache_key, None)

            return True
        except Exception as e:
            print(f"Error deleting photo: {e}")
            return False

    def regenerate_thumbnails(self, photo, session=None):
        """Regenerate thumbnails for a photo after rotation or other changes"""
        try:
            # Extract photo information
            photo_id = photo.id
            observation_id = photo.observation_id

            # Get the observation to determine lifelist_id
            from db.models import Observation

            if session:
                # Use provided session
                observation = session.query(Observation).filter(
                    Observation.id == observation_id
                ).first()
            else:
                # Create a new session if none provided (less ideal)
                from db.base import DatabaseManager
                temp_session = DatabaseManager.get_instance().Session()
                try:
                    observation = temp_session.query(Observation).filter(
                        Observation.id == observation_id
                    ).first()
                finally:
                    temp_session.close()

            if not observation:
                return False

            lifelist_id = observation.lifelist_id

            # Get file path
            file_path = photo.file_path
            if not Path(file_path).exists():
                return False

            # Generate new thumbnails
            with Image.open(file_path) as img:
                for size_name, dimensions in self.thumbnail_sizes.items():
                    thumb_path = self.get_thumbnail_path(
                        lifelist_id, observation_id, photo_id, size_name
                    )
                    img_copy = img.copy()
                    img_copy.thumbnail(dimensions)
                    img_copy.save(thumb_path, "JPEG", quality=85)

                # Update image dimensions in database
                photo.width = img.width
                photo.height = img.height

            # Clear from cache
            for size in self.thumbnail_sizes:
                cache_key = f"{lifelist_id}_{observation_id}_{photo_id}_{size}"
                if cache_key in self.image_cache:
                    self.image_cache.cache.pop(cache_key, None)

            return True

        except Exception as e:
            print(f"Error regenerating thumbnails: {e}")
            return False