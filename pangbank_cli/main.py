from pathlib import Path
from typing import Optional, TextIO
import sys
import typer
from typing_extensions import Annotated

from pangbank_cli import __version__
from rich.logging import RichHandler
import logging
import requests

from pydantic import HttpUrl
from rich.console import Console
from pangbank_cli.collections import (
    query_collections,
    format_collections_to_dataframe,
    format_collections_to_yaml,
)
from pangbank_cli.utils import (
    print_dataframe_as_rich_table,
    check_mash_availability,
    print_yaml_with_rich,
)

from pangbank_cli.pangenomes import (
    query_pangenomes,
    query_pangenome_by_id,
    format_pangenomes_to_dataframe,
    download_pangenomes,
    display_pangenome_summary_by_collection,
    print_pangenome_info,
)

from pangbank_cli.match_pangenome import (
    get_mash_sketch_file,
    compute_mash_distance,
    get_matching_pangenome,
)
from pangbank_api.models import CollectionPublicWithReleases

logger = logging.getLogger(__name__)
err_console = Console(stderr=True)

app = typer.Typer(
    name="PanGBank CLI",
    help=f"PanGBank CLI {__version__}: Command-line tool for retrieving pangenomes using the PanGBank API.",
    context_settings={"help_option_names": ["-h", "--help"]},
    add_completion=False,
    rich_markup_mode="rich",
)


def validate_api_url(api_url: str) -> HttpUrl:
    """Check if the API is reachable by making a GET request and validating the URL."""

    # Validate the URL format using Pydantic HttpUrl
    try:
        # This will raise a ValueError if the URL is not valid
        valid_url = HttpUrl(api_url)
    except ValueError:
        err_console.print(f"[bold red]Error: Invalid URL format: {api_url}[/bold red]")
        err_console.print(
            "[yellow]Tip: Ensure the URL is correctly formatted. Example: https://api.example.com[/yellow]"
        )
        raise typer.Exit(code=1)

    try:
        # Make a request to the API URL with a timeout
        health_response = requests.get(api_url, timeout=5)
        health_response.raise_for_status()  # Raise an error for bad status codes (4xx, 5xx)

        # Optionally: Check for a specific endpoint that indicates the service is healthy
        if health_response.status_code == 200:
            logger.info(f"Successfully connected to API at {api_url}")
        else:
            err_console.print(
                f"[yellow]Warning: API at {api_url} responded with status code {health_response.status_code}[/yellow]",
            )

    except requests.exceptions.RequestException as e:
        err_console.print(
            f"[bold red]Error: Could not connect to API at {api_url}[/bold red]"
        )
        err_console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)

    return valid_url


def version_callback(
    value: bool,
    ctx: typer.Context,
):
    """Prints the version and exits if --version is passed."""
    if ctx.resilient_parsing:
        return

    if value:
        typer.echo(f"PanGBank {__version__}")
        raise typer.Exit()


def verbose_callback(
    verbose: bool,
):
    """Sets the logging level to DEBUG if --verbose is passed."""
    lvl = logging.INFO

    if verbose:
        lvl = logging.DEBUG

    # Set up logging
    logging.basicConfig(
        level=lvl,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=err_console)],
    )


Verbose = typer.Option(
    False,
    "--verbose",
    help="Enable verbose logging.",
    callback=verbose_callback,
    rich_help_panel="Execution settings",
)
Outdir = typer.Option(
    help="Output directory for downloaded pangenomes.",
    rich_help_panel="Output and downloads",
)
Download = typer.Option(
    help="Download HDF5 pangenome files.",
    rich_help_panel="Output and downloads",
)
Progress = typer.Option(
    help="Show progress bar while fetching pangenomes (disable with --no-progress).",
    rich_help_panel="Execution settings",
)


@app.callback(no_args_is_help=True)
def main(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = None,
):

    pass
    """Main entry point for PanGBank CLI."""


ApiUrlOption = typer.Option(
    HttpUrl("https://pangbank-api.genoscope.cns.fr/"),
    envvar="PANGBANK_API_URL",
    parser=validate_api_url,
    help="URL of the PanGBank API.",
    rich_help_panel="Execution settings",
)


def log_no_pangenome_search_context(
    api_url: HttpUrl,
    collection: Optional[str],
    release_version: Optional[str],
):
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
                        f"Available releases are: {', '.join([f"'{version}'" for version in available_versions])}."
                    )
                else:
                    logger.warning(
                        f"No releases were found for collection '{collection}'."
                    )
        else:
            logger.warning(
                f"Release version '{release_version}' exists, but no pangenomes matched the other search filters."
            )


