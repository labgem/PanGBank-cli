from typing import Optional, Dict, Any, List
from rich.console import Console
from rich.table import Table

from pathlib import Path
import hashlib
import pandas as pd
import logging
import shutil
import yaml
import os
from rich.syntax import Syntax

import requests
from requests.exceptions import RequestException, HTTPError
from pydantic import HttpUrl

from contextlib import contextmanager

from contextlib import contextmanager
from collections.abc import Generator

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


def print_dataframe_as_rich_table(df: pd.DataFrame, title: Optional[str] = None):
    """Convert a Pandas DataFrame into a Rich table and print it efficiently using namedtuples."""
    if df.empty:
        print("No data available.")
        return

    # Get terminal width from environment variable if set and valid
    terminal_width = None
    if "TERMINAL_WIDTH" in os.environ:
        try:
            terminal_width = int(os.environ["TERMINAL_WIDTH"])
        except ValueError:
            pass  # If not a valid integer, keep None

    console = Console(width=terminal_width)
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


def print_yaml_with_rich(data: List[Dict[str, Any]]) -> None:
    """Pretty-print a list of dicts as YAML using Rich."""

    console = Console()

    yaml_str = yaml.safe_dump(data, sort_keys=False, indent=2)
    syntax = Syntax(yaml_str, "yaml", line_numbers=False, background_color="default")
    console.print(syntax)


def compute_md5(file_path: Path):
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):  # Read file in chunks
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def fetch_api_data(api_url: HttpUrl, route: str, params: Dict[str, Any]) -> Any:
    """
    Generic function to fetch data from an API endpoint with error handling.

    Args:
        api_url: Base URL of the API.
        route: Endpoint route (e.g., "/pangenomes/").
        params: Dictionary of query parameters.

    Returns:
        Parsed JSON response from the API.

    Raises:
        HTTPError: If the API request fails or returns an error.
    """

    url = f"{api_url}{route}"
    response = requests.get(url, params=params, timeout=10)

    try:
        response.raise_for_status()
        return response.json()

    except RequestException as e:
        error_detail: List[Dict[str, Any]] = []
        try:
            error_detail = response.json().get("detail", [])
            if isinstance(error_detail, str):
                error_detail = [{"msg": error_detail}]
        except (ValueError, AttributeError):
            pass

        if error_detail:
            error_msg = error_detail[0].get("msg", "Unknown error")
            logger.error(f"API error: {error_msg}")
            raise HTTPError(f"Failed to fetch data from {url}: {error_msg}") from e
        else:
            logger.error(f"API request failed: {str(e)}")
            raise HTTPError(f"Failed to fetch data from {url}") from e
