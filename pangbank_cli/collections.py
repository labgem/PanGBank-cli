import logging
from typing import Any

import pandas as pd
from pangbank_api.models import CollectionPublicWithReleases
from pangbank_api.sdk import PanGBankClient
from pydantic import HttpUrl

logger = logging.getLogger(__name__)


def query_collections(
    api_url: HttpUrl,
    collection_name: str | None = None,
    latest: bool | None = None,
    release_version: str | None = None,
) -> list[CollectionPublicWithReleases]:
    """Fetch collections from the given API URL."""

    name_query = f"with name: '{collection_name}'" if collection_name else ""

    logger.debug(f"Fetching collections {name_query}")
    with PanGBankClient(
        base_url=str(api_url),
    ) as client:
        collections = client.collections.list(
            collection_name=collection_name,
            only_latest_release=latest,
            release_version=release_version,
        )

    return collections


def format_collections_to_dataframe(
    collections: list[CollectionPublicWithReleases], latest: bool = True
) -> pd.DataFrame:
    """Convert a list of CollectionPublicWithReleases objects into a pandas DataFrame."""

    data: list[dict[str, Any]] = []

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


def log_no_pangenome_search_context(
    api_url: HttpUrl,
    collection: str | None,
    release_version: str | None,
) -> None:
    """Log contextual warnings to explain why a pangenome search returned no result."""

    collections = query_collections(api_url, latest=False)
    existing_collection_names = [c.name for c in collections]

    if collection is not None and collection not in existing_collection_names:
        names_formatted = ", ".join(f"'{name}'" for name in existing_collection_names)
        logger.warning(
            f"Collection '{collection}' not found in PanGBank. "
            f"Available collections are: {names_formatted}."
        )

    if release_version is not None:
        if collection is None:
            searchable_collections = collections
        else:
            searchable_collections = [c for c in collections if c.name == collection]

        release_exists_in_scope = any(
            release.version == release_version
            for current_collection in searchable_collections
            for release in current_collection.releases
        )

        if not release_exists_in_scope:
            if collection is None:
                logger.warning(
                    f"Release version '{release_version}' was not found in PanGBank."
                )
            elif searchable_collections:
                available_versions = sorted(
                    {
                        release.version
                        for current_collection in searchable_collections
                        for release in current_collection.releases
                    }
                )
                if available_versions:
                    logger.warning(
                        f"Release version '{release_version}' was not found in collection '{collection}'. "
                        f"Available releases are: {', '.join(available_versions)}."
                    )
                else:
                    logger.warning(
                        f"No releases were found for collection '{collection}'."
                    )
        else:
            logger.warning(
                f"Release version '{release_version}' exists, but no pangenomes matched the other search filters."
            )