@app.command(no_args_is_help=False)
def list_collections(
    latest: Annotated[
        bool,
        typer.Option(
            "--latest-only",
            "-l",
            help="List only latest release of each collection.",
        ),
    ] = False,
    api_url: HttpUrl = ApiUrlOption,
    verbose: bool = Verbose,
):
    """List available collections."""
    collections = query_collections(api_url, latest=latest)

    n_release = sum(1 for c in collections for _ in c.releases)
    logger.info(
        f"Found {len(collections)} collections ({n_release} releases) in PanGBank."
    )

    df = format_collections_to_dataframe(collections, latest)

    # Use rich formatting if interactive terminal, plain TSV if redirected
    if sys.stdout.isatty():
        print_dataframe_as_rich_table(df, title="Available collections of PanGBank:")
    else:
        df.to_csv(sys.stdout, index=False, sep="\t")

    print_yaml = False
    if print_yaml:
        yaml_collections = format_collections_to_yaml(collections)
        print_yaml_with_rich(yaml_collections)


@app.command("search", no_args_is_help=True, hidden=True)
@app.command(no_args_is_help=True)
def search_pangenomes(
    # Search filters
    collection: Annotated[
        Optional[str],
        typer.Option(
            "--collection",
            "-c",
            help="Filter pangenomes by collection name (e.g. 'GTDB_refseq').",
            rich_help_panel="Search filters",
        ),
    ] = None,
    latest: Annotated[
        bool,
        typer.Option(
            "--latest-only",
            "-l",
            help="Search only in latest release of each collection.",
            rich_help_panel="Search filters",
        ),
    ] = False,
    release_version: Annotated[
        Optional[str],
        typer.Option(
            "--release-version",
            "-r",
            help=(
                "Filter pangenomes to a specific collection release version "
                "(e.g. '2.0.0')."
            ),
            rich_help_panel="Search filters",
        ),
    ] = None,
    taxon: Annotated[
        Optional[str],
        typer.Option(
            "--taxon",
            "-t",
            help="Filter pangenomes by taxon name (e.g. 'Escherichia').",
            rich_help_panel="Search filters",
        ),
    ] = None,
    genome: Annotated[
        Optional[str],
        typer.Option(
            "--genome",
            "-g",
            help="Filter pangenomes by genome assembly identifier (e.g. 'GCF_000354175.2').",
            rich_help_panel="Search filters",
        ),
    ] = None,
    exact_match: Annotated[
        bool,
        typer.Option(
            help="Use exact string matching instead of partial matches.",
            rich_help_panel="Search filters",
        ),
    ] = False,
    # Output and downloads
    download: Annotated[
        bool,
        Download,
    ] = False,
    outdir: Annotated[
        Path,
        Outdir,
    ] = Path("pangbank"),
    details: Annotated[
        bool,
        typer.Option(
            help="Display summary information for each matching pangenome.",
            rich_help_panel="Output and downloads",
        ),
    ] = False,
    table: Annotated[
        bool,
        typer.Option(
            help="Output a TSV table summarizing the matching pangenomes to stdout.",
            rich_help_panel="Output and downloads",
        ),
    ] = True,
    table_path: Annotated[
        Optional[Path],
        typer.Option(
            "--table-path",
            help=(
                "Save TSV table to a file instead of stdout (e.g., pangenomes_information.tsv). "
                "Implies --table."
            ),
            rich_help_panel="Output and downloads",
        ),
    ] = None,
    # Execution settings
    api_url: HttpUrl = ApiUrlOption,
    verbose: bool = Verbose,
    progress: Annotated[
        bool,
        Progress,
    ] = True,
):
    """Search for pangenomes."""

    pangenomes = query_pangenomes(
        api_url,
        taxon_name=taxon,
        substring_taxon_match=not exact_match,
        collection_name=collection,
        genome_name=genome,
        release_version=release_version,
        only_latest_release=latest,
        disable_progress_bar=not progress,
    )

    if not pangenomes:
        log_no_pangenome_search_context(
            api_url=api_url,
            collection=collection,
            release_version=release_version,
        )
        raise typer.Exit(code=1)

    df = format_pangenomes_to_dataframe(pangenomes)

    # Output table if enabled
    if table or table_path is not None:
        if table_path is not None:
            logger.info(
                f"Saving pangenomes information as TSV table to file: {table_path}"
            )
            output_handle: TextIO | Path = table_path
        else:
            logger.info("Printing pangenomes information as TSV table to stdout")
            output_handle: TextIO | Path = sys.stdout

        df.to_csv(output_handle, index=False, sep="\t")

    if details:
        display_pangenome_summary_by_collection(pangenomes, True)
        print_pangenome_info(pangenomes)

    if download:
        outdir.mkdir(parents=True, exist_ok=True)
        download_pangenomes(
            api_url, pangenomes, outdir, disable_progress_bar=not progress
        )


