# ui/dialogs/text_input_dialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit,
                               QDialogButtonBox)


class TextInputDialog(QDialog):
    """Simple dialog for text input"""

    def __init__(self, parent=None, title="Input", prompt="Enter value:", initial_value=""):
        super().__init__(parent)

        self.setWindowTitle(title)
        self._setup_ui(prompt, initial_value)

    def _setup_ui(self, prompt, initial_value):
        layout = QVBoxLayout(self)

        # Add prompt label
        self.prompt_label = QLabel(prompt)
        layout.addWidget(self.prompt_label)

        # Add text input
        self.text_edit = QLineEdit()
        self.text_edit.setText(initial_value)
        self.text_edit.selectAll()
        layout.addWidget(self.text_edit)

        # Add button box
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Set minimum width
        self.setMinimumWidth(300)

    def get_text(self):
        """Get the entered text"""
        return self.text_edit.text()