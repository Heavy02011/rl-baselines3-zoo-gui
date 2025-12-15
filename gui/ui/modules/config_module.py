"""Configuration editor module."""
import json
from typing import Any, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.ui.modules.base_module import BaseModule


class ConfigModule(BaseModule):
    """Module for editing configuration."""

    MODULE_NAME = "Configuration"
    MODULE_ICON = "⚙️"

    def _setup_ui(self) -> None:
        """Set up the configuration editor UI."""
        # Description
        desc = QLabel(
            "Edit configuration settings. Changes are saved to config.yaml."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888888; margin-bottom: 10px;")
        self.add_widget(desc)

        # Config tree
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Setting", "Value"])
        self._tree.setAlternatingRowColors(True)
        self._tree.itemDoubleClicked.connect(self._edit_item)
        header = self._tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.add_widget(self._tree)

        # Edit area
        edit_widget = QWidget()
        edit_layout = QFormLayout(edit_widget)
        edit_layout.setContentsMargins(0, 10, 0, 0)

        self._key_label = QLabel("-")
        self._key_label.setStyleSheet("font-family: monospace;")
        edit_layout.addRow("Selected Key:", self._key_label)

        self._value_input = QLineEdit()
        self._value_input.setPlaceholderText("Select an item to edit...")
        edit_layout.addRow("Value:", self._value_input)

        self.add_widget(edit_widget)

        # Apply button for current edit
        apply_btn = QPushButton("✓ Apply Change")
        apply_btn.clicked.connect(self._apply_change)
        self.add_widget(apply_btn)

        # Action buttons
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 10, 0, 0)

        save_btn = QPushButton("💾 Save Config")
        save_btn.clicked.connect(self._save_config)
        save_btn.setStyleSheet(
            "background-color: #107c10; color: white; font-weight: bold;"
        )
        btn_layout.addWidget(save_btn)

        reload_btn = QPushButton("🔄 Reload")
        reload_btn.clicked.connect(self._reload_config)
        btn_layout.addWidget(reload_btn)

        self.add_widget(btn_widget)

        # Import/Export buttons
        ie_widget = QWidget()
        ie_layout = QHBoxLayout(ie_widget)
        ie_layout.setContentsMargins(0, 0, 0, 0)

        import_btn = QPushButton("📥 Import Config...")
        import_btn.clicked.connect(self._import_config)
        ie_layout.addWidget(import_btn)

        export_btn = QPushButton("📤 Export Config...")
        export_btn.clicked.connect(self._export_config)
        ie_layout.addWidget(export_btn)

        self.add_widget(ie_widget)

        # Validation status
        self._validation_label = QLabel("")
        self._validation_label.setWordWrap(True)
        self.add_widget(self._validation_label)

        self.add_stretch()

        # Load initial config
        self._load_tree()

        # Connect tree selection
        self._tree.itemClicked.connect(self._on_item_selected)

    def _load_tree(self) -> None:
        """Load configuration into tree view."""
        self._tree.clear()
        config = self.config.config

        def add_items(parent: QTreeWidgetItem, data: dict, prefix: str = "") -> None:
            for key, value in data.items():
                key_path = f"{prefix}.{key}" if prefix else key
                item = QTreeWidgetItem(parent)
                item.setText(0, key)
                item.setData(0, Qt.ItemDataRole.UserRole, key_path)

                if isinstance(value, dict):
                    item.setText(1, "")
                    add_items(item, value, key_path)
                elif isinstance(value, list):
                    item.setText(1, json.dumps(value))
                else:
                    item.setText(1, str(value))

        for key, value in config.items():
            item = QTreeWidgetItem(self._tree)
            item.setText(0, key)
            item.setData(0, Qt.ItemDataRole.UserRole, key)

            if isinstance(value, dict):
                item.setText(1, "")
                add_items(item, value, key)
            elif isinstance(value, list):
                item.setText(1, json.dumps(value))
            else:
                item.setText(1, str(value))

        self._tree.expandAll()

    def _on_item_selected(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle item selection.

        Args:
            item: Selected tree item.
            column: Clicked column.
        """
        key_path = item.data(0, Qt.ItemDataRole.UserRole)
        value = item.text(1)

        if value:  # Only editable if it's a leaf node
            self._key_label.setText(key_path)
            self._value_input.setText(value)
            self._current_item = item
        else:
            self._key_label.setText("-")
            self._value_input.setText("")
            self._current_item = None

    def _edit_item(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle double-click to edit.

        Args:
            item: Double-clicked tree item.
            column: Clicked column.
        """
        if column == 1 and item.text(1):
            self._value_input.setFocus()
            self._value_input.selectAll()

    def _apply_change(self) -> None:
        """Apply the current edit."""
        if not hasattr(self, "_current_item") or self._current_item is None:
            return

        key_path = self._key_label.text()
        new_value = self._value_input.text()

        # Try to convert to appropriate type
        try:
            # Try JSON first (for lists and booleans)
            converted = json.loads(new_value)
        except json.JSONDecodeError:
            # Try numeric
            try:
                if "." in new_value:
                    converted = float(new_value)
                else:
                    converted = int(new_value)
            except ValueError:
                # Keep as string
                converted = new_value

        # Update config
        self.config.set(key_path, converted)

        # Update tree
        self._current_item.setText(1, str(new_value))

        self.log(f"[Config] Updated {key_path} = {converted}")
        self._validate_config()

    def _save_config(self) -> None:
        """Save configuration to file."""
        errors = self.config.validate()
        if errors:
            reply = QMessageBox.warning(
                self,
                "Validation Warnings",
                "Configuration has warnings:\n\n"
                + "\n".join(errors)
                + "\n\nSave anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.config.save()
        self.log("[Config] Configuration saved")

    def _reload_config(self) -> None:
        """Reload configuration from file."""
        self.config.load()
        self._load_tree()
        self.log("[Config] Configuration reloaded")
        self._validate_config()

    def _import_config(self) -> None:
        """Import configuration from file."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Configuration",
            "",
            "YAML Files (*.yml *.yaml);;All Files (*)",
        )
        if path:
            from ruamel.yaml import YAML

            yaml = YAML()
            with open(path, "r", encoding="utf-8") as f:
                imported = yaml.load(f)

            if imported:
                # Merge imported config
                for key, value in imported.items():
                    self.config.set_section(key, value)

                self._load_tree()
                self.log(f"[Config] Imported configuration from {path}")

    def _export_config(self) -> None:
        """Export configuration to file."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Configuration",
            "config_export.yaml",
            "YAML Files (*.yml *.yaml);;All Files (*)",
        )
        if path:
            from ruamel.yaml import YAML

            yaml = YAML()
            yaml.preserve_quotes = True
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(self.config.config, f)

            self.log(f"[Config] Exported configuration to {path}")

    def _validate_config(self) -> None:
        """Validate configuration and show status."""
        errors = self.config.validate()
        if errors:
            self._validation_label.setText(
                "⚠️ " + "\n⚠️ ".join(errors)
            )
            self._validation_label.setStyleSheet("color: #ffa500;")
        else:
            self._validation_label.setText("✓ Configuration valid")
            self._validation_label.setStyleSheet("color: #00ff00;")

    def on_show(self) -> None:
        """Called when module is shown."""
        self._load_tree()
        self._validate_config()
