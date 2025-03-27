from typing import Optional
from rich.console import Console
from rich.table import Table
import pandas as pd
import logging
import shutil

logger = logging.getLogger(__name__)


def print_dataframe_as_rich_table(df: pd.DataFrame, title: Optional[str] = None):
    """Convert a Pandas DataFrame into a Rich table and print it efficiently using namedtuples."""
    if df.empty:
        print("No data available.")
        return

    console = Console(stderr=True)
    table = Table(
        title=title,
        show_header=True,
        header_style="bold magenta",
        show_lines=True,
        title_justify="left",
    )

    column_colors = ["deep_sky_blue1", "light_slate_grey"]  # Softer contrast
    for i, column in enumerate(df.columns):
        table.add_column(
            str(column), style=column_colors[i % len(column_colors)], justify="left"
        )

    row_styles = ["", "grey50"]  # Alternating row styles for better readability
    for i, row in enumerate(df.itertuples(index=False, name=None)):
        table.add_row(*map(str, row), style=row_styles[i % 2])

    console.print(table, new_line_start=True)


def check_mash_availability():
    """
    Check if the 'mash' tool is available in the system's PATH.

    :return: None
    """
    if shutil.which("mash") is None:
        logger.warning(
            "The 'mash' tool is not found in the system's PATH. "
            "Please install it to ensure 'pangbank match-pangenome' works correctly."
        )
        return False
    return True
