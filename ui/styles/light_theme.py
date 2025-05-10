# ui/styles/light_theme.py
from PySide6.QtGui import QPalette, QColor

def apply_light_theme(app):
    """Apply a light color theme to the application"""
    # Set light palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
    palette.setColor(QPalette.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Link, QColor(0, 100, 200))
    palette.setColor(QPalette.Highlight, QColor(0, 120, 215))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))

    # Set disabled colors
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(150, 150, 150))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(150, 150, 150))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(150, 150, 150))
    palette.setColor(QPalette.Disabled, QPalette.Highlight, QColor(200, 200, 200))
    palette.setColor(QPalette.Disabled, QPalette.HighlightedText, QColor(150, 150, 150))

    app.setPalette(palette)

    # Set stylesheet for fine-tuning
    app.setStyleSheet("""
        QToolTip { 
            color: #000000; 
            background-color: #F5F5F5; 
            border: 1px solid #C0C0C0; 
            border-radius: 4px;
        }
        QTableView {
            gridline-color: #D3D3D3;
            background-color: #FFFFFF;
            alternate-background-color: #F5F5F5;
        }
        QTabWidget::pane { 
            border: 1px solid #C0C0C0;
        }
        QTabBar::tab {
            background: #E6E6E6; 
            border: 1px solid #C0C0C0;
            padding: 5px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected, QTabBar::tab:hover {
            background: #F0F0F0;
        }
        QTabBar::tab:selected {
            border-bottom: 2px solid #0078D7;
        }
        QPushButton {
            background-color: #E6E6E6;
            border: 1px solid #C0C0C0;
            border-radius: 4px;
            padding: 5px 10px;
        }
        QPushButton:hover {
            background-color: #D7D7D7;
        }
        QPushButton:pressed {
            background-color: #C7C7C7;
        }
        QHeaderView::section {
            background-color: #E6E6E6;
            border: 1px solid #C0C0C0;
            padding: 4px;
        }
        QScrollBar:vertical {
            border: none;
            background: #F0F0F0;
            width: 10px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: #CDCDCD;
            min-height: 20px;
            border-radius: 5px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
            height: 0px;
        }
    """)