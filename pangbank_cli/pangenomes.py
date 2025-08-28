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
    TaxonPublic,
)
from pangbank_cli.utils import compute_md5
from pangbank_api.crud.common import FilterGenomeTaxonGenomePangenome, PaginationParams  # type: ignore
from itertools import groupby
from operator import attrgetter

from rich.console import Console
from rich.progress import Progress

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


def count_pangenomes(
    api_url: HttpUrl,
    filter_params: FilterGenomeTaxonGenomePangenome,
):
    """Fetch pangenomes from the API with filtering options."""

    params = filter_params.model_dump()
    response = requests.get(f"{api_url}/pangenomes/count/", params=params, timeout=10)

    try:
        response.raise_for_status()
        return int(response.text)

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
    genome_name: Optional[str] = None,
    only_latest_release: bool = True,
    substring_taxon_match: bool = False,
    disable_progress_bar: bool = False,
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
        genome_name=genome_name,
    )

    filter_logs = [
        f"{param}={value}"
        for param, value in filter_params.model_dump(exclude_none=True).items()
    ]
    logger.info(f"Counting pangenomes for {' & '.join(filter_logs)}")

    pangenome_count = count_pangenomes(api_url, filter_params)

    if pangenome_count == 0:
        logger.info("No pangenomes found matching the search criteria.")
        return []

    plural = "s" if pangenome_count > 1 else ""
    logger.info(f"Found {pangenome_count} pangenome{plural} matching search criteria.")

    logger.info(f"Fetching information for the {pangenome_count} pangenome{plural}.")

    # Progress bar for fetching
    with Progress(disable=disable_progress_bar) as progress:
        task = progress.add_task("Fetching pangenome", total=pangenome_count)

        while True:

            pagination_params = PaginationParams(offset=offset, limit=limit)
            responses_pangenomes = get_pangenomes(
                api_url=api_url,
                filter_params=filter_params,
                pagination_params=pagination_params,
            )

            logger.debug(
                f"Found {len(responses_pangenomes)} pangenomes at offset {offset}"
            )

            if not responses_pangenomes:  # If no pangenomes are returned, exit the loop
                break

            all_pangenomes.extend(
                responses_pangenomes
            )  # Add the pangenomes to the list

            progress.update(task, advance=len(responses_pangenomes))
            offset += limit  # Increment the offset for the next request

            # If the number of pangenomes fetched is less than the limit, we have reached the end
            if len(responses_pangenomes) < limit:
                break

    pangenomes = validate_pangenomes(all_pangenomes)
    collection_names = {
        f"'{pan.collection_release.collection_name}'" for pan in pangenomes
    }
    c_plural = "s" if len(collection_names) > 1 else ""
    logger.info(
        f"The {len(pangenomes)} pangenome{plural} matching search criteria {'are' if len(pangenomes) > 1 else 'is'} from {len(collection_names)} collection{c_plural} : {', '.join(collection_names)}"
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


def display_pangenome_summary_by_collection(
    pangenomes: List["PangenomePublic"], show_details: bool = True
):
    """
    Displays pangenome information grouped by collection in a YAML-like format with colors.

    :param pangenomes: List of PangenomePublic objects to display.
    :param show_details: If True, shows genome count and taxonomies for each pangenome.
    """
    console = Console(stderr=True)

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
            f"  matching_pangenome: [bold magenta]{len(pangenomes)}[/bold magenta]"
        )
        list_of_taxa = [pangenome.taxonomy.taxa for pangenome in pangenomes]
        common_taxa = get_common_taxonomy(list_of_taxa)

        yaml_lines.append(
            f"  common_taxonomy: [bold magenta]{format_taxonomy_to_string(common_taxa)}[/bold magenta]"
        )

    # Convert list to string and print with syntax highlighting
    yaml_output = "\n".join(yaml_lines + [""])
    console.print(yaml_output)


def format_taxonomy_to_string(taxonomy: List[TaxonPublic]) -> str:
    """Format a list of TaxonPublic objects into a string with alternating colors."""
    taxa_names = [taxon.name for taxon in sorted(taxonomy, key=lambda x: x.depth)]

    taxonomy_formated: List[str] = ["[italic bright_green]root[/italic bright_green]"]
    for i, taxon_name in enumerate(taxa_names):
        tag = "italic bright_green" if i % 2 else "italic green"
        taxonomy_formated.append(f"[{tag}]{taxon_name}[/{tag}]")

    taxonomy_str = ";".join(taxonomy_formated)

    return taxonomy_str


def get_common_taxonomy(list_of_taxa: List[List[TaxonPublic]]):
    common: List[TaxonPublic] = []

    if not list_of_taxa:
        return common

    # zip will group taxa at the same level across all taxonomies
    common: List[TaxonPublic] = []
    for taxa in zip(*list_of_taxa):
        if all(taxon == taxa[0] for taxon in taxa):
            common.append(taxa[0])
        else:
            break
    return common


def print_pangenome_info(
    pangenomes: List[PangenomePublic], display_count: Optional[int] = None
):

    console = Console(stderr=False)
    if display_count is not None and len(pangenomes) > display_count:
        logger.info(
            f"Displaying information for the first {display_count} pangenome{'' if display_count == 1 else 's'}:"
        )
    else:
        logger.info(
            f"Displaying information for the {len(pangenomes)} pangenome{'' if len(pangenomes) == 1 else 's'}:"
        )

    for pangenome in pangenomes[:display_count]:
        pangenome_info = format_pangenome_info(pangenome)
        console.print("\n".join(pangenome_info))


