import requests
from pydantic import HttpUrl, ValidationError
from typing import Any, List, Dict, Optional
import logging
from pathlib import Path
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
                        "Taxonomy": f"{release.taxonomy_source.name}:{release.taxonomy_source.version}",
                        "Pangenome Count": release.pangenome_count,
                    }
                )

    return pd.DataFrame(data)


def get_mash_sketch_file(
    api_url: HttpUrl, collection: CollectionPublicWithReleases, outdir: Path
):
    """ """
    latest_release = next(
        (release for release in collection.releases if release.latest), None
    )

    if not latest_release:
        raise ValueError(f"No latest release found for collection {collection.name}")

    output_file_path = (
        outdir
        / "mash_sketch"
        / f"collection_{collection.name}_{latest_release.version}.msh"
    )
    output_file_path.parent.mkdir(parents=True, exist_ok=True)

    if output_file_path.exists():
        logger.info(
            f"Mash sketch file for collection {collection.name} already exists at {output_file_path}. No re-download."
        )
    else:

        logger.info(
            f"Downloading mash sketch file for collection to {collection.name} release {latest_release.version}"
        )
        download_mash_sketch(
            api_url=api_url,
            collection_id=collection.id,
            output_file_path=output_file_path,
        )

    if not output_file_path.exists():
        raise FileNotFoundError(
            f"Failed to download mash sketch file to {output_file_path}"
        )

    return output_file_path


def download_mash_sketch(api_url: HttpUrl, collection_id: int, output_file_path: Path):
    """ """

    try:
        response = requests.get(
            f"{api_url}/collections/{collection_id}/mash_sketch",
            timeout=10,
            stream=True,
        )
        response.raise_for_status()

        with open(output_file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"Mash sketch file saved to {output_file_path}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        exit(1)
