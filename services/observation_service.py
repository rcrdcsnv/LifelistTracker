# services/observation_service.py
"""
Observation Service - Handles operations related to observations
"""
from typing import List, Optional, Dict, Any, Tuple
from LifelistTracker.models.observation import Observation
from LifelistTracker.models.photo import Photo
from LifelistTracker.models.tag import Tag
from LifelistTracker.services.database_service import IDatabaseService


class IObservationService:
    """Interface for observation service"""

    def get_observation(self, observation_id: int) -> Optional[Observation]:
        pass

    def get_filtered_observations(self, lifelist_id: int, tier: Optional[str] = None,
                                  tag_ids: Optional[List[int]] = None,
                                  search_term: Optional[str] = None) -> List[Dict[str, Any]]:
        pass

    def get_observations_by_species(self, lifelist_id: int, species_name: str) -> List[int]:
        pass

    def add_observation(self, observation: Observation) -> Optional[int]:
        pass

    def update_observation(self, observation: Observation) -> bool:
        pass

    def delete_observation(self, observation_id: int) -> Tuple[bool, List[str]]:
        pass

    def get_all_tags(self) -> List[Tag]:
        pass

    def get_observation_tags(self, observation_id: int) -> List[Tag]:
        pass

    def add_tag(self, tag_name: str) -> int:
        pass

    def add_tag_to_observation(self, observation_id: int, tag_id: int) -> bool:
        pass

    def remove_tag_from_observation(self, observation_id: int, tag_id: int) -> bool:
        pass


