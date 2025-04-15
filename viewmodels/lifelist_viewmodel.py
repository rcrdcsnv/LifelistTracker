# viewmodels/lifelist_viewmodel.py
"""
Lifelist ViewModel - Provides data and commands for the Lifelist View
"""
from typing import List, Optional, Dict, Any, Callable
from LifelistTracker.models.lifelist import Lifelist
from LifelistTracker.services.lifelist_service import ILifelistService
from LifelistTracker.services.observation_service import IObservationService
from LifelistTracker.services.photo_service import IPhotoService


class LifelistViewModel:
    """ViewModel for the Lifelist View"""

    def __init__(self, lifelist_service: ILifelistService,
                 observation_service: IObservationService,
                 photo_service: IPhotoService):
        self.lifelist_service = lifelist_service
        self.observation_service = observation_service
        self.photo_service = photo_service
        self.current_lifelist_id: Optional[int] = None
        self.current_lifelist: Optional[Lifelist] = None
        self.search_term: str = ""
        self.selected_tier: str = "All"
        self.selected_tag_ids: List[int] = []
        self.observations: List[Dict[str, Any]] = []
        self.on_state_changed: List[Callable] = []

    def load_lifelist(self, lifelist_id: int) -> bool:
        """
        Load a lifelist and its observations

        Args:
            lifelist_id: ID of the lifelist to load

        Returns:
            True if loading succeeded, False otherwise
        """
        lifelist = self.lifelist_service.get_lifelist(lifelist_id)
        if not lifelist:
            return False

        self.current_lifelist_id = lifelist_id
        self.current_lifelist = lifelist

        # Load observations with current filters
        self.load_observations()

        # Notify state change
        self._notify_state_changed()

        return True

    def load_observations(self) -> None:
        """Load observations based on current filters"""
        if not self.current_lifelist_id:
            self.observations = []
            return

        tier = None if self.selected_tier == "All" else self.selected_tier
        tag_ids = self.selected_tag_ids if self.selected_tag_ids else None
        search = self.search_term if self.search_term else None

        self.observations = self.observation_service.get_filtered_observations(
            self.current_lifelist_id, tier, tag_ids, search
        )

        # Group observations by species
        self._group_observations_by_species()

        # Load primary photos for each species
        self._load_species_photos()

        # Notify state change
        self._notify_state_changed()

    def _group_observations_by_species(self) -> None:
        """Group observations by species"""
        if not self.observations:
            return

        species_groups = {}
        for obs in self.observations:
            species_name = obs['species_name']

            # If we haven't seen this species yet, create a new entry
            if species_name not in species_groups:
                species_groups[species_name] = {
                    "latest_id": obs['id'],
                    "date": obs['observation_date'],
                    "location": obs['location'],
                    "tier": obs['tier'],
                    "observation_ids": [obs['id']]
                }
            else:
                # Add this observation ID to the list
                species_groups[species_name]["observation_ids"].append(obs['id'])

                # Update date if this observation is more recent
                if not species_groups[species_name]["date"] or (obs['observation_date'] and (
                        not species_groups[species_name]["date"] or
                        obs['observation_date'] > species_groups[species_name]["date"])):
                    species_groups[species_name]["date"] = obs['observation_date']
                    species_groups[species_name]["location"] = obs['location']
                    species_groups[species_name]["latest_id"] = obs['id']

                # Update tier if this tier is "higher" in precedence
                # Tier precedence: wild > heard > captive
                tier_precedence = {"wild": 3, "heard": 2, "captive": 1}
                current_tier_value = tier_precedence.get(species_groups[species_name]["tier"], 0)
                new_tier_value = tier_precedence.get(obs['tier'], 0)

                if new_tier_value > current_tier_value:
                    species_groups[species_name]["tier"] = obs['tier']

        # Replace the observations with the grouped observations
        self.observations = []
        for species_name, data in species_groups.items():
            entry = {
                "species_name": species_name,
                "id": data["latest_id"],
                "observation_date": data["date"],
                "location": data["location"],
                "tier": data["tier"],
                "observation_ids": data["observation_ids"],
                "observation_count": len(data["observation_ids"])
            }
            self.observations.append(entry)

    def _load_species_photos(self) -> None:
        """Load primary photos for each species"""
        if not self.observations:
            return

        for obs in self.observations:
            species_name = obs["species_name"]
            photo_data = self.photo_service.get_species_primary_photo(
                self.current_lifelist_id, species_name)

            if photo_data:
                obs["photo_data"] = photo_data

    def set_search_term(self, search_term: str) -> None:
        """
        Set the search term filter

        Args:
            search_term: Term to search for
        """
        self.search_term = search_term

    def set_selected_tier(self, tier: str) -> None:
        """
        Set the selected tier filter

        Args:
            tier: Tier to filter by, or "All"
        """
        self.selected_tier = tier

    def set_selected_tag_ids(self, tag_ids: List[int]) -> None:
        """
        Set the selected tag IDs filter

        Args:
            tag_ids: List of tag IDs to filter by
        """
        self.selected_tag_ids = tag_ids

    def clear_filters(self) -> None:
        """Clear all filters"""
        self.search_term = ""
        self.selected_tier = "All"
        self.selected_tag_ids = []

    def register_state_change_callback(self, callback: Callable) -> None:
        """
        Register a callback for state changes

        Args:
            callback: Function to call on state change
        """
        if callback not in self.on_state_changed:
            self.on_state_changed.append(callback)

    def unregister_state_change_callback(self, callback: Callable) -> None:
        """
        Unregister a previously registered callback

        Args:
            callback: Function to remove from callback list
        """
        if callback in self.on_state_changed:
            self.on_state_changed.remove(callback)

    def _notify_state_changed(self) -> None:
        """Notify all registered callbacks of a state change"""
        for callback in self.on_state_changed:
            callback()