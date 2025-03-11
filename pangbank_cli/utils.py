
from typing import Optional
from rich.console import Console
from rich.table import Table
import pandas as pd

def print_dataframe_as_rich_table(df: pd.DataFrame, title:Optional[str]=None):
    """Convert a Pandas DataFrame into a Rich table and print it efficiently using namedtuples."""
    if df.empty:
        print("No data available.")
        return

    console = Console()
    table = Table(
        title=title,
        show_header=True,
        header_style="bold magenta",
        show_lines=True,
        title_justify="left",
    )

    for column in df.columns:
        table.add_column(str(column), style="cyan", justify="left")

    for row in df.itertuples(index=False, name=None):
        table.add_row(*map(str, row))

    console.print(table, new_line_start=True)
