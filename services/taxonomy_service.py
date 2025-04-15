# services/taxonomy_service.py
"""
Taxonomy Service - Handles operations related to taxonomies
"""
from typing import List, Optional, Dict
import json
from LifelistTracker.models.taxonomy import Taxonomy, TaxonomyEntry
from LifelistTracker.services.database_service import IDatabaseService


class ITaxonomyService:
    """Interface for taxonomy service"""

    def get_taxonomy(self, taxonomy_id: int) -> Optional[Taxonomy]:
        pass

    def get_taxonomies(self, lifelist_id: int) -> List[Taxonomy]:
        pass

    def get_active_taxonomy(self, lifelist_id: int) -> Optional[Taxonomy]:
        pass

    def add_taxonomy(self, taxonomy: Taxonomy) -> Optional[int]:
        pass

    def set_active_taxonomy(self, taxonomy_id: int, lifelist_id: int) -> bool:
        pass

    def delete_taxonomy(self, taxonomy_id: int) -> bool:
        pass

    def add_taxonomy_entry(self, entry: TaxonomyEntry) -> Optional[int]:
        pass

    def search_taxonomy(self, taxonomy_id: int, search_term: str, limit: int = 10) -> List[TaxonomyEntry]:
        pass

    def import_csv_taxonomy(self, taxonomy_id: int, csv_file: str, mapping: Dict[str, str]) -> int:
        pass


