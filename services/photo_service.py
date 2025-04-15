# services/photo_service.py
"""
Photo Service - Handles operations related to photos
"""
from typing import List, Optional, Dict, Any, Tuple
from LifelistTracker.models.photo import Photo
from LifelistTracker.services.database_service import IDatabaseService


class IPhotoService:
    """Interface for photo service"""

    def get_photo(self, photo_id: int) -> Optional[Photo]:
        pass

    def get_observation_photos(self, observation_id: int) -> List[Photo]:
        pass

    def species_has_primary_photo(self, lifelist_id: int, species_name: str) -> bool:
        pass

    def get_species_primary_photo(self, lifelist_id: int, species_name: str) -> Optional[Dict[str, Any]]:
        pass

    def get_primary_photo_for_species(self, lifelist_id: int, species_name: str) -> Optional[Photo]:
        pass

    def add_photo(self, photo: Photo) -> Optional[int]:
        pass

    def set_primary_photo(self, photo_id: int, observation_id: int) -> bool:
        pass

    def delete_photo(self, photo_id: int) -> Tuple[bool, Optional[str]]:
        pass


class PhotoService(IPhotoService):
    """Service for photo operations"""

    def __init__(self, database_service: IDatabaseService):
        self.db = database_service

    def get_photo(self, photo_id: int) -> Optional[Photo]:
        """
        Get a photo by ID

        Args:
            photo_id: ID of the photo to get

        Returns:
            Photo if found, None otherwise
        """
        query = """
        SELECT id, observation_id, file_path, is_primary, latitude, longitude, taken_date
        FROM photos WHERE id = ?
        """
        results = self.db.execute_query(query, (photo_id,))

        if not results:
            return None

        return Photo.from_dict(results[0])

    def get_observation_photos(self, observation_id: int) -> List[Photo]:
        """
        Get all photos for an observation

        Args:
            observation_id: ID of the observation

        Returns:
            List of Photo objects
        """
        query = """
        SELECT id, observation_id, file_path, is_primary, latitude, longitude, taken_date
        FROM photos WHERE observation_id = ?
        """
        results = self.db.execute_query(query, (observation_id,))

        return [Photo.from_dict(result) for result in results]

    def species_has_primary_photo(self, lifelist_id: int, species_name: str) -> bool:
        """
        Check if a species already has a primary photo set

        Args:
            lifelist_id: ID of the lifelist
            species_name: Name of the species

        Returns:
            True if species has a primary photo, False otherwise
        """
        query = """
        SELECT COUNT(*) as count FROM photos p
        JOIN observations o ON p.observation_id = o.id
        WHERE o.lifelist_id = ? AND o.species_name = ? AND p.is_primary = 1
        """
        results = self.db.execute_query(query, (lifelist_id, species_name))

        if not results:
            return False

        return results[0]['count'] > 0

    def get_species_primary_photo(self, lifelist_id: int, species_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the primary photo for a species across all observations

        Args:
            lifelist_id: ID of the lifelist
            species_name: Name of the species

        Returns:
            Dictionary with photo data, or None if no photo found
        """
        query = """
        SELECT p.id, p.file_path, p.is_primary, p.latitude, p.longitude, p.taken_date, o.id as observation_id
        FROM photos p
        JOIN observations o ON p.observation_id = o.id
        WHERE o.lifelist_id = ? AND o.species_name = ? AND p.is_primary = 1
        ORDER BY p.id DESC
        LIMIT 1
        """
        results = self.db.execute_query(query, (lifelist_id, species_name))

        if results:
            return results[0]

        # If no primary photo is set, find any photo for this species
        query = """
        SELECT p.id, p.file_path, p.is_primary, p.latitude, p.longitude, p.taken_date, o.id as observation_id
        FROM photos p
        JOIN observations o ON p.observation_id = o.id
        WHERE o.lifelist_id = ? AND o.species_name = ?
        LIMIT 1
        """
        results = self.db.execute_query(query, (lifelist_id, species_name))

        if results:
            return results[0]

        return None

    def get_primary_photo_for_species(self, lifelist_id: int, species_name: str) -> Optional[Photo]:
        """
        Get the primary photo for a species

        Args:
            lifelist_id: ID of the lifelist
            species_name: Name of the species

        Returns:
            Photo if found, None otherwise
        """
        photo_data = self.get_species_primary_photo(lifelist_id, species_name)

        if not photo_data:
            return None

        return Photo.from_dict(photo_data)

    def add_photo(self, photo: Photo) -> Optional[int]:
        """
        Add a photo to an observation

        Args:
            photo: Photo to add

        Returns:
            ID of the new photo, or None if adding failed
        """
        try:
            def transaction_func():
                # Get the species and lifelist for this observation
                query = "SELECT species_name, lifelist_id FROM observations WHERE id = ?"
                results = self.db.execute_query(query, (photo.observation_id,))

                if not results:
                    raise Exception("Observation not found")

                species_name = results[0]['species_name']
                lifelist_id = results[0]['lifelist_id']

                # If this is being set as primary, reset all other photos for this species
                if photo.is_primary:
                    # Get all observations for this species
                    species_obs_query = "SELECT id FROM observations WHERE lifelist_id = ? AND species_name = ?"
                    species_obs_results = self.db.execute_query(species_obs_query, (lifelist_id, species_name))
                    species_obs_ids = [row['id'] for row in species_obs_results]

                    # Reset all primary photos for this species
                    for obs_id in species_obs_ids:
                        self.db.execute_non_query(
                            "UPDATE photos SET is_primary = 0 WHERE observation_id = ?",
                            (obs_id,)
                        )

                # Insert the new photo
                photo_id = self.db.execute_non_query(
                    """INSERT INTO photos 
                    (observation_id, file_path, is_primary, latitude, longitude, taken_date) 
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (photo.observation_id, photo.file_path, 1 if photo.is_primary else 0,
                     photo.latitude, photo.longitude, photo.taken_date)
                )

                return photo_id

            return self.db.execute_transaction(transaction_func)

        except Exception as e:
            print(f"Error adding photo: {e}")
            return None

    def set_primary_photo(self, photo_id: int, observation_id: int) -> bool:
        """
        Set a photo as the primary photo for a species

        Args:
            photo_id: ID of the photo to set as primary
            observation_id: ID of the observation

        Returns:
            True if setting succeeded, False otherwise
        """
        try:
            def transaction_func():
                # Get the species name and lifelist_id for this observation
                query = "SELECT species_name, lifelist_id FROM observations WHERE id = ?"
                results = self.db.execute_query(query, (observation_id,))

                if not results:
                    return False

                species_name = results[0]['species_name']
                lifelist_id = results[0]['lifelist_id']

                # Get all observations for this species
                species_obs_query = "SELECT id FROM observations WHERE lifelist_id = ? AND species_name = ?"
                species_obs_results = self.db.execute_query(species_obs_query, (lifelist_id, species_name))
                all_obs_ids = [row['id'] for row in species_obs_results]

                # Reset primary flag for all photos of this species
                for obs_id in all_obs_ids:
                    self.db.execute_non_query("UPDATE photos SET is_primary = 0 WHERE observation_id = ?", (obs_id,))

                # Set the selected photo as primary
                self.db.execute_non_query("UPDATE photos SET is_primary = 1 WHERE id = ?", (photo_id,))

                return True

            return self.db.execute_transaction(transaction_func)

        except Exception as e:
            print(f"Error setting primary photo: {e}")
            return False

    def delete_photo(self, photo_id: int) -> Tuple[bool, Optional[str]]:
        """
        Delete a photo

        Args:
            photo_id: ID of the photo to delete

        Returns:
            Tuple of (success, file path)
        """
        try:
            def transaction_func():
                # First, get the photo details
                query = "SELECT file_path, is_primary, observation_id FROM photos WHERE id = ?"
                results = self.db.execute_query(query, (photo_id,))

                if not results:
                    return False, None

                file_path = results[0]['file_path']
                is_primary = bool(results[0]['is_primary'])
                observation_id = results[0]['observation_id']

                # Delete the photo
                self.db.execute_non_query("DELETE FROM photos WHERE id = ?", (photo_id,))

                # If this was the primary photo, set another as primary
                if is_primary:
                    next_photo_query = """
                    SELECT id FROM photos WHERE observation_id = ? ORDER BY id LIMIT 1
                    """
                    next_photo_results = self.db.execute_query(next_photo_query, (observation_id,))

                    if next_photo_results:
                        next_photo_id = next_photo_results[0]['id']
                        self.db.execute_non_query("UPDATE photos SET is_primary = 1 WHERE id = ?", (next_photo_id,))

                return True, file_path

            return self.db.execute_transaction(transaction_func)

        except Exception as e:
            print(f"Error deleting photo: {e}")
            return False, None