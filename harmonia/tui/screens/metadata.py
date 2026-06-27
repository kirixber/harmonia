from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Button, Input, Static, DataTable

from .base import BaseScreen
from ...core.metadata.rename import NAMED_TEMPLATES


class MetadataScreen(BaseScreen):
    TITLE = "Metadata"

    def compose(self) -> ComposeResult:
        with Vertical(id="metadata-area"):
            yield Static("Metadata", classes="screen-title")
            yield Button("1. Validation Report", id="meta-validate", classes="menu-item")
            yield Button("2. Normalize Tags", id="meta-normalize", classes="menu-item")
            yield Button("3. Rename Files", id="meta-rename", classes="menu-item")
            yield Button("4. Edit Track", id="meta-edit", classes="menu-item")

            with Horizontal(id="meta-inputs"):
                yield Input(placeholder="Track ID", id="meta-track-id")
                yield Input(placeholder="Field (title, artist, album…)", id="meta-field")
                yield Input(placeholder="New value", id="meta-value")
                yield Input(placeholder="Template / Base dir", id="meta-template")
            yield Static(id="meta-progress")
            yield DataTable(id="meta-results")

    def on_mount(self) -> None:
        dt = self.query_one("#meta-results", DataTable)
        dt.add_columns("Key", "Value")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "meta-validate":
            self._validate()
        elif event.button.id == "meta-normalize":
            self._normalize()
        elif event.button.id == "meta-rename":
            self._rename()
        elif event.button.id == "meta-edit":
            self._edit()

    def _validate(self) -> None:
        report = self.library.metadata_report()
        dt = self.query_one("#meta-results", DataTable)
        dt.clear()
        for category, count in report.summary.items():
            dt.add_row(category.replace("_", " "), str(count))
        self.query_one("#meta-progress", Static).update(
            f"{report.total} issue(s) across the library."
        )

    def _normalize(self) -> None:
        outcomes = self.library.normalize_all(dry_run=True)
        dt = self.query_one("#meta-results", DataTable)
        dt.clear()
        if not outcomes:
            self.query_one("#meta-progress", Static).update(
                "[green]Nothing to normalize — tags already clean.[/green]"
            )
            return
        for tid, outcome in outcomes:
            from pathlib import Path
            name = Path(self.library.db.get_track(tid)["path"]).name
            for change in outcome.write.changes:
                dt.add_row(name, str(change))
        self.query_one("#meta-progress", Static).update(
            "[yellow]Preview only. Use --apply from CLI to write changes.[/yellow]"
        )

    def _rename(self) -> None:
        template = self.query_one("#meta-template", Input).value.strip()
        if not template:
            self.query_one("#meta-progress", Static).update(
                f"Presets: {', '.join(NAMED_TEMPLATES)}. Enter template above."
            )
            return
        plans = self.library.rename_all(template, dry_run=True)
        dt = self.query_one("#meta-results", DataTable)
        dt.clear()
        shown = 0
        for plan in plans:
            if plan.status.value in ("unchanged",):
                continue
            from pathlib import Path
            dest = Path(plan.new_path).name if plan.new_path else "—"
            dt.add_row(plan.status.value, f"{Path(plan.old_path).name} → {dest}")
            shown += 1
        if shown == 0:
            self.query_one("#meta-progress", Static).update(
                "[green]All files already match the template.[/green]"
            )
        else:
            self.query_one("#meta-progress", Static).update(
                "[yellow]Preview only. Use --apply from CLI to move files.[/yellow]"
            )

    def _edit(self) -> None:
        track_id_str = self.query_one("#meta-track-id", Input).value.strip()
        field = self.query_one("#meta-field", Input).value.strip()
        value = self.query_one("#meta-value", Input).value.strip()
        if not track_id_str.isdigit():
            self.query_one("#meta-progress", Static).update(
                "[red]Track ID must be a number.[/red]"
            )
            return
        if not field:
            self.query_one("#meta-progress", Static).update(
                "[red]Enter a field name (title, artist, album…).[/red]"
            )
            return
        try:
            outcome = self.library.edit_track(
                int(track_id_str), {field: value}, dry_run=True
            )
        except (KeyError, ValueError) as exc:
            self.query_one("#meta-progress", Static).update(f"[red]{exc}[/red]")
            return

        if outcome.blocked:
            msgs = [f"{i.field}: {i.message}" for i in outcome.issues if i.severity.value == "error"]
            self.query_one("#meta-progress", Static).update(
                f"[red]Blocked:[/red] {'; '.join(msgs)}"
            )
            return

        dt = self.query_one("#meta-results", DataTable)
        dt.clear()
        if outcome.write is None or not outcome.write.changes:
            self.query_one("#meta-progress", Static).update(
                "[dim]No changes — values already match.[/dim]"
            )
        else:
            for c in outcome.write.changes:
                dt.add_row(str(c), "")
            self.query_one("#meta-progress", Static).update(
                "[yellow]Preview only. Use --apply from CLI to write changes.[/yellow]"
            )