def format_pangenome_info(pangenome: "PangenomePublic") -> List[str]:

    taxonomy = [
        taxon.name for taxon in sorted(pangenome.taxonomy.taxa, key=lambda x: x.depth)
    ]

    yaml_lines: List[str] = []
    yaml_lines.append(f"[bold]{taxonomy[-1]}[/bold]:")

    taxonomy_formated: List[str] = []
    for i, taxon in enumerate(taxonomy):
        tag = "italic bright_green" if i % 2 else "italic green"
        taxonomy_formated.append(f"[{tag}]{taxon}[/{tag}]")
    taxonomy_str = ";".join(taxonomy_formated)
    yaml_lines.append(f"    collection: {pangenome.collection_release.collection_name}")
    yaml_lines.append(f"    taxonomy: {taxonomy_str}")
    yaml_lines.append(
        f"    taxonomy_source: [bright_green]{pangenome.taxonomy.taxonomy_source.name} {pangenome.taxonomy.taxonomy_source.version}[/bright_green]"
    )

    yaml_lines.append(f"    genomes: {pangenome.genome_count}")

    yaml_lines.append(f"    genes: {pangenome.gene_count}")
    yaml_lines.append(f"    families: {pangenome.family_count}")
    yaml_lines.append("    partitions:")
    yaml_lines.append(
        f"        persistent_families: {pangenome.persistent_family_count}"
    )
    yaml_lines.append(f"        shell_families: {pangenome.shell_family_count}")
    yaml_lines.append(f"        cloud_families: {pangenome.cloud_family_count}")
    yaml_lines.append(f"    modules: {pangenome.module_count}")

    yaml_lines.append(f"    RGPs: {pangenome.rgp_count}")

    yaml_lines.append(f"    spots: {pangenome.spot_count}")

    return yaml_lines


def get_pangenome_file(
    api_url: HttpUrl, pangenome_id: int, output_file: Path, expected_md5sum: str
):
    url = f"{api_url}/pangenomes/{pangenome_id}/file"

    # --- Check for existing file ---
    if output_file.exists():
        existing_md5 = compute_md5(output_file)
        if existing_md5 == expected_md5sum:
            logger.debug(
                f"File '{output_file}' already exists with valid checksum. Skipping download."
            )
            return output_file
        else:
            logger.warning(
                f"File '{output_file}' exists but checksum mismatch. Redownloading..."
            )
            logger.debug(f"Expected MD5: {expected_md5sum}, Found MD5: {existing_md5}")
            try:
                output_file.unlink()
            except Exception as cleanup_err:
                logger.error(
                    f"Failed to remove corrupted file '{output_file}': {cleanup_err}"
                )

    # --- Download file ---
    try:
        logger.debug(f"Downloading pangenome {pangenome_id} from {url} ...")
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()

        with open(output_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.debug(f"Pangenome {pangenome_id} successfully saved to '{output_file}'")

    except requests.exceptions.Timeout:
        logger.error(
            f"Request timed out while downloading pangenome {pangenome_id} from {url}"
        )
        raise

    except requests.exceptions.HTTPError as e:
        logger.error(
            f"HTTP error {e.response.status_code} while fetching pangenome {pangenome_id} from {url}"
        )
        raise

    except requests.exceptions.RequestException as e:
        logger.error(
            f"Network error while fetching pangenome {pangenome_id} from {url}: {e}"
        )
        raise

    # Verify checksum
    file_md5sum = compute_md5(output_file)
    if file_md5sum != expected_md5sum:
        logger.error(f"MD5 checksum mismatch for '{output_file}'.")

        logger.debug(f"Expected MD5: {expected_md5sum}, Found MD5: {file_md5sum}")
        # Delete corrupt file to avoid confusion
        try:
            output_file.unlink(missing_ok=True)
            logger.warning(f"Corrupted file '{output_file}' has been removed.")
        except Exception as cleanup_err:
            logger.warning(
                f"Failed to remove corrupted file '{output_file}': {cleanup_err}"
            )

        raise ValueError(
            f"MD5 checksum mismatch for pangenome {pangenome_id}. "
            f"Expected {expected_md5sum}, got {file_md5sum}"
        )

    logger.debug(f"MD5 checksum verified for '{output_file}'")

    return output_file


def download_pangenomes(
    api_url: HttpUrl,
    pangenomes: List[PangenomePublic],
    outdir: Path,
    disable_progress_bar: bool = False,
):

    logger.info(
        f"Downloading {len(pangenomes)} pangenome file{'' if len(pangenomes) == 1 else 's'} to '{outdir}/'"
    )
    with Progress(disable=disable_progress_bar) as progress:
        task = progress.add_task("Downloading pangenome", total=len(pangenomes))

        for pangenome in pangenomes:
            last_taxon = sorted(pangenome.taxonomy.taxa, key=attrgetter("depth"))[
                -1
            ].name.replace(" ", "_")

            collection_name = pangenome.collection_release.collection.name.replace(
                " ", "_"
            )
            output_file_path = (
                outdir / f"{collection_name}_{last_taxon}_id{pangenome.id}.h5"
            )
            output_file_path.parent.mkdir(parents=True, exist_ok=True)
            get_pangenome_file(
                api_url,
                pangenome.id,
                output_file_path,
                expected_md5sum=pangenome.file_md5sum,
            )

            progress.update(task, advance=1)

    logger.info(
        f"Successfully downloaded {len(pangenomes)} pangenome file{'' if len(pangenomes) == 1 else 's'} to '{outdir}/'."
    )
    return outdir
