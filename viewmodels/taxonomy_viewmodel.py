# viewmodels/taxonomy_viewmodel.py
"""
Taxonomy ViewModel - Provides data and commands for the Taxonomy Manager
"""
from typing import List, Optional, Dict, Any, Callable
import tempfile
import requests
from LifelistTracker.models.taxonomy import Taxonomy, TaxonomyEntry
from LifelistTracker.services.taxonomy_service import ITaxonomyService
from LifelistTracker.services.file_service import IFileService


class TaxonomyViewModel:
    """ViewModel for the Taxonomy Manager"""

    def __init__(self, taxonomy_service: ITaxonomyService, file_service: IFileService):
        self.taxonomy_service = taxonomy_service
        self.file_service = file_service

        self.current_lifelist_id = None
        self.taxonomies: List[Taxonomy] = []
        self.selected_taxonomy: Optional[Taxonomy] = None
        self.csv_headers: List[str] = []
        self.field_mappings: Dict[str, str] = {}
        self.download_progress = 0
        self.download_status = ""

        # Standard taxonomy definitions
        self.standard_taxonomies = [
            {
                "name": "eBird Taxonomy v2023",
                "description": "The eBird/Clements taxonomy, updated 2023",
                "url": "https://www.birds.cornell.edu/clementschecklist/download/",
                "type": "birds"
            },
            {
                "name": "IOC World Bird List v13.1",
                "description": "International Ornithological Congress bird list",
                "url": "https://www.worldbirdnames.org/new/ioc-lists/master-list-2/",
                "type": "birds"
            },
            {
                "name": "Mammal Species of the World",
                "description": "Comprehensive mammal taxonomy",
                "url": "https://www.departments.bucknell.edu/biology/resources/msw3/",
                "type": "mammals"
            },
            {
                "name": "The Plant List",
                "description": "Working list of all known plant species",
                "url": "http://www.theplantlist.org/",
                "type": "plants"
            },
            {
                "name": "Catalog of Life",
                "description": "Global index of all known species",
                "url": "https://www.catalogueoflife.org/data/download",
                "type": "comprehensive"
            },
        ]

        # Endpoints for standard taxonomies
        self.taxonomy_endpoints = {
            "eBird Taxonomy v2023": {
                "url": "https://media.ebird.org/catalog/resource/eBird_Taxonomy_v2023.csv",
                "mapping": {
                    "scientific_name": "SCI_NAME",
                    "common_name": "PRIMARY_COM_NAME",
                    "family": "FAMILY",
                    "order_name": "ORDER1",
                    "species": "SPECIES_CODE"
                }
            },
            "IOC World Bird List v13.1": {
                "url": "https://www.worldbirdnames.org/IOC_names_export_13.1.csv",
                "mapping": {
                    "scientific_name": "Scientific name",
                    "common_name": "English name",
                    "family": "Family",
                    "order_name": "Order"
                }
            },
            "Mammal Species of the World": {
                "url": "https://www.mammaldiversity.org/assets/data/MDD_v1.11_6818species.csv",
                "mapping": {
                    "scientific_name": "sciName",
                    "common_name": "vernacularName",
                    "family": "familyNameValid",
                    "order_name": "orderNameValid",
                    "genus": "genusNameValid",
                    "species": "speciesNameValid"
                }
            },
            "The Plant List": {
                "url": "https://raw.githubusercontent.com/crazybilly/tpldata/master/data/namesAccepted.csv",
                "mapping": {
                    "scientific_name": "ScientificName",
                    "family": "Family",
                    "genus": "Genus",
                    "species": "Species"
                }
            },
            "Catalog of Life": {
                "url": "https://api.checklistbank.org/dataset/9820/export.csv?format=SimpleDwC",
                "mapping": {
                    "scientific_name": "scientificName",
                    "common_name": "vernacularName",
                    "family": "family",
                    "order_name": "order",
                    "genus": "genus",
                    "species": "specificEpithet",
                    "rank": "taxonRank"
                }
            }
        }

        self.on_state_changed: List[Callable] = []

    def load_taxonomies(self, lifelist_id: int) -> None:
        """
        Load taxonomies for a lifelist

        Args:
            lifelist_id: ID of the lifelist
        """
        self.current_lifelist_id = lifelist_id
        self.taxonomies = self.taxonomy_service.get_taxonomies(lifelist_id)
        self._notify_state_changed()

    def activate_taxonomy(self, taxonomy_id: int) -> bool:
        """
        Set a taxonomy as active

        Args:
            taxonomy_id: ID of the taxonomy to activate

        Returns:
            True if activation succeeded, False otherwise
        """
        if not self.current_lifelist_id:
            return False

        success = self.taxonomy_service.set_active_taxonomy(taxonomy_id, self.current_lifelist_id)

        if success:
            # Reload taxonomies to update active status
            self.load_taxonomies(self.current_lifelist_id)

        return success

    def delete_taxonomy(self, taxonomy_id: int) -> bool:
        """
        Delete a taxonomy

        Args:
            taxonomy_id: ID of the taxonomy to delete

        Returns:
            True if deletion succeeded, False otherwise
        """
        success = self.taxonomy_service.delete_taxonomy(taxonomy_id)

        if success and self.current_lifelist_id:
            # Reload taxonomies
            self.load_taxonomies(self.current_lifelist_id)

        return success

    def preview_csv_headers(self, file_path: str) -> bool:
        """
        Preview headers from a CSV file

        Args:
            file_path: Path to the CSV file

        Returns:
            True if preview succeeded, False otherwise
        """
        # Reset existing mappings
        self.field_mappings = {}

        # Try to read headers
        _, headers = self.file_service.read_csv_rows(file_path)

        if not headers:
            return False

        self.csv_headers = headers

        # Try to guess mappings based on common field names
        db_fields = [
            "scientific_name",
            "common_name",
            "family",
            "genus",
            "species",
            "order_name",
            "class_name",
            "code",
            "rank"
        ]

        for db_field in db_fields:
            for header in headers:
                header_lower = header.lower()
                if db_field == "scientific_name" and any(x in header_lower for x in ["scientific", "latin"]):
                    self.field_mappings[db_field] = header
                elif db_field == "common_name" and any(x in header_lower for x in ["common", "english"]):
                    self.field_mappings[db_field] = header
                elif db_field.lower() in header_lower:
                    self.field_mappings[db_field] = header

        self._notify_state_changed()
        return True

    def update_field_mapping(self, db_field: str, csv_field: str) -> None:
        """
        Update a field mapping

        Args:
            db_field: Database field
            csv_field: CSV field
        """
        if csv_field:
            self.field_mappings[db_field] = csv_field
        elif db_field in self.field_mappings:
            del self.field_mappings[db_field]

        self._notify_state_changed()

    def import_taxonomy(self, name: str, version: str, source: str, file_path: str) -> Optional[int]:
        """
        Import a taxonomy from a CSV file

        Args:
            name: Name of the taxonomy
            version: Version of the taxonomy
            source: Source of the taxonomy
            file_path: Path to the CSV file

        Returns:
            ID of the new taxonomy, or None if import failed
        """
        if not self.current_lifelist_id:
            return None

        # Create the taxonomy
        taxonomy = Taxonomy(
            lifelist_id=self.current_lifelist_id,
            name=name,
            version=version or None,
            source=source or None
        )

        taxonomy_id = self.taxonomy_service.add_taxonomy(taxonomy)

        if not taxonomy_id:
            return None

        # Import the data
        count = self.taxonomy_service.import_csv_taxonomy(taxonomy_id, file_path, self.field_mappings)

        if count < 0:
            # Import failed
            self.taxonomy_service.delete_taxonomy(taxonomy_id)
            return None

        # Set this as the active taxonomy if it's the first one
        if not self.taxonomy_service.get_active_taxonomy(self.current_lifelist_id):
            self.taxonomy_service.set_active_taxonomy(taxonomy_id, self.current_lifelist_id)

        # Reload taxonomies
        self.load_taxonomies(self.current_lifelist_id)

        return taxonomy_id

    def download_standard_taxonomy(self, taxonomy_info: Dict[str, Any],
                                   progress_callback: Callable[[float, str], None]) -> bool:
        """
        Download and import a standard taxonomy

        Args:
            taxonomy_info: Information about the taxonomy to download
            progress_callback: Callback function for progress updates

        Returns:
            True if download and import succeeded, False otherwise
        """
        if not self.current_lifelist_id:
            return False

        # Configure the download based on the selected taxonomy
        endpoint_info = self.taxonomy_endpoints.get(taxonomy_info["name"])

        if not endpoint_info:
            progress_callback(0, "Error: Taxonomy information not found")
            return False

        try:
            # Update status
            progress_callback(0, f"Downloading {taxonomy_info['name']}...")

            # Create a temporary file to store the download
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
            temp_file_path = temp_file.name
            temp_file.close()

            # Download the file with progress tracking
            response = requests.get(endpoint_info["url"], stream=True)
            response.raise_for_status()

            # Get total file size
            total_size = int(response.headers.get('content-length', 0))

            # Download with progress updates
            downloaded = 0
            with open(temp_file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Update progress
                        if total_size:
                            progress = downloaded / total_size
                            progress_callback(progress,
                                              f"Downloaded {downloaded / 1024 / 1024:.1f} MB of {total_size / 1024 / 1024:.1f} MB")

            # Update status
            progress_callback(0, "Processing data...")

            # Create the taxonomy
            taxonomy = Taxonomy(
                lifelist_id=self.current_lifelist_id,
                name=taxonomy_info["name"],
                version=taxonomy_info.get("version", ""),
                source=taxonomy_info.get("url", ""),
                description=taxonomy_info.get("description", "")
            )

            taxonomy_id = self.taxonomy_service.add_taxonomy(taxonomy)

            if not taxonomy_id:
                progress_callback(0, "Error: Failed to create taxonomy")
                return False

            # Import the CSV
            count = self.taxonomy_service.import_csv_taxonomy(taxonomy_id, temp_file_path, endpoint_info["mapping"])

            # Clean up the temporary file
            self.file_service.delete_file(temp_file_path)

            if count >= 0:
                # Set as active taxonomy if it's the first one
                if not self.taxonomy_service.get_active_taxonomy(self.current_lifelist_id):
                    self.taxonomy_service.set_active_taxonomy(taxonomy_id, self.current_lifelist_id)

                # Update status
                progress_callback(1, f"Successfully imported {count} taxonomy entries")

                # Reload taxonomies
                self.load_taxonomies(self.current_lifelist_id)

                return True
            else:
                progress_callback(0, "Error: Failed to import taxonomy data")
                return False

        except Exception as e:
            progress_callback(0, f"Error: {str(e)}")
            return False

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