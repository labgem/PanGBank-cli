import requests
from pydantic import HttpUrl, ValidationError
from typing import Any, Generator, Iterable, List, Dict, Optional, Tuple
import logging
import pandas as pd
from pathlib import Path
from pangbank_api.models import (  # type: ignore
    CollectionReleasePublic,
    PangenomePublic,
    CollectionPublic,
)
from pangbank_api.crud.common import FilterGenomeTaxonGenomePangenome, PaginationParams  # type: ignore
from itertools import groupby
from operator import attrgetter

from rich.console import Console

logger = logging.getLogger(__name__)


def get_pangenomes(
    api_url: HttpUrl,
    filter_params: FilterGenomeTaxonGenomePangenome,
    pagination_params: PaginationParams,
):
    """Fetch pangenomes from the API with filtering options."""

    params = filter_params.model_dump()
    params.update(pagination_params.model_dump())
    response = requests.get(f"{api_url}/pangenomes/", params=params, timeout=10)
    try:
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:

        error_detail = response.json().get("detail", [])

        if error_detail:
            logger.error(f"API error: {error_detail[0].get('msg', 'Unknown error')}")
            raise requests.HTTPError(
                f"Failed to fetch pangenomes from {api_url}: {error_detail[0].get('msg', 'Unknown error')}"
            )
        raise requests.HTTPError(f"Failed to fetch pangenomes from {api_url}") from e


def query_pangenomes(
    api_url: HttpUrl,
    taxon_name: Optional[str] = None,
    pangenome_name: Optional[str] = None,
    collection_name: Optional[str] = None,
    only_latest_release: bool = True,
    substring_taxon_match: bool = False,
) -> List[PangenomePublic]:

    all_pangenomes: List[Any] = []
    offset = 0
    limit = 100  # Number of pangenome we retrieve per request

    filter_params = FilterGenomeTaxonGenomePangenome(
        taxon_name=taxon_name,
        pangenome_name=pangenome_name,
        collection_name=collection_name,
        only_latest_release=only_latest_release,
        substring_taxon_match=substring_taxon_match,
    )
    filter_logs = [
        f"{param}={value}"
        for param, value in filter_params.model_dump(exclude_none=True).items()
    ]
    logger.info(f"Fetching pangenomes for {' & '.join(filter_logs)}")
    while True:
        pagination_params = PaginationParams(offset=offset, limit=limit)
        responses_pangenomes = get_pangenomes(
            api_url=api_url,
            filter_params=filter_params,
            pagination_params=pagination_params,
        )

        logger.debug(f"Found {len(responses_pangenomes)} pangenomes at offset {offset}")

        if not responses_pangenomes:  # If no pangenomes are returned, exit the loop
            break

        all_pangenomes.extend(responses_pangenomes)  # Add the pangenomes to the list
        offset += limit  # Increment the offset for the next request

        # If the number of pangenomes fetched is less than the limit, we have reached the end
        if len(responses_pangenomes) < limit:
            break

    pangenomes = validate_pangenomes(all_pangenomes)
    collection_names = {pan.collection_release.collection_name for pan in pangenomes}
    logger.info(
        f"Found {len(pangenomes)} pangenomes matching search criteria from {len(collection_names)} collections."
    )

    return pangenomes


def validate_pangenomes(pangenomes: List[Any]) -> List[PangenomePublic]:
    """Validate the fetched pangenomes against the PangenomePublic model."""
    validated_pangenomes: List[PangenomePublic] = []

    for i, collection in enumerate(pangenomes):
        try:
            validated_pangenomes.append(PangenomePublic(**collection))
        except ValidationError as e:
            logger.warning(f"Validation failed for collection at index {i}: {e}")
            raise ValueError(f"Failed to validate pangenomes: {e}") from e

    return validated_pangenomes


def format_element_to_dict(element: Any, columns: list[str]):
    """
    Converts a list of elements into a pandas DataFrame with a specified subset of columns.

    :param elements: List of elements to convert.
    :param columns: List of strings specifying the subset of columns to include in the DataFrame.
    :return: pandas DataFrame with the selected columns.
    """

    row: Dict[str, Optional[str]] = {}
    for column in columns:
        if hasattr(element, column):
            row[column] = getattr(element, column)
        else:
            row[column] = None  # If column not found, set as None

    return row