class ObservationService(IObservationService):
    """Service for observation operations"""

    def __init__(self, database_service: IDatabaseService):
        self.db = database_service

    def get_observation(self, observation_id: int) -> Optional[Observation]:
        """
        Get an observation by ID with all related data

        Args:
            observation_id: ID of the observation to get

        Returns:
            Observation if found, None otherwise
        """
        query = """
        SELECT id, lifelist_id, species_name, observation_date, location, 
               latitude, longitude, tier, notes, created_at 
        FROM observations WHERE id = ?
        """
        results = self.db.execute_query(query, (observation_id,))

        if not results:
            return None

        observation = Observation.from_dict(results[0])

        # Load custom field values
        custom_fields_query = """
        SELECT ocf.id, ocf.observation_id, ocf.field_id, ocf.value,
               cf.field_name, cf.field_type
        FROM observation_custom_fields ocf
        JOIN custom_fields cf ON ocf.field_id = cf.id
        WHERE ocf.observation_id = ?
        """
        custom_field_values = self.db.execute_query(custom_fields_query, (observation_id,))
        observation.custom_field_values = custom_field_values

        # Load tags
        tags_query = """
        SELECT t.id, t.name
        FROM tags t
        JOIN observation_tags ot ON t.id = ot.tag_id
        WHERE ot.observation_id = ?
        """
        tag_results = self.db.execute_query(tags_query, (observation_id,))
        observation.tags = [Tag.from_dict(tag) for tag in tag_results]

        # Load photos
        photos_query = """
        SELECT id, observation_id, file_path, is_primary, latitude, longitude, taken_date
        FROM photos
        WHERE observation_id = ?
        """
        photo_results = self.db.execute_query(photos_query, (observation_id,))
        observation.photos = [Photo.from_dict(photo) for photo in photo_results]

        return observation

    def get_filtered_observations(self, lifelist_id: int, tier: Optional[str] = None,
                                  tag_ids: Optional[List[int]] = None,
                                  search_term: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get observations with optional filtering

        Args:
            lifelist_id: ID of the lifelist
            tier: Optional tier to filter by
            tag_ids: Optional list of tag IDs to filter by
            search_term: Optional search term to filter by

        Returns:
            List of observation dictionaries
        """
        query = """
        SELECT id, species_name, observation_date, location, tier
        FROM observations
        WHERE lifelist_id = ?
        """
        params = [lifelist_id]

        if tier:
            query += " AND tier = ?"
            params.append(tier)

        if search_term:
            query += " AND (species_name LIKE ? OR notes LIKE ? OR location LIKE ?)"
            search_param = f"%{search_term}%"
            params.extend([search_param, search_param, search_param])

        if tag_ids and len(tag_ids) > 0:
            placeholders = ','.join(['?' for _ in tag_ids])
            query = f"""
            SELECT o.id, o.species_name, o.observation_date, o.location, o.tier
            FROM observations o
            JOIN observation_tags ot ON o.id = ot.observation_id
            WHERE o.lifelist_id = ? AND ot.tag_id IN ({placeholders})
            GROUP BY o.id
            HAVING COUNT(DISTINCT ot.tag_id) = ?
            """
            params = [lifelist_id] + tag_ids + [len(tag_ids)]

        query += " ORDER BY observation_date DESC"

        results = self.db.execute_query(query, tuple(params))
        return results

    def get_observations_by_species(self, lifelist_id: int, species_name: str) -> List[int]:
        """
        Get all observations of a specific species in a lifelist

        Args:
            lifelist_id: ID of the lifelist
            species_name: Name of the species

        Returns:
            List of observation IDs
        """
        query = "SELECT id FROM observations WHERE lifelist_id = ? AND species_name = ?"
        results = self.db.execute_query(query, (lifelist_id, species_name))
        return [result['id'] for result in results]

    def add_observation(self, observation: Observation) -> Optional[int]:
        """
        Add a new observation

        Args:
            observation: Observation to add

        Returns:
            ID of the new observation, or None if adding failed
        """
        try:
            def transaction_func():
                # Insert the observation
                query = """
                INSERT INTO observations 
                (lifelist_id, species_name, observation_date, location, latitude, longitude, tier, notes) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    observation.lifelist_id,
                    observation.species_name,
                    observation.observation_date,
                    observation.location,
                    observation.latitude,
                    observation.longitude,
                    observation.tier,
                    observation.notes
                )
                observation_id = self.db.execute_non_query(query, params)

                if observation_id <= 0:
                    raise Exception("Failed to insert observation")

                # Add custom field values
                for field in observation.custom_field_values:
                    self.db.execute_non_query(
                        "INSERT INTO observation_custom_fields (observation_id, field_id, value) VALUES (?, ?, ?)",
                        (observation_id, field.get('field_id'), field.get('value'))
                    )

                # Add tags
                for tag in observation.tags:
                    tag_id = self.add_tag(tag.name)
                    self.add_tag_to_observation(observation_id, tag_id)

                # Add photos
                for photo in observation.photos:
                    photo.observation_id = observation_id
                    self.db.execute_non_query(
                        """INSERT INTO photos 
                        (observation_id, file_path, is_primary, latitude, longitude, taken_date) 
                        VALUES (?, ?, ?, ?, ?, ?)""",
                        (observation_id, photo.file_path, 1 if photo.is_primary else 0,
                         photo.latitude, photo.longitude, photo.taken_date)
                    )

                return observation_id

            return self.db.execute_transaction(transaction_func)

        except Exception as e:
            print(f"Error adding observation: {e}")
            return None

    def update_observation(self, observation: Observation) -> bool:
        """
        Update an existing observation

        Args:
            observation: Observation with updated data

        Returns:
            True if update succeeded, False otherwise
        """
        try:
            def transaction_func():
                # Update the observation
                query = """
                UPDATE observations SET
                species_name = ?, observation_date = ?, location = ?, 
                latitude = ?, longitude = ?, tier = ?, notes = ?
                WHERE id = ?
                """
                params = (
                    observation.species_name,
                    observation.observation_date,
                    observation.location,
                    observation.latitude,
                    observation.longitude,
                    observation.tier,
                    observation.notes,
                    observation.id
                )
                self.db.execute_non_query(query, params)

                # Update custom field values
                self.db.execute_non_query(
                    "DELETE FROM observation_custom_fields WHERE observation_id = ?",
                    (observation.id,)
                )

                for field in observation.custom_field_values:
                    self.db.execute_non_query(
                        "INSERT INTO observation_custom_fields (observation_id, field_id, value) VALUES (?, ?, ?)",
                        (observation.id, field.get('field_id'), field.get('value'))
                    )

                # Update tags
                self.db.execute_non_query(
                    "DELETE FROM observation_tags WHERE observation_id = ?",
                    (observation.id,)
                )

                for tag in observation.tags:
                    tag_id = self.add_tag(tag.name)
                    self.add_tag_to_observation(observation.id, tag_id)

                # Handle photos (keep track of which ones to delete)
                existing_photos = self.db.execute_query(
                    "SELECT id FROM photos WHERE observation_id = ?",
                    (observation.id,)
                )
                existing_photo_ids = [photo['id'] for photo in existing_photos]
                kept_photo_ids = []

                # Update existing photos and add new ones
                for photo in observation.photos:
                    if photo.id:
                        # Existing photo
                        kept_photo_ids.append(photo.id)
                        self.db.execute_non_query(
                            "UPDATE photos SET is_primary = ? WHERE id = ?",
                            (1 if photo.is_primary else 0, photo.id)
                        )
                    else:
                        # New photo
                        self.db.execute_non_query(
                            """INSERT INTO photos 
                            (observation_id, file_path, is_primary, latitude, longitude, taken_date) 
                            VALUES (?, ?, ?, ?, ?, ?)""",
                            (observation.id, photo.file_path, 1 if photo.is_primary else 0,
                             photo.latitude, photo.longitude, photo.taken_date)
                        )

                # Delete photos that were removed
                photos_to_delete = [pid for pid in existing_photo_ids if pid not in kept_photo_ids]
                for photo_id in photos_to_delete:
                    self.db.execute_non_query("DELETE FROM photos WHERE id = ?", (photo_id,))

                return True

            return self.db.execute_transaction(transaction_func)

        except Exception as e:
            print(f"Error updating observation: {e}")
            return False

    def delete_observation(self, observation_id: int) -> Tuple[bool, List[str]]:
        """
        Delete an observation

        Args:
            observation_id: ID of the observation to delete

        Returns:
            Tuple of (success, list of photo file paths)
        """
        try:
            def transaction_func():
                # Get the photo file paths first
                photos_query = "SELECT file_path FROM photos WHERE observation_id = ?"
                photos = self.db.execute_query(photos_query, (observation_id,))
                photo_paths = [photo['file_path'] for photo in photos]

                # Delete the observation (cascades to other tables)
                self.db.execute_non_query("DELETE FROM observations WHERE id = ?", (observation_id,))

                return True, photo_paths

            return self.db.execute_transaction(transaction_func)

        except Exception as e:
            print(f"Error deleting observation: {e}")
            return False, []

    def get_all_tags(self) -> List[Tag]:
        """
        Get all tags

        Returns:
            List of Tag objects
        """
        query = "SELECT id, name FROM tags ORDER BY name"
        results = self.db.execute_query(query)
        return [Tag.from_dict(result) for result in results]

    def get_observation_tags(self, observation_id: int) -> List[Tag]:
        """
        Get all tags for an observation

        Args:
            observation_id: ID of the observation

        Returns:
            List of Tag objects
        """
        query = """
        SELECT t.id, t.name FROM tags t
        JOIN observation_tags ot ON t.id = ot.tag_id
        WHERE ot.observation_id = ?
        """
        results = self.db.execute_query(query, (observation_id,))
        return [Tag.from_dict(result) for result in results]

    def add_tag(self, tag_name: str) -> int:
        """
        Add a tag or get existing tag ID

        Args:
            tag_name: Name of the tag

        Returns:
            ID of the tag
        """
        # Check if tag already exists
        query = "SELECT id FROM tags WHERE name = ?"
        results = self.db.execute_query(query, (tag_name,))

        if results:
            return results[0]['id']

        # Insert new tag
        tag_id = self.db.execute_non_query("INSERT INTO tags (name) VALUES (?)", (tag_name,))
        return tag_id

    def add_tag_to_observation(self, observation_id: int, tag_id: int) -> bool:
        """
        Add a tag to an observation

        Args:
            observation_id: ID of the observation
            tag_id: ID of the tag

        Returns:
            True if adding succeeded, False otherwise
        """
        try:
            # Check if the tag is already associated with this observation
            query = "SELECT 1 FROM observation_tags WHERE observation_id = ? AND tag_id = ?"
            results = self.db.execute_query(query, (observation_id, tag_id))

            if results:
                return True  # Already associated

            # Add the association
            self.db.execute_non_query(
                "INSERT INTO observation_tags (observation_id, tag_id) VALUES (?, ?)",
                (observation_id, tag_id)
            )
            return True

        except Exception as e:
            print(f"Error adding tag to observation: {e}")
            return False

    def remove_tag_from_observation(self, observation_id: int, tag_id: int) -> bool:
        """
        Remove a tag from an observation

        Args:
            observation_id: ID of the observation
            tag_id: ID of the tag

        Returns:
            True if removal succeeded, False otherwise
        """
        try:
            self.db.execute_non_query(
                "DELETE FROM observation_tags WHERE observation_id = ? AND tag_id = ?",
                (observation_id, tag_id)
            )
            return True

        except Exception as e:
            print(f"Error removing tag from observation: {e}")
            return False