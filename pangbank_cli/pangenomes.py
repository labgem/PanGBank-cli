import logging
import re
from collections import defaultdict
from operator import attrgetter
from pathlib import Path
from typing import TypedDict

import pandas as pd
import requests
from pangbank_api.exports.pangenomes import build_table_of_pangenomes
from pangbank_api.models import PangenomePublic, TaxonPublic
from pangbank_api.sdk import PanGBankClient, PanGBankNotFoundError
from pydantic import HttpUrl
from rich.console import Console
from rich.markup import escape
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from pangbank_cli.utils import compute_md5, silence_logger

logger = logging.getLogger(__name__)


class PangenomeFilters(TypedDict):
    """Filters accepted by the SDK's `pangenomes.list` and `pangenomes.count`.

    Unpacked with `**` into those calls, so pyright checks every key and value
    type against the SDK signature: a renamed SDK parameter is a type error.
    """

    taxon_name: str | None
    pangenome_name: str | None
    collection_name: str | None
    genome_name: str | None
    release_version: str | None
    only_latest_release: bool
    substring_taxon_match: bool


def get_pangenomes(
    api_url: HttpUrl,
    filters: PangenomeFilters,
    offset: int,
    limit: int,
) -> list[PangenomePublic]:
    """Fetch one page of pangenomes matching the filters."""

    with PanGBankClient(
        base_url=str(api_url),
    ) as client:
        try:
            return client.pangenomes.list(**filters, offset=offset, limit=limit)
        except PanGBankNotFoundError:
            logger.warning("No pangenomes found matching the search criteria.")
            return []


def count_pangenomes(api_url: HttpUrl, filters: PangenomeFilters) -> int:
    """Count pangenomes matching the filters."""

    with PanGBankClient(
        base_url=str(api_url),
    ) as client:
        try:
            return client.pangenomes.count(**filters)
        except PanGBankNotFoundError:
            logger.warning("No pangenomes found matching the search criteria.")
            return 0


def query_pangenome_by_id(
    api_url: HttpUrl, pangenome_id: int
) -> PangenomePublic | None:
    """Fetch a pangenome by its ID."""

    with PanGBankClient(
        base_url=str(api_url),
    ) as client:
        try:
            pangenome = client.pangenomes.get(pangenome_id)
        except PanGBankNotFoundError:
            logger.warning(f"Pangenome with ID {pangenome_id} not found.")
            return None

    return pangenome