def format_pangenomes_to_dataframe(
    pangenomes: List[PangenomePublic],
) -> pd.DataFrame:
    """Convert a list of CollectionPublicWithReleases objects into a pandas DataFrame."""

    data: List[Dict[str, Any]] = []
    columns: List[str] = [
        "genome_count",
        "gene_count",
        "family_count",
        "edge_count",
        "persistent_family_count",
        "shell_family_count",
        "cloud_family_count",
        "partition_count",
        "rgp_count",
        "spot_count",
        "module_count",
    ]

    for pangenome in pangenomes:

        taxonomy = [
            taxon.name
            for taxon in sorted(pangenome.taxonomy.taxa, key=lambda x: x.depth)
        ]

        pangenome_info: Dict[str, Any] = {
            "collection": pangenome.collection_release.collection_name,
            "release_version": pangenome.collection_release.version,
            "name": taxonomy[-1],
            "taxonomy": ";".join(taxonomy),
        }

        pangenome_info.update(format_element_to_dict(pangenome, columns=columns))

        data.append(pangenome_info)

    return pd.DataFrame(data)


def groupby_attribute(
    elements: Iterable[Any], group_by_attribute: str, sort_by_attribute: Optional[str]
):
    """ """

    if sort_by_attribute is None:
        sort_by_attribute = group_by_attribute

    attribute_and_elements = (
        (key, list(element_group))
        for key, element_group in groupby(
            sorted(elements, key=attrgetter(sort_by_attribute)),
            key=attrgetter(group_by_attribute),
        )
    )
    return attribute_and_elements


console = Console()


def display_pangenome_info_by_collection(
    pangenomes: List["PangenomePublic"], show_details: bool = True
):
    """
    Displays pangenome information grouped by collection in a YAML-like format with colors.

    :param pangenomes: List of PangenomePublic objects to display.
    :param show_details: If True, shows genome count and taxonomies for each pangenome.
    """
    console = Console()

    collection_and_pangenomes: Generator[
        Tuple["CollectionPublic", List["PangenomePublic"]], None, None
    ] = groupby_attribute(
        pangenomes,
        group_by_attribute="collection_release.collection",
        sort_by_attribute="collection_release.collection.name",
    )

    yaml_lines: List[str] = []

    for collection, pangenomes in collection_and_pangenomes:
        yaml_lines.append(f"[bold cyan]{collection.name}[/bold cyan]:")
        yaml_lines.append(f"  description: [italic]{collection.description}[/italic]")

        release_and_pangenomes: Generator[
            Tuple["CollectionReleasePublic", List["PangenomePublic"]], None, None
        ] = groupby_attribute(
            pangenomes,
            group_by_attribute="collection_release",
            sort_by_attribute="collection_release.version",
        )

        # Only display latest release
        release, pangenomes = list(release_and_pangenomes)[0]

        yaml_lines.append(f"  release: [bold yellow]{release.version}[/bold yellow]")
        yaml_lines.append(
            f"  date: [bold yellow]{release.date.strftime('%d %b %Y')}[/bold yellow]"
        )
        yaml_lines.append(
            f"  pangenome_count: [bold magenta]{len(pangenomes)}[/bold magenta]"
        )

        if show_details:
            yaml_lines.append("  pangenomes:")
            for pangenome in pangenomes:
                taxonomy = [
                    taxon.name
                    for taxon in sorted(pangenome.taxonomy.taxa, key=lambda x: x.depth)
                ]

                yaml_lines.append(f"    name: [bold green]{taxonomy[-1]}[/bold green]")
                yaml_lines.append(
                    f"    genome_count: [bold green]{pangenome.genome_count}[/bold green]"
                )
                taxonomy_formated: List[str] = []
                for i, taxon in enumerate(taxonomy):
                    tag = "italic bright_green" if i % 2 else "italic bright_green"
                    taxonomy_formated.append(f"[{tag}]{taxon}[/{tag}]")
                taxonomy_str = ";".join(taxonomy_formated)

                yaml_lines.append(f"    taxonomy: {taxonomy_str}")

        yaml_lines.append("")

    # Convert list to string and print with syntax highlighting
    yaml_output = "\n".join(yaml_lines)
    console.print(yaml_output)


def get_pangenome_file(api_url: HttpUrl, pangenome_id: int, output_file: Path):
    try:
        response = requests.get(
            f"{api_url}/pangenomes/{pangenome_id}/file", timeout=10, stream=True
        )
        response.raise_for_status()

        with open(output_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"Pangenome file saved to {output_file}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Request failed: {e}")
        raise requests.HTTPError(
            f"Failed to fetch pangenome file from {api_url}"
        ) from e


def download_pangenomes(
    api_url: HttpUrl, pangenomes: List[PangenomePublic], outdir: Path
):

    for pangenome in pangenomes:
        last_taxon = sorted(pangenome.taxonomy.taxa, key=attrgetter("depth"))[-1]
        output_file_path = outdir / last_taxon.name.replace(" ", "_") / "pangenome.h5"
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        get_pangenome_file(api_url, pangenome.id, output_file_path)
