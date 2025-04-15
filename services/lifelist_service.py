# services/lifelist_service.py
"""
Lifelist Service - Handles operations related to lifelists
"""
from typing import List, Optional
from LifelistTracker.models.lifelist import Lifelist
from LifelistTracker.services.database_service import IDatabaseService


class ILifelistService:
    """Interface for lifelist service"""

    def get_lifelist(self, lifelist_id: int) -> Optional[Lifelist]:
        pass

    def get_all_lifelists(self) -> List[Lifelist]:
        pass

    def create_lifelist(self, name: str, taxonomy: Optional[str] = None) -> Optional[Lifelist]:
        pass

    def delete_lifelist(self, lifelist_id: int) -> bool:
        pass

    def get_lifelist_tiers(self, lifelist_id: int) -> List[str]:
        pass

    def set_lifelist_tiers(self, lifelist_id: int, tiers: List[str]) -> bool:
        pass

    def get_all_tiers(self, lifelist_id: int) -> List[str]:
        pass


class LifelistService(ILifelistService):
    """Service for lifelist operations"""

    def __init__(self, database_service: IDatabaseService):
        self.db = database_service

    def get_lifelist(self, lifelist_id: int) -> Optional[Lifelist]:
        """
        Get a lifelist by ID

        Args:
            lifelist_id: ID of the lifelist to get

        Returns:
            Lifelist if found, None otherwise
        """
        query = "SELECT id, name, taxonomy, created_at FROM lifelists WHERE id = ?"
        result = self.db.execute_query(query, (lifelist_id,))

        if not result:
            return None

        lifelist = Lifelist.from_dict(result[0])

        # Load tiers
        lifelist.tiers = self.get_lifelist_tiers(lifelist_id)

        # Load custom fields
        custom_fields_query = "SELECT id, field_name, field_type FROM custom_fields WHERE lifelist_id = ?"
        custom_fields = self.db.execute_query(custom_fields_query, (lifelist_id,))
        lifelist.custom_fields = custom_fields

        return lifelist

    def get_all_lifelists(self) -> List[Lifelist]:
        """
        Get all lifelists

        Returns:
            List of Lifelist objects
        """
        query = "SELECT id, name, taxonomy, created_at FROM lifelists ORDER BY name"
        results = self.db.execute_query(query)

        lifelists = []
        for result in results:
            lifelist = Lifelist.from_dict(result)
            lifelists.append(lifelist)

        return lifelists

    def create_lifelist(self, name: str, taxonomy: Optional[str] = None) -> Optional[Lifelist]:
        """
        Create a new lifelist

        Args:
            name: Name of the lifelist
            taxonomy: Optional taxonomy reference

        Returns:
            The created Lifelist, or None if creation failed
        """
        query = "INSERT INTO lifelists (name, taxonomy) VALUES (?, ?)"
        lifelist_id = self.db.execute_non_query(query, (name, taxonomy))

        if lifelist_id <= 0:
            return None

        return self.get_lifelist(lifelist_id)

    def delete_lifelist(self, lifelist_id: int) -> bool:
        """
        Delete a lifelist

        Args:
            lifelist_id: ID of the lifelist to delete

        Returns:
            True if deletion succeeded, False otherwise
        """
        # Check if lifelist exists
        exists_query = "SELECT id FROM lifelists WHERE id = ?"
        result = self.db.execute_query(exists_query, (lifelist_id,))

        if not result:
            return False

        # Delete the lifelist (cascades to other tables)
        query = "DELETE FROM lifelists WHERE id = ?"
        self.db.execute_non_query(query, (lifelist_id,))

        return True

    def get_lifelist_tiers(self, lifelist_id: int) -> List[str]:
        """
        Get tiers for a lifelist

        Args:
            lifelist_id: ID of the lifelist

        Returns:
            List of tier names
        """
        query = "SELECT tier_name FROM lifelist_tiers WHERE lifelist_id = ? ORDER BY tier_order"
        results = self.db.execute_query(query, (lifelist_id,))

        tiers = [row['tier_name'] for row in results]

        # Return default tiers if none defined
        if not tiers:
            return ["wild", "heard", "captive"]

        return tiers

    def set_lifelist_tiers(self, lifelist_id: int, tiers: List[str]) -> bool:
        """
        Set tiers for a lifelist

        Args:
            lifelist_id: ID of the lifelist
            tiers: List of tier names

        Returns:
            True if the operation succeeded, False otherwise
        """
        try:
            def transaction_func():
                # Delete existing tiers
                self.db.execute_non_query("DELETE FROM lifelist_tiers WHERE lifelist_id = ?", (lifelist_id,))

                # Insert new tiers
                for i, tier_name in enumerate(tiers):
                    self.db.execute_non_query(
                        "INSERT INTO lifelist_tiers (lifelist_id, tier_name, tier_order) VALUES (?, ?, ?)",
                        (lifelist_id, tier_name, i)
                    )

                return True

            return self.db.execute_transaction(transaction_func)
        except Exception as e:
            print(f"Error setting lifelist tiers: {e}")
            return False

    def get_all_tiers(self, lifelist_id: int) -> List[str]:
        """
        Get all tiers used in observations for a lifelist along with custom tiers

        Args:
            lifelist_id: ID of the lifelist

        Returns:
            List of all tiers
        """
        # Get custom tiers defined for this lifelist
        custom_tiers = self.get_lifelist_tiers(lifelist_id)

        # Get tiers actually used in observations (could include legacy tiers)
        query = "SELECT DISTINCT tier FROM observations WHERE lifelist_id = ?"
        results = self.db.execute_query(query, (lifelist_id,))
        used_tiers = [row["tier"] for row in results if row["tier"]]

        # Combine and deduplicate
        all_tiers = []
        for tier in custom_tiers:
            if tier not in all_tiers:
                all_tiers.append(tier)

        for tier in used_tiers:
            if tier not in all_tiers:
                all_tiers.append(tier)

        return all_tiers