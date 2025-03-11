import requests
from rich.console import Console
from rich.table import Table
from pydantic import HttpUrl, ValidationError
from typing import Any, List, Dict
import logging
import pandas as pd

from pangbank_api.models import CollectionPublicWithReleases


logger = logging.getLogger(__name__)


def get_collections(api_url: HttpUrl):
    """Fetch collections from the given API URL."""
    try:
        response = requests.get(f"{api_url}/collections/", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.warning(f"Request failed: {e}")
        raise requests.HTTPError(f"Failed to fetch collections from {api_url}") from e


def validate_collections(collections: List[Any]) -> List[CollectionPublicWithReleases]:
    """Validate the fetched collections against the CollectionPublicWithReleases model."""
    validated_collections: List[CollectionPublicWithReleases] = []

    for i, collection in enumerate(collections):
        try:
            validated_collections.append(CollectionPublicWithReleases(**collection))
        except ValidationError as e:
            logger.warning(f"Validation failed for collection at index {i}: {e}")
            raise ValueError(f"Failed to validate collections: {e}") from e

    return validated_collections


def query_collections(api_url: HttpUrl) -> List[CollectionPublicWithReleases]:
    """Fetch and validate collections from the given API URL."""
    collections_response = get_collections(api_url)
    return validate_collections(collections_response)


def format_collections_to_dataframe(
    collections: List[CollectionPublicWithReleases],
) -> pd.DataFrame:
    """Convert a list of CollectionPublicWithReleases objects into a pandas DataFrame."""

    data: List[Dict[str, Any]] = []

    for collection in collections:
        for release in collection.releases:
            if release.latest:

                data.append(
                    {
                        "Collection": collection.name,
                        "Description": collection.description,
                        "Latest release": release.version,
                        "Release date": release.date.strftime("%d %b %Y"),
                        "Taxonomy": f"{release.taxonomy_source.name}:{release.taxonomy_source.version}",
                        "Pangenome Count": release.pangenome_count,
                    }
                )

    return pd.DataFrame(data)


def print_dataframe_as_rich_table(df: pd.DataFrame):
    """Convert a Pandas DataFrame into a Rich table and print it efficiently using namedtuples."""
    if df.empty:
        print("No data available.")
        return

    console = Console()
    table = Table(
        title="Avalaible collections of PanGBank:",
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