def query_pangenomes(
    api_url: HttpUrl,
    taxon_name: str | None = None,
    pangenome_name: str | None = None,
    collection_name: str | None = None,
    genome_name: str | None = None,
    release_version: str | None = None,
    only_latest_release: bool = True,
    substring_taxon_match: bool = False,
    disable_progress_bar: bool = False,
) -> list[PangenomePublic]:
    """Count then fetch, page by page, all pangenomes matching the filters."""

    all_pangenomes: list[PangenomePublic] = []
    offset = 0
    limit = 100  # Number of pangenomes we retrieve per request (API maximum)

    filters = PangenomeFilters(
        taxon_name=taxon_name,
        pangenome_name=pangenome_name,
        collection_name=collection_name,
        only_latest_release=only_latest_release,
        substring_taxon_match=substring_taxon_match,
        genome_name=genome_name,
        release_version=release_version,
    )

    filter_logs = [
        f"{param}={value}" for param, value in filters.items() if value is not None
    ]
    logger.info(f"Counting pangenomes for {' & '.join(filter_logs)}")

    pangenome_count = count_pangenomes(api_url, filters)

    if pangenome_count == 0:
        logger.info("No pangenomes found matching the search criteria.")
        return []

    plural = "s" if pangenome_count > 1 else ""
    logger.info(f"Found {pangenome_count} pangenome{plural} matching search criteria.")

    logger.info(f"Fetching information for {pangenome_count} pangenome{plural}.")

    # Progress bar for fetching
    progress_console = Console(stderr=True)
    with (
        Progress(console=progress_console, disable=disable_progress_bar) as progress,
        silence_logger("httpx", logging.WARNING),
    ):
        task = progress.add_task("Fetching pangenome", total=pangenome_count)

        while True:
            responses_pangenomes = get_pangenomes(
                api_url=api_url,
                filters=filters,
                offset=offset,
                limit=limit,
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

    pangenomes = all_pangenomes

    if not pangenomes:
        logger.info("No pangenome found matching the search criteria.")
        return []

    return pangenomes


def format_pangenomes_to_dataframe(
    pangenomes: list[PangenomePublic],
) -> pd.DataFrame:
    """Convert pangenomes into a pandas DataFrame."""

    headers, rows = build_table_of_pangenomes(pangenomes)
    return pd.DataFrame(rows, columns=pd.Index(headers))


def version_sort_key(version: str) -> tuple[tuple[int, int | str], ...]:
    """
    Sort key that orders version strings numerically ('2.0.0' < '10.0.0').

    Numeric parts compare as integers and come before text parts, so
    non-standard versions (e.g. '2.0.0-beta') still sort without errors.
    """
    parts = re.findall(r"\d+|[^\d.\-_]+", version)
    return tuple((0, int(p)) if p.isdigit() else (1, p) for p in parts)


def get_common_taxonomy(list_of_taxa: list[list[TaxonPublic]]) -> list[TaxonPublic]:
    """Return the taxa shared by all taxonomies, from the root down to the deepest common rank."""
    common: list[TaxonPublic] = []

    # Sort each taxonomy by depth so zip groups taxa of the same rank together.
    sorted_taxa = [sorted(taxa, key=attrgetter("depth")) for taxa in list_of_taxa]
    for taxa in zip(*sorted_taxa, strict=False):
        if all(taxon == taxa[0] for taxon in taxa):
            common.append(taxa[0])
        else:
            break
    return common


def print_pangenome_info(
    pangenomes: list[PangenomePublic], display_count: int | None = None
) -> None:

    console = Console(stderr=False)
    if display_count is not None and len(pangenomes) > display_count:
        logger.info(
            f"Displaying information for the first {display_count} pangenome{'' if display_count == 1 else 's'}:"
        )
    else:
        logger.info(
            f"Displaying information for {len(pangenomes)} pangenome{'' if len(pangenomes) == 1 else 's'}:"
        )

    for pangenome in pangenomes[:display_count]:
        pangenome_info = format_pangenome_info(pangenome)
        console.print("\n".join(pangenome_info))


def format_pangenome_info(pangenome: "PangenomePublic") -> list[str]:

    taxonomy = [
        taxon.name for taxon in sorted(pangenome.taxonomy.taxa, key=lambda x: x.depth)
    ]

    yaml_lines: list[str] = []
    yaml_lines.append(f"[bold]{taxonomy[-1]}[/bold]:")

    taxonomy_formated: list[str] = []
    for i, taxon in enumerate(taxonomy):
        tag = "italic bright_green" if i % 2 else "italic green"
        taxonomy_formated.append(f"[{tag}]{taxon}[/{tag}]")
    taxonomy_str = ";".join(taxonomy_formated)

    yaml_lines.append(f"    pangenome_id: {pangenome.id}")

    yaml_lines.append(f"    collection: {pangenome.collection_release.collection_name}")
    yaml_lines.append(f"    collection_release: {pangenome.collection_release.version}")

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
    api_url: HttpUrl,
    pangenome_id: int,
    output_file: Path,
    expected_md5sum: str,
    progress: Progress | None = None,
    task_id: TaskID | None = None,
    force_redownload: bool = False,
) -> Path | None:
    """Download one pangenome file and verify its MD5.

    Return None when a local file with a different checksum exists and
    force_redownload is False: that file is left untouched.
    """
    # HttpUrl always ends with "/": strip it to avoid a "//pangenomes" path.
    url = f"{str(api_url).rstrip('/')}/pangenomes/{pangenome_id}/file"
    tmp_file = output_file.with_suffix(".tmp")

    # --- Check for existing file ---
    if output_file.exists():
        existing_md5 = compute_md5(output_file)

        if existing_md5 == expected_md5sum:
            logger.debug(
                f"File '{output_file}' already exists with valid checksum. "
                "No download required."
            )

            if progress is not None and task_id is not None:
                file_size = output_file.stat().st_size
                progress.update(task_id, total=file_size, completed=file_size)

            return output_file

        logger.debug(
            f"Existing file checksum mismatch for '{output_file}'. "
            f"Expected: {expected_md5sum}, Found: {existing_md5}"
        )

        if not force_redownload:
            if progress is not None and task_id is not None:
                progress.update(task_id, total=0, completed=0)

            logger.warning(
                f"Skipping download of '{output_file}': existing file checksum does not match "
                "the API version. The file may have been modified. Use --force to replace it."
            )
            return None

        logger.info(
            f"Replacing existing file '{output_file}' because --force was provided "
            "(checksum mismatch detected)."
        )
    # --- Download file ---
    try:
        logger.debug(f"Downloading pangenome {pangenome_id} from {url} ...")
        response = requests.get(
            url, timeout=30, stream=True, headers={"Accept-Encoding": "identity"}
        )
        response.raise_for_status()

        content_length = response.headers.get("Content-Length")
        if progress is not None and task_id is not None:
            total = int(content_length) if content_length else None
            progress.update(task_id, total=total, completed=0)

        with open(tmp_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                if progress is not None and task_id is not None:
                    progress.update(task_id, advance=len(chunk))

        logger.debug(f"Pangenome {pangenome_id} successfully saved to '{output_file}'")

        # Verify checksum
        file_md5sum = compute_md5(tmp_file)

        if file_md5sum != expected_md5sum:
            logger.error(f"MD5 checksum mismatch for '{tmp_file}'.")
            logger.debug(f"Expected MD5: {expected_md5sum}, Found MD5: {file_md5sum}")

            tmp_file.unlink(missing_ok=True)

            raise ValueError(
                f"MD5 checksum mismatch for pangenome {pangenome_id}. "
                f"Expected {expected_md5sum}, got {file_md5sum}"
            )

        # Replace existing file only after successful validation
        tmp_file.replace(output_file)

        logger.debug(f"MD5 checksum verified for '{output_file}'")

    except requests.exceptions.Timeout:
        logger.error(
            f"Request timed out while downloading pangenome {pangenome_id} from {url}"
        )
        raise

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        logger.error(
            f"HTTP error {status} while fetching pangenome {pangenome_id} from {url}"
        )
        raise

    except requests.exceptions.RequestException as e:
        logger.error(
            f"Network error while fetching pangenome {pangenome_id} from {url}: {e}"
        )
        raise

    finally:
        # Cleanup incomplete downloads
        if tmp_file.exists():
            tmp_file.unlink()

    return output_file


def download_pangenomes(
    api_url: HttpUrl,
    pangenomes: list[PangenomePublic],
    outdir: Path,
    disable_progress_bar: bool = False,
    force_redownload: bool = False,
) -> Path:

    total = len(pangenomes)
    logger.info(
        f"Downloading {total} pangenome file{'' if total == 1 else 's'} to '{outdir}/'"
    )
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        disable=disable_progress_bar,
    ) as progress:
        download_task = progress.add_task("Starting...")
        downloaded = 0
        skipped = 0

        for i, pangenome in enumerate(pangenomes):
            last_taxon = max(
                pangenome.taxonomy.taxa,
                key=attrgetter("depth"),
            ).name.replace(" ", "_")

            collection_name = pangenome.collection_release.collection.name.replace(
                " ", "_"
            )
            output_file_path = (
                outdir / f"{collection_name}_{last_taxon}_id{pangenome.id}.h5"
            )

            output_file_path.parent.mkdir(parents=True, exist_ok=True)

            progress.update(
                download_task,
                description=f"[bold cyan][{i + 1}/{total}][/bold cyan] {output_file_path.name}",
                completed=0,
            )
            result = get_pangenome_file(
                api_url,
                pangenome.id,
                output_file_path,
                expected_md5sum=pangenome.file_md5sum,
                progress=progress,
                task_id=download_task,
                force_redownload=force_redownload,
            )
            if result is None:
                skipped += 1
            else:
                downloaded += 1

    if skipped:
        logger.warning(
            f"Completed with warnings: {downloaded}/{total} pangenomes are available. "
            f"{skipped} existing file{'s' if skipped > 1 else ''} did not match the API checksum "
            "and were left unchanged (use --force to replace them)."
        )
    else:
        logger.info(f"All pangenomes are available: {downloaded}/{total} files.")
    return outdir


