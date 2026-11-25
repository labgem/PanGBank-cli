import contextlib
import hashlib
import logging
import os
import shutil
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import pandas as pd
from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)


@contextmanager
def silence_logger(
    name: str,
    level: int = logging.WARNING,
) -> Generator[None, None, None]:
    """Temporarily change the logging level of a logger."""
    target_logger = logging.getLogger(name)
    previous_level = target_logger.getEffectiveLevel()

    target_logger.setLevel(level)
    try:
        yield
    finally:
        target_logger.setLevel(previous_level)


def print_dataframe_as_rich_table(df: pd.DataFrame, title: str | None = None) -> None:
    """Print a pandas DataFrame as a Rich table."""
    if df.empty:
        print("No data available.")
        return

    # Get terminal width from environment variable if set and valid
    terminal_width = None
    if "TERMINAL_WIDTH" in os.environ:
        with contextlib.suppress(ValueError):  # If not a valid integer, keep None
            terminal_width = int(os.environ["TERMINAL_WIDTH"])

    console = Console(width=terminal_width)
    table = Table(
        title=title,
        show_header=True,
        header_style="bold magenta",
        show_lines=True,
        title_justify="left",
    )

    column_colors = ["deep_sky_blue1", "light_slate_grey"]  # Softer contrast
    for i, column in enumerate(map(str, df.columns)):
        table.add_column(
            column, style=column_colors[i % len(column_colors)], justify="left"
        )

    row_styles = ["", "grey50"]  # Alternating row styles for better readability
    for i, row in enumerate(df.itertuples(index=False, name=None)):
        table.add_row(*map(str, row), style=row_styles[i % 2])

    console.print(table, new_line_start=True)


def check_mash_availability() -> bool:
    """Return True if the 'mash' tool is on PATH, otherwise log an error and return False."""
    if shutil.which("mash") is None:
        logger.error(
            "The 'mash' tool is not found in the system's PATH. "
            "Please install it to use 'pangbank match-pangenome'."
        )
        return False
    return True


def compute_md5(file_path: Path) -> str:
    """Return the hex MD5 digest of a file, read in chunks."""
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()
