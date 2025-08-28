import requests
from pydantic import HttpUrl, ValidationError
from typing import Any, List, Dict, Optional
import logging
import pandas as pd

from pangbank_api.models import CollectionPublicWithReleases  # type: ignore
from pangbank_api.crud.common import FilterCollection  # type: ignore

logger = logging.getLogger(__name__)


def get_collections(api_url: HttpUrl, filter_params: FilterCollection):
    """Fetch collections from the given API URL."""

    params = filter_params.model_dump()

    try:
        response = requests.get(f"{api_url}/collections/", params=params, timeout=10)
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


def query_collections(
    api_url: HttpUrl, collection_name: Optional[str] = None
) -> List[CollectionPublicWithReleases]:
    """Fetch and validate collections from the given API URL."""

    name_query = f"with name: '{collection_name}'" if collection_name else ""

    logger.debug(f"Fetching collections {name_query}")
    filter_params = FilterCollection(
        collection_name=collection_name, only_latest_release=True
    )
    collections_response = get_collections(api_url, filter_params)
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
