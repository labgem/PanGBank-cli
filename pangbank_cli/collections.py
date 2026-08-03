from pangbank_api.sdk import PanGBankClient
from pydantic import HttpUrl, ValidationError
from typing import Any, List, Dict, Optional
import logging
import pandas as pd

from pangbank_api.models import CollectionPublicWithReleases  # type: ignore
from pangbank_api.crud.common import FilterCollection  # type: ignore
from pangbank_cli.utils import fetch_api_data

logger = logging.getLogger(__name__)


def get_collections(api_url: HttpUrl, filter_params: FilterCollection):
    """Fetch collections from the given API URL."""

    params = filter_params.model_dump()

    return fetch_api_data(api_url, "/collections/", params)


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


def query_collections(
    api_url: HttpUrl, collection_name: Optional[str] = None, latest: bool = True
) -> List[CollectionPublicWithReleases]:
    """Fetch and validate collections from the given API URL."""

    name_query = f"with name: '{collection_name}'" if collection_name else ""

    logger.debug(f"Fetching collections {name_query}")
    with PanGBankClient(
        base_url=str(api_url),
    ) as client:
        collections = client.collections.list(
            collection_name=collection_name, only_latest_release=latest
        )

    return collections


def format_collections_to_dataframe(
    collections: List[CollectionPublicWithReleases], latest: bool = True
) -> pd.DataFrame:
    """Convert a list of CollectionPublicWithReleases objects into a pandas DataFrame."""

    data: List[Dict[str, Any]] = []

    for collection in collections:
        for release in collection.releases:
            if latest and not release.latest:
                continue
            data.append(
                {
                    "Collection": collection.name,
                    "Description": collection.description,
                    "Release": release.version,
                    "Release date": release.date.strftime("%d %b %Y"),
                    "Taxonomy": (
                        f"{release.taxonomy_source.name}:{release.taxonomy_source.version}"
                    ),
                    "Pangenome Count": release.pangenome_count,
                }
            )

    return pd.DataFrame(data)


def format_collections_to_yaml(
    collections: List[CollectionPublicWithReleases],
):
    """Convert a list of CollectionPublicWithReleases objects into a YAML string."""

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
                        "Taxonomy": {
                            "name": release.taxonomy_source.name,
                            "version": release.taxonomy_source.version,
                        },
                        "Pangenome Count": release.pangenome_count,
                    }
                )

    return data
