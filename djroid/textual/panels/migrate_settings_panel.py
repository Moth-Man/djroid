"""Migrate settings panel widget for the djroid GUI."""

from pathlib import Path
from typing import List, Optional
import uuid

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Button, Select, Input, Label
from textual.reactive import reactive
from rich.text import Text

from ..styles.colors import HighlightColors
from ...db.session import SessionLocal
from ...db.dao.migration_rule_dao import MigrationRuleDAO
from ...db.models.migration_rule import MigrationRule


CUSTOM_OPTION = "__custom__"


class RuleWidget(Static):
    """Widget representing a single migration rule with dropdowns."""

    def __init__(
        self,
        rule_id: Optional[uuid.UUID] = None,
        metadata_tag: str = "",
        metadata_value: str = "",
        destination_directory: str = "",
        available_tags: List[str] = None,
        available_values: List[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.rule_id = rule_id
        self.metadata_tag = metadata_tag
        self.metadata_value = metadata_value
        self.destination_directory = destination_directory
        self.available_tags = available_tags or []
        self.available_values = available_values or []

        # Check if current value is custom (not in available values)
        self.is_custom_value = (
            metadata_value and
            metadata_value not in self.available_values
        )

    def compose(self) -> ComposeResult:
        with Vertical(classes="rule-container"):
            with Horizontal(classes="rule-row"):
                # Metadata tag dropdown
                tag_options = [(tag, tag) for tag in self.available_tags]
                if self.metadata_tag and self.metadata_tag not in self.available_tags:
                    tag_options.insert(0, (self.metadata_tag, self.metadata_tag))

                yield Select(
                    tag_options,
                    value=self.metadata_tag if self.metadata_tag else Select.BLANK,
                    prompt="Tag",
                    id=f"tag-select-{self.rule_id or 'new'}",
                    classes="rule-select tag-select"
                )

                yield Static(":", classes="rule-separator")

                # Metadata value dropdown with Custom option at bottom
                value_options = [(val, val) for val in self.available_values]
                value_options.append(("+ Custom...", CUSTOM_OPTION))

                # Determine dropdown value
                if self.is_custom_value:
                    dropdown_value = CUSTOM_OPTION
                elif self.metadata_value and self.metadata_value in self.available_values:
                    dropdown_value = self.metadata_value
                else:
                    dropdown_value = Select.BLANK

                yield Select(
                    value_options,
                    value=dropdown_value,
                    prompt="Value",
                    id=f"value-select-{self.rule_id or 'new'}",
                    classes="rule-select value-select"
                )

                yield Static("->", classes="rule-arrow")

                # Destination directory input
                yield Input(
                    value=self.destination_directory,
                    placeholder="Destination directory path",
                    id=f"dest-input-{self.rule_id or 'new'}",
                    classes="rule-input dest-input"
                )

                # Delete button
                yield Button(
                    "X",
                    id=f"delete-btn-{self.rule_id or 'new'}",
                    classes="rule-delete-btn",
                    variant="error"
                )

            # Custom value input row (shown when Custom is selected)
            custom_row = Horizontal(
                Static("", classes="custom-spacer"),
                Static("Custom value:", classes="custom-label"),
                Input(
                    value=self.metadata_value if self.is_custom_value else "",
                    placeholder="Enter custom value",
                    id=f"custom-value-{self.rule_id or 'new'}",
                    classes="custom-value-input"
                ),
                classes="custom-row",
                id=f"custom-row-{self.rule_id or 'new'}"
            )
            custom_row.display = "block" if self.is_custom_value else "none"
            yield custom_row

    def get_metadata_value(self) -> str:
        """Get the metadata value, using custom input if Custom is selected."""
        try:
            value_select = self.query_one(".value-select", Select)

            if value_select.value == CUSTOM_OPTION:
                custom_input = self.query_one(".custom-value-input", Input)
                return custom_input.value.strip()
            elif value_select.value != Select.BLANK:
                return value_select.value

            return ""
        except Exception:
            return ""


class MigrateSettingsPanel(Static):
    """Panel for managing migration rules."""

    rules: reactive[List[dict]] = reactive([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.available_tags = []
        self.available_values_cache = {}

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("MIGRATION RULES", classes="panel-header settings-header")
            yield Static(
                "Define rules to move files based on metadata. Select '+ Custom...' for values not in list.",
                classes="settings-description"
            )

            with ScrollableContainer(id="rules-container"):
                yield Static("Loading rules...", id="rules-placeholder")

            with Horizontal(id="rules-actions"):
                yield Button("+ Add Rule", id="add-rule-btn", variant="primary")
                yield Button("Save All", id="save-rules-btn", variant="success")
                yield Button("Refresh", id="refresh-rules-btn")

    def on_mount(self) -> None:
        """Called when the widget is mounted to the DOM."""
        self.border_title = "Migrate Settings"
        self.load_available_options()
        self.load_rules()

    def load_available_options(self) -> None:
        """Load available metadata tags and cache value options."""
        db = SessionLocal()
        try:
            rule_dao = MigrationRuleDAO(db)
            self.available_tags = rule_dao.get_available_metadata_tags()

            # Pre-cache values for each tag
            for tag in self.available_tags:
                values = rule_dao.get_distinct_values_for_tag(tag)
                self.available_values_cache[tag] = values

        except Exception as e:
            self.available_tags = ["genre", "artist", "album", "key", "year"]
        finally:
            db.close()

    def load_rules(self) -> None:
        """Load existing migration rules from database."""
        db = SessionLocal()
        try:
            rule_dao = MigrationRuleDAO(db)
            rules = rule_dao.get_all_rules()

            container = self.query_one("#rules-container")
            container.remove_children()

            if not rules:
                container.mount(
                    Static("No migration rules configured. Click '+ Add Rule' to create one.",
                           id="rules-placeholder",
                           classes="no-rules-message")
                )
                return

            for rule in rules:
                # Get available values for this rule's tag
                available_values = self.available_values_cache.get(
                    rule.metadata_tag.lower(), []
                )

                widget = RuleWidget(
                    rule_id=rule.id,
                    metadata_tag=rule.metadata_tag,
                    metadata_value=rule.metadata_value,
                    destination_directory=rule.destination_directory,
                    available_tags=self.available_tags,
                    available_values=available_values,
                    classes="rule-widget"
                )
                container.mount(widget)

        except Exception as e:
            container = self.query_one("#rules-container")
            container.remove_children()
            container.mount(
                Static(f"Error loading rules: {str(e)}",
                       classes="error-message")
            )
        finally:
            db.close()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "add-rule-btn":
            self.add_new_rule()
        elif button_id == "save-rules-btn":
            self.save_all_rules()
        elif button_id == "refresh-rules-btn":
            self.load_available_options()
            self.load_rules()
        elif button_id and button_id.startswith("delete-btn-"):
            rule_id_str = button_id.replace("delete-btn-", "")
            self.delete_rule(rule_id_str)

    def add_new_rule(self) -> None:
        """Add a new empty rule widget."""
        container = self.query_one("#rules-container")

        # Remove placeholder if present
        try:
            placeholder = container.query_one("#rules-placeholder")
            placeholder.remove()
        except Exception:
            pass

        # Generate a temporary ID for the new rule
        temp_id = f"new-{uuid.uuid4().hex[:8]}"

        widget = RuleWidget(
            rule_id=None,
            metadata_tag="",
            metadata_value="",
            destination_directory="",
            available_tags=self.available_tags,
            available_values=[],
            id=f"rule-{temp_id}",
            classes="rule-widget new-rule"
        )
        container.mount(widget)

    def delete_rule(self, rule_id_str: str) -> None:
        """Delete a rule."""
        if rule_id_str == "new" or rule_id_str.startswith("new-"):
            # Just remove the widget for unsaved rules
            try:
                container = self.query_one("#rules-container")
                for child in container.children:
                    if isinstance(child, RuleWidget) and (
                        child.rule_id is None or
                        f"rule-{rule_id_str}" == child.id
                    ):
                        child.remove()
                        break
            except Exception:
                pass
        else:
            # Delete from database
            try:
                rule_uuid = uuid.UUID(rule_id_str)
                db = SessionLocal()
                try:
                    rule_dao = MigrationRuleDAO(db)
                    rule_dao.delete_rule(rule_uuid)
                finally:
                    db.close()

                self.load_rules()

            except Exception as e:
                self.notify(f"Error deleting rule: {str(e)}", severity="error")

    def save_all_rules(self) -> None:
        """Save all rules to database."""
        container = self.query_one("#rules-container")
        saved_count = 0
        error_count = 0

        db = SessionLocal()
        try:
            rule_dao = MigrationRuleDAO(db)

            for child in container.children:
                if not isinstance(child, RuleWidget):
                    continue

                # Get values from the widget
                try:
                    tag_select = child.query_one(".tag-select", Select)
                    dest_input = child.query_one(".dest-input", Input)

                    tag = tag_select.value if tag_select.value != Select.BLANK else ""

                    # Use the widget's method to get value
                    value = child.get_metadata_value()

                    dest = dest_input.value.strip()

                    # Skip incomplete rules
                    if not tag or not value or not dest:
                        continue

                    if child.rule_id:
                        # Update existing rule
                        rule_dao.update_rule(
                            child.rule_id,
                            metadata_tag=tag,
                            metadata_value=value,
                            destination_directory=dest
                        )
                    else:
                        # Create new rule
                        rule_dao.create_rule(
                            metadata_tag=tag,
                            metadata_value=value,
                            destination_directory=dest
                        )

                    saved_count += 1

                except Exception as e:
                    error_count += 1

        finally:
            db.close()

        if saved_count > 0:
            self.notify(f"Saved {saved_count} rule(s)", severity="information")
        if error_count > 0:
            self.notify(f"Failed to save {error_count} rule(s)", severity="warning")

        self.load_rules()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes."""
        select_id = event.select.id

        if select_id and "tag-select" in select_id:
            # When tag changes, update the available values in the value select
            new_tag = event.value
            if new_tag and new_tag != Select.BLANK:
                parent = event.select.parent
                if parent:
                    try:
                        # Find the rule container (go up to rule-container)
                        rule_container = parent.parent
                        value_select = rule_container.query_one(".value-select", Select)
                        new_values = self.available_values_cache.get(new_tag.lower(), [])

                        # Build options with Custom at the end
                        value_options = [(val, val) for val in new_values]
                        value_options.append(("+ Custom...", CUSTOM_OPTION))

                        value_select.set_options(value_options)
                    except Exception:
                        pass

        elif select_id and "value-select" in select_id:
            # Show/hide custom input row based on selection
            try:
                # Find the custom row - it's a sibling of the rule-row
                rule_widget = event.select.parent.parent  # rule-row -> rule-container -> RuleWidget
                if isinstance(rule_widget, RuleWidget):
                    custom_row = rule_widget.query_one(".custom-row")
                    custom_row.display = "block" if event.value == CUSTOM_OPTION else "none"
            except Exception:
                pass