MAX_PANGENOMES_PER_RELEASE = 10


def format_taxonomy(taxa: list[TaxonPublic]) -> str:
    """Format a lineage as Rich markup, alternating two greens so ranks are easy to tell apart."""
    if not taxa:
        return "[dim]none[/dim]"
    parts: list[str] = []
    for i, taxon in enumerate(sorted(taxa, key=attrgetter("depth"))):
        colour = "bright_green" if i % 2 else "green"
        parts.append(f"[{colour}]{escape(taxon.name)}[/{colour}]")
    # "; " lets Rich wrap a long lineage between taxa rather than inside a name.
    return "[dim];[/dim] ".join(parts)


def log_found_pangenomes_summary(pangenomes: list[PangenomePublic]) -> None:
    """
    Log the matching pangenomes grouped by collection release: release date,
    common taxonomy, and up to MAX_PANGENOMES_PER_RELEASE pangenomes per release.

    Messages use Rich markup for colours, rendered by the CLI's RichHandler.
    """

    def log(message: str) -> None:
        logger.info(message, extra={"markup": True})

    collection_to_releases: dict[str, dict[str, list[PangenomePublic]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for pangenome in pangenomes:
        release = pangenome.collection_release
        collection_to_releases[release.collection.name][release.version].append(
            pangenome
        )

    p_plural = "s" if len(pangenomes) > 1 else ""
    c_plural = "s" if len(collection_to_releases) > 1 else ""
    log(
        f"Found [bold magenta]{len(pangenomes)}[/bold magenta] matching pangenome{p_plural} "
        f"in {len(collection_to_releases)} collection{c_plural}"
    )

    for collection_name in sorted(collection_to_releases):
        releases = collection_to_releases[collection_name]

        for version in sorted(releases, key=version_sort_key):
            release_pangenomes = releases[version]
            count = len(release_pangenomes)
            release_date = release_pangenomes[0].collection_release.date.strftime(
                "%d %b %Y"
            )
            log(
                f"[bold cyan]{escape(collection_name)}[/bold cyan] "
                f"release [bold yellow]{escape(version)}[/bold yellow] "
                f"[dim]({release_date})[/dim]: "
                f"[bold magenta]{count}[/bold magenta] matching "
                f"pangenome{'s' if count > 1 else ''}"
            )

            common_taxa = get_common_taxonomy(
                [pangenome.taxonomy.taxa for pangenome in release_pangenomes]
            )
            log(f"  [bold]common taxonomy:[/bold] {format_taxonomy(common_taxa)}")

            for pangenome in release_pangenomes[:MAX_PANGENOMES_PER_RELEASE]:
                last_taxon = max(pangenome.taxonomy.taxa, key=attrgetter("depth"))
                log(
                    f"  [dim]id=[/dim]{pangenome.id}  "
                    f"[italic green]{escape(last_taxon.name)}[/italic green]  "
                    f"[dim]{pangenome.genome_count} genomes[/dim]"
                )

            remaining = count - MAX_PANGENOMES_PER_RELEASE
            if remaining > 0:
                log(
                    f"  [dim]... and {remaining} more "
                    f"pangenome{'s' if remaining > 1 else ''} "
                    "(use --table or --details to see all)[/dim]"
                )