class TaxonomyService(ITaxonomyService):
    """Service for taxonomy operations"""

    def __init__(self, database_service: IDatabaseService):
        self.db = database_service

    def get_taxonomy(self, taxonomy_id: int) -> Optional[Taxonomy]:
        """
        Get a taxonomy by ID

        Args:
            taxonomy_id: ID of the taxonomy to get

        Returns:
            Taxonomy if found, None otherwise
        """
        query = """
        SELECT id, lifelist_id, name, version, source, description, is_active, created_at
        FROM taxonomies WHERE id = ?
        """
        results = self.db.execute_query(query, (taxonomy_id,))

        if not results:
            return None

        taxonomy = Taxonomy.from_dict(results[0])

        # Load taxonomy entries (optional, can be expensive for large taxonomies)
        entries_query = """
        SELECT id, taxonomy_id, scientific_name, common_name, family, genus, species,
        subspecies, order_name, class_name, code, rank, is_custom, additional_data
        FROM taxonomy_entries WHERE taxonomy_id = ? LIMIT 100
        """
        entry_results = self.db.execute_query(entries_query, (taxonomy_id,))
        taxonomy.entries = [TaxonomyEntry.from_dict(entry) for entry in entry_results]

        return taxonomy

    def get_taxonomies(self, lifelist_id: int) -> List[Taxonomy]:
        """
        Get all taxonomies for a lifelist

        Args:
            lifelist_id: ID of the lifelist

        Returns:
            List of Taxonomy objects
        """
        query = """
        SELECT id, lifelist_id, name, version, source, description, is_active, created_at
        FROM taxonomies WHERE lifelist_id = ?
        """
        results = self.db.execute_query(query, (lifelist_id,))

        taxonomies = []
        for result in results:
            taxonomy = Taxonomy.from_dict(result)

            # Count entries for each taxonomy
            count_query = "SELECT COUNT(*) as count FROM taxonomy_entries WHERE taxonomy_id = ?"
            count_result = self.db.execute_query(count_query, (taxonomy.id,))

            if count_result:
                taxonomy.entry_count = count_result[0].get('count', 0)

            taxonomies.append(taxonomy)

        return taxonomies

    def get_active_taxonomy(self, lifelist_id: int) -> Optional[Taxonomy]:
        """
        Get the active taxonomy for a lifelist

        Args:
            lifelist_id: ID of the lifelist

        Returns:
            Active Taxonomy if found, None otherwise
        """
        query = """
        SELECT id, lifelist_id, name, version, source, description, is_active, created_at
        FROM taxonomies WHERE lifelist_id = ? AND is_active = 1
        """
        results = self.db.execute_query(query, (lifelist_id,))

        if not results:
            return None

        return Taxonomy.from_dict(results[0])

    def add_taxonomy(self, taxonomy: Taxonomy) -> Optional[int]:
        """
        Add a new taxonomy

        Args:
            taxonomy: Taxonomy to add

        Returns:
            ID of the new taxonomy, or None if adding failed
        """
        try:
            query = """
            INSERT INTO taxonomies 
            (lifelist_id, name, version, source, description, is_active) 
            VALUES (?, ?, ?, ?, ?, ?)
            """
            params = (
                taxonomy.lifelist_id,
                taxonomy.name,
                taxonomy.version,
                taxonomy.source,
                taxonomy.description,
                1 if taxonomy.is_active else 0
            )

            taxonomy_id = self.db.execute_non_query(query, params)
            return taxonomy_id

        except Exception as e:
            print(f"Error adding taxonomy: {e}")
            return None

    def set_active_taxonomy(self, taxonomy_id: int, lifelist_id: int) -> bool:
        """
        Set a taxonomy as active for a lifelist

        Args:
            taxonomy_id: ID of the taxonomy to set as active
            lifelist_id: ID of the lifelist

        Returns:
            True if setting succeeded, False otherwise
        """
        try:
            def transaction_func():
                # First, set all taxonomies for this lifelist as inactive
                self.db.execute_non_query(
                    "UPDATE taxonomies SET is_active = 0 WHERE lifelist_id = ?",
                    (lifelist_id,)
                )

                # Then set the selected taxonomy as active
                self.db.execute_non_query(
                    "UPDATE taxonomies SET is_active = 1 WHERE id = ?",
                    (taxonomy_id,)
                )

                return True

            return self.db.execute_transaction(transaction_func)

        except Exception as e:
            print(f"Error setting active taxonomy: {e}")
            return False

    def delete_taxonomy(self, taxonomy_id: int) -> bool:
        """
        Delete a taxonomy

        Args:
            taxonomy_id: ID of the taxonomy to delete

        Returns:
            True if deletion succeeded, False otherwise
        """
        try:
            self.db.execute_non_query("DELETE FROM taxonomies WHERE id = ?", (taxonomy_id,))
            return True

        except Exception as e:
            print(f"Error deleting taxonomy: {e}")
            return False

    def add_taxonomy_entry(self, entry: TaxonomyEntry) -> Optional[int]:
        """
        Add an entry to a taxonomy

        Args:
            entry: TaxonomyEntry to add

        Returns:
            ID of the new entry, or None if adding failed
        """
        try:
            # Convert additional_data dict to JSON string if provided
            additional_data = None
            if entry.additional_data:
                additional_data = json.dumps(entry.additional_data)

            query = """
            INSERT INTO taxonomy_entries 
            (taxonomy_id, scientific_name, common_name, family, genus, species, 
            subspecies, order_name, class_name, code, rank, is_custom, additional_data) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                entry.taxonomy_id,
                entry.scientific_name,
                entry.common_name,
                entry.family,
                entry.genus,
                entry.species,
                entry.subspecies,
                entry.order_name,
                entry.class_name,
                entry.code,
                entry.rank,
                1 if entry.is_custom else 0,
                additional_data
            )

            entry_id = self.db.execute_non_query(query, params)
            return entry_id

        except Exception as e:
            print(f"Error adding taxonomy entry: {e}")
            return None

    def search_taxonomy(self, taxonomy_id: int, search_term: str, limit: int = 10) -> List[TaxonomyEntry]:
        """
        Search for entries in a taxonomy

        Args:
            taxonomy_id: ID of the taxonomy to search
            search_term: Term to search for
            limit: Maximum number of results

        Returns:
            List of TaxonomyEntry objects
        """
        search_param = f"%{search_term}%"

        query = """
        SELECT id, taxonomy_id, scientific_name, common_name, family, genus, species,
        subspecies, order_name, class_name, code, rank, is_custom, additional_data
        FROM taxonomy_entries 
        WHERE taxonomy_id = ? AND 
        (scientific_name LIKE ? OR common_name LIKE ?)
        ORDER BY 
            CASE WHEN scientific_name LIKE ? THEN 1
                 WHEN common_name LIKE ? THEN 2
                 ELSE 3
            END,
            scientific_name
        LIMIT ?
        """
        params = (taxonomy_id, search_param, search_param,
                  f"{search_term}%", f"{search_term}%", limit)

        results = self.db.execute_query(query, params)

        return [TaxonomyEntry.from_dict(result) for result in results]

    def import_csv_taxonomy(self, taxonomy_id: int, csv_file: str, mapping: Dict[str, str]) -> int:
        """
        Import taxonomy entries from a CSV file

        Args:
            taxonomy_id: ID of the taxonomy to import to
            csv_file: Path to the CSV file
            mapping: Mapping of database fields to CSV columns

        Returns:
            Number of entries imported, or -1 if import failed
        """
        try:
            import csv

            def transaction_func():
                # Track the number of entries added
                count = 0

                # Read the CSV file
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)

                    # Process each row
                    for row in reader:
                        # Map CSV fields to database fields
                        entry_data = {}

                        for db_field, csv_field in mapping.items():
                            if csv_field in row:
                                entry_data[db_field] = row[csv_field]

                        # Check if we have at least a scientific name
                        if 'scientific_name' in entry_data and entry_data['scientific_name']:
                            # Add any unmapped data to the additional_data field
                            additional_data = {}
                            for key, value in row.items():
                                if key not in mapping.values() and value:
                                    additional_data[key] = value

                            # Only add additional_data if we have any
                            if additional_data:
                                entry_data['additional_data'] = json.dumps(additional_data)

                            # Create a TaxonomyEntry object
                            entry = TaxonomyEntry(
                                taxonomy_id=taxonomy_id,
                                scientific_name=entry_data.get('scientific_name'),
                                common_name=entry_data.get('common_name'),
                                family=entry_data.get('family'),
                                genus=entry_data.get('genus'),
                                species=entry_data.get('species'),
                                subspecies=entry_data.get('subspecies'),
                                order_name=entry_data.get('order_name'),
                                class_name=entry_data.get('class_name'),
                                code=entry_data.get('code'),
                                rank=entry_data.get('rank'),
                                is_custom=False,
                                additional_data=additional_data if additional_data else None
                            )

                            # Add the entry to the database
                            self.add_taxonomy_entry(entry)
                            count += 1

                return count

            return self.db.execute_transaction(transaction_func)

        except Exception as e:
            print(f"Error importing taxonomy from CSV: {e}")
            return -1