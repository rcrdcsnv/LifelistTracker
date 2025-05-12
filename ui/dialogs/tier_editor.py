# ui/dialogs/tier_editor.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QListWidget, QAbstractItemView,
                               QDialogButtonBox, QMessageBox)

from ui.dialogs.text_input_dialog import TextInputDialog


class TierEditorDialog(QDialog):
    """Dialog for editing lifelist tiers"""

    def __init__(self, parent, db_manager, lifelist_id, observation_term="observation"):
        super().__init__(parent)

        self.db_manager = db_manager
        self.lifelist_id = lifelist_id
        self.observation_term = observation_term

        self.tiers = []
        self.original_tiers = []

        self.setWindowTitle("Edit Tiers")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)

        self._setup_ui()
        self._load_tiers()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Explanation label
        explanation = QLabel(
            f"Tiers represent different categories or statuses for your {self.observation_term}s. "
            "Drag items to reorder them."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        # Tiers list
        self.tiers_list = QListWidget()
        self.tiers_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.tiers_list.model().rowsMoved.connect(self._tiers_reordered)
        layout.addWidget(self.tiers_list)

        # Buttons layout
        buttons_layout = QHBoxLayout()

        self.add_btn = QPushButton("Add Tier")
        self.add_btn.clicked.connect(self._add_tier)
        buttons_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Edit Tier")
        self.edit_btn.clicked.connect(self._edit_tier)
        buttons_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Delete Tier")
        self.delete_btn.clicked.connect(self._delete_tier)
        buttons_layout.addWidget(self.delete_btn)

        self.reset_btn = QPushButton("Reset to Default")
        self.reset_btn.clicked.connect(self._reset_to_default)
        buttons_layout.addWidget(self.reset_btn)

        layout.addLayout(buttons_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._save_tiers)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_tiers(self):
        """Load tiers from database"""
        with self.db_manager.session_scope() as session:
            from db.repositories import LifelistRepository

            # Get current tiers
            self.tiers = LifelistRepository.get_lifelist_tiers(session, self.lifelist_id)

            # Store original tiers for comparison
            self.original_tiers = self.tiers.copy()

            # Populate list
            self.tiers_list.clear()
            for tier in self.tiers:
                self.tiers_list.addItem(tier)

    def _tiers_reordered(self):
        """Update tiers list after drag-and-drop reordering"""
        # Update tiers from list items
        self.tiers = []
        self.tiers.extend(
            self.tiers_list.item(i).text() for i in range(self.tiers_list.count())
        )

    def _add_tier(self):
        """Add a new tier"""
        dialog = TextInputDialog(self, "Add Tier", "Enter tier name:")

        if dialog.exec():
            tier_name = dialog.get_text().strip()

            if not tier_name:
                return

            # Check for duplicates
            if tier_name in self.tiers:
                QMessageBox.warning(self, "Duplicate Tier", "This tier already exists.")
                return

            # Add tier
            self.tiers.append(tier_name)
            self.tiers_list.addItem(tier_name)

    def _edit_tier(self):
        """Edit selected tier"""
        current_item = self.tiers_list.currentItem()
        if not current_item:
            return

        current_tier = current_item.text()
        current_index = self.tiers_list.currentRow()

        dialog = TextInputDialog(self, "Edit Tier", "Enter tier name:", current_tier)

        if dialog.exec():
            tier_name = dialog.get_text().strip()

            if not tier_name:
                return

            # Check for duplicates
            if tier_name in self.tiers and tier_name != current_tier:
                QMessageBox.warning(self, "Duplicate Tier", "This tier already exists.")
                return

            # Update tier
            self.tiers[current_index] = tier_name
            current_item.setText(tier_name)

    def _delete_tier(self):
        """Delete selected tier"""
        current_item = self.tiers_list.currentItem()
        if not current_item:
            return

        current_tier = current_item.text()
        current_index = self.tiers_list.currentRow()

        # Confirm deletion
        message_box = QMessageBox(self)
        message_box.setWindowTitle("Confirm Deletion")
        message_box.setIcon(QMessageBox.Warning)
        message_box.setText(f"Are you sure you want to delete the tier '{current_tier}'?")
        message_box.setInformativeText(
            f"Any {self.observation_term}s using this tier will be marked as 'Undetermined'."
        )
        message_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        message_box.setDefaultButton(QMessageBox.No)

        if message_box.exec() == QMessageBox.Yes:
            # Remove tier
            self.tiers.pop(current_index)
            self.tiers_list.takeItem(current_index)

    def _reset_to_default(self):
        """Reset tiers to default for this lifelist type"""
        # Confirm reset
        message_box = QMessageBox(self)
        message_box.setWindowTitle("Confirm Reset")
        message_box.setIcon(QMessageBox.Warning)
        message_box.setText("Are you sure you want to reset tiers to default?")
        message_box.setInformativeText(
            f"Any custom tiers will be lost, and {self.observation_term}s may need to be reassigned."
        )
        message_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        message_box.setDefaultButton(QMessageBox.No)

        if message_box.exec() == QMessageBox.Yes:
            with self.db_manager.session_scope() as session:
                from db.repositories import LifelistRepository
                from db.models import Lifelist

                # Get lifelist to determine type
                lifelist = session.query(Lifelist).filter_by(id=self.lifelist_id).first()

                if lifelist and lifelist.lifelist_type_id:
                    # Get default tiers for this type
                    default_tiers = LifelistRepository.get_default_tiers_for_type(
                        session, lifelist.lifelist_type_id
                    )

                    # Update tiers
                    self.tiers = default_tiers

                    # Update list
                    self.tiers_list.clear()
                    for tier in self.tiers:
                        self.tiers_list.addItem(tier)

    def _save_tiers(self):
        """Save tiers to database"""
        if not self.tiers:
            QMessageBox.warning(
                self,
                "No Tiers",
                f"You must have at least one tier for your {self.observation_term}s."
            )
            return

        # Check if tiers have changed
        if self.tiers == self.original_tiers:
            self.accept()
            return

        try:
            with self.db_manager.session_scope() as session:
                from db.repositories import LifelistRepository

                # Save tiers
                LifelistRepository.set_lifelist_tiers(session, self.lifelist_id, self.tiers)

                # Check for orphaned observations
                self._check_orphaned_observations(session)

                session.commit()

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save tiers: {str(e)}")

    def _check_orphaned_observations(self, session):
        """Check if any observations use tiers that have been removed"""
        # Get all observations for this lifelist
        from db.models import Observation
        observations = session.query(Observation).filter_by(lifelist_id=self.lifelist_id).all()

        # Check for observations with tiers not in the new tiers list
        orphaned_count = 0
        undetermined_tier = "Undetermined"  # Special tier for orphaned observations

        for observation in observations:
            if observation.tier and observation.tier not in self.tiers:
                orphaned_count += 1

                # Assign to "Undetermined" tier
                observation.tier = undetermined_tier

        # Show message if orphaned observations were found
        if orphaned_count > 0:
            tier_text = "tier" if orphaned_count == 1 else "tiers"
            obs_text = "observation" if orphaned_count == 1 else "observations"

            message = (
                f"{orphaned_count} {obs_text} used {tier_text} that have been removed. "
                f"These have been marked as '{undetermined_tier}'."
            )

            QMessageBox.information(self, "Orphaned Observations", message)