@app.command("get", no_args_is_help=True, hidden=True)
@app.command(no_args_is_help=True)
def get_pangenome(
    id: Annotated[
        int,
        typer.Argument(
            help="The unique numerical identifier of the pangenome in the pangbank database. "
            "Use this to fetch a specific pangenome by its ID.",
        ),
    ],
    # Output and downloads
    download: Annotated[
        bool,
        Download,
    ] = False,
    outdir: Annotated[
        Path,
        Outdir,
    ] = Path("pangbank"),
    # Execution settings
    api_url: HttpUrl = ApiUrlOption,
    verbose: bool = Verbose,
):
    """Get a pangenome by ID."""

    pangenome = query_pangenome_by_id(
        api_url,
        pangenome_id=id,
    )

    if not pangenome:
        raise typer.Exit(code=1)

    print_pangenome_info([pangenome])

    if download:
        outdir.mkdir(parents=True, exist_ok=True)
        download_pangenomes(api_url, [pangenome], outdir, disable_progress_bar=True)


@app.command("match", no_args_is_help=True, hidden=True)
@app.command(no_args_is_help=True)
def match_pangenome(
    collection_name: Annotated[
        str,
        typer.Option(
            "--collection",
            "-c",
            help="The pangenome collection to match in.",
            rich_help_panel="Match parameters",
        ),
    ],
    input_genome_file: Annotated[
        Path,
        typer.Option(
            "--input-genome",
            "-i",
            help="Input genome to search a matching pangenome from.",
            exists=True,
            rich_help_panel="Match parameters",
        ),
    ],
    release_version: Annotated[
        Optional[str],
        typer.Option(
            "--release-version",
            "-r",
            help=(
                "Filter collection to a specific collection release version "
                "(e.g. '2.0.0'). Default is to search in the latest release of the collection."
            ),
            rich_help_panel="Match parameters",
        ),
    ] = None,
    threads: Annotated[
        int,
        typer.Option(
            "--threads",
            "-t",
            help="Number of threads to use for computing mash distances.",
            rich_help_panel="Match parameters",
        ),
    ] = 1,
    download: Annotated[
        bool,
        Download,
    ] = False,
    outdir: Annotated[
        Path,
        Outdir,
    ] = Path("pangbank"),
    api_url: HttpUrl = ApiUrlOption,
    progress: Annotated[
        bool,
        Progress,
    ] = True,
    verbose: bool = Verbose,
):
    """Match a pangenome from an input genome."""

    latest = True
    if release_version:
        latest = False

    logger.info(
        f"Searching a matching pangenome in collection '{collection_name}' ({'latest release' if latest else f'release version {release_version}'}) for genome '{input_genome_file}'"
    )

    collections: list[CollectionPublicWithReleases] = query_collections(
        api_url,
        collection_name=collection_name,
        release_version=release_version,
        latest=latest,
    )

    check_mash_availability()

    if not collections:
        log_no_pangenome_search_context(
            api_url=api_url,
            collection=collection_name,
            release_version=release_version,
        )
        raise typer.Exit(code=1)

    elif len(collections) > 1:
        logger.warning(
            f"Only one collection should be returned. Got {len(collections)} "
            f"when querying collection_name={collection_name}"
        )
        raise typer.Exit(code=1)
    else:
        collection = collections[0]

    if not collection.releases:
        logger.warning(
            f"No releases found for collection '{collection.name}'. Cannot proceed with matching."
        )
        raise typer.Exit(code=1)

    elif len(collection.releases) > 1:
        logger.warning(
            f"Only one release should be returned. Got {len(collection.releases)} "
            f"when querying collection_name={collection_name} and release_version={release_version} and only_latest_release={latest}. "
        )
        raise typer.Exit(code=1)

    release = collection.releases[0]

    logger.debug(f"Collection found: {collection.name}: {release.version} ")

    mash_sketch_file = get_mash_sketch_file(api_url, collection, release, outdir)

    query_to_best_match = compute_mash_distance(
        mash_sketch_file, [input_genome_file], threads=threads
    )

    if query_to_best_match is None:
        raise typer.Exit(code=1)

    get_matching_pangenome(
        api_url=api_url,
        collection=collection,
        query_to_best_match=query_to_best_match,
        outdir=outdir,
        download=download,
        progress=progress,
    )


if __name__ == "__main__":
    app()
