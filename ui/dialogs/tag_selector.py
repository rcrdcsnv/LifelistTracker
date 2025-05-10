# ui/dialogs/tag_selector.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QTreeWidget, QTreeWidgetItem, QDialogButtonBox,
                               QPushButton, QLineEdit)
from PySide6.QtCore import Qt


class TagSelectorDialog(QDialog):
    """Dialog for selecting tags for filtering"""

    def __init__(self, parent, db_manager, selected_tag_ids=None):
        super().__init__(parent)

        self.db_manager = db_manager
        self.selected_tag_ids = selected_tag_ids or []
        self.tag_items = {}  # Maps tag_id to QTreeWidgetItem

        self.setWindowTitle("Select Tags")
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)

        self._setup_ui()
        self._load_tags()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Search field
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search tags...")
        self.search_edit.textChanged.connect(self._filter_tags)
        search_layout.addWidget(self.search_edit)

        layout.addLayout(search_layout)

        # Tag tree
        self.tag_tree = QTreeWidget()
        self.tag_tree.setHeaderLabels(["Tag"])
        self.tag_tree.setSelectionMode(QTreeWidget.NoSelection)
        layout.addWidget(self.tag_tree)

        # Selection controls
        buttons_layout = QHBoxLayout()

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self._select_all)
        buttons_layout.addWidget(self.select_all_btn)

        self.clear_all_btn = QPushButton("Clear All")
        self.clear_all_btn.clicked.connect(self._clear_all)
        buttons_layout.addWidget(self.clear_all_btn)

        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_tags(self):
        """Load tags from database and populate tree"""
        self.tag_tree.clear()
        self.tag_items = {}

        # Get all tags
        with self.db_manager.session_scope() as session:
            from db.repositories import TagRepository
            tags_by_category = TagRepository.get_tags_by_category(session)

            # Add uncategorized tags first
            if None in tags_by_category:
                uncategorized = QTreeWidgetItem(self.tag_tree, ["Uncategorized"])
                uncategorized.setExpanded(True)

                for tag in tags_by_category[None]:
                    tag_item = QTreeWidgetItem(uncategorized, [tag.name])
                    tag_item.setData(0, Qt.UserRole, tag.id)
                    tag_item.setCheckState(0, Qt.Checked if tag.id in self.selected_tag_ids else Qt.Unchecked)

                    self.tag_items[tag.id] = tag_item

            # Add categorized tags
            for category, tags in tags_by_category.items():
                if category is None:
                    continue

                category_item = QTreeWidgetItem(self.tag_tree, [category])
                category_item.setExpanded(True)

                for tag in tags:
                    tag_item = QTreeWidgetItem(category_item, [tag.name])
                    tag_item.setData(0, Qt.UserRole, tag.id)
                    tag_item.setCheckState(0, Qt.Checked if tag.id in self.selected_tag_ids else Qt.Unchecked)

                    self.tag_items[tag.id] = tag_item

    def _filter_tags(self, text):
        """Filter tags based on search text"""
        search_text = text.strip().lower()

        if not search_text:
            # Show all items
            for i in range(self.tag_tree.topLevelItemCount()):
                category_item = self.tag_tree.topLevelItem(i)
                category_item.setHidden(False)

                for j in range(category_item.childCount()):
                    category_item.child(j).setHidden(False)

            return

        # Hide non-matching items
        for i in range(self.tag_tree.topLevelItemCount()):
            category_item = self.tag_tree.topLevelItem(i)
            category_name = category_item.text(0).lower()
            category_visible = False

            # Check if category matches
            if search_text in category_name:
                category_visible = True

                # Show all children
                for j in range(category_item.childCount()):
                    category_item.child(j).setHidden(False)
            else:
                # Check each tag in the category
                for j in range(category_item.childCount()):
                    tag_item = category_item.child(j)
                    tag_name = tag_item.text(0).lower()

                    if search_text in tag_name:
                        tag_item.setHidden(False)
                        category_visible = True
                    else:
                        tag_item.setHidden(True)

            category_item.setHidden(not category_visible)

    def _select_all(self):
        """Select all visible tags"""
        for i in range(self.tag_tree.topLevelItemCount()):
            category_item = self.tag_tree.topLevelItem(i)

            if not category_item.isHidden():
                for j in range(category_item.childCount()):
                    tag_item = category_item.child(j)

                    if not tag_item.isHidden():
                        tag_item.setCheckState(0, Qt.Checked)

    def _clear_all(self):
        """Clear all selected tags"""
        for i in range(self.tag_tree.topLevelItemCount()):
            category_item = self.tag_tree.topLevelItem(i)

            for j in range(category_item.childCount()):
                tag_item = category_item.child(j)
                tag_item.setCheckState(0, Qt.Unchecked)

    def get_selected_tags(self):
        """Get list of selected tag IDs"""
        selected_tags = []

        selected_tags.extend(
            tag_id
            for tag_id, tag_item in self.tag_items.items()
            if tag_item.checkState(0) == Qt.Checked
        )
        return selected_tags