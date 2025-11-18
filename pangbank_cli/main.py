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


@app.command(no_args_is_help=False)
def list_collections(
    api_url: HttpUrl = ApiUrlOption,
    verbose: bool = Verbose,
):
    """List available collections."""
    collections = query_collections(api_url)
    logger.info(f"Found {len(collections)} collections in PanGBank.")

    df = format_collections_to_dataframe(collections)
    print_dataframe_as_rich_table(df, title="Available collections of PanGBank:")
    print_yaml = False
    if print_yaml:
        yaml_collections = format_collections_to_yaml(collections)
        print_yaml_with_rich(yaml_collections)


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
    table_path: Annotated[
        Path,
        typer.Option(
            "--table",
            help=(
                "Save a TSV table summarizing the matching pangenomes. "
                "Use '-' to print the table to stdout."
            ),
            rich_help_panel="Output and downloads",
        ),
    ] = Path("pangenomes_information.tsv"),
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
        only_latest_release=True,
        disable_progress_bar=not progress,
    )

    if not pangenomes:

        if collection is not None:
            collections = query_collections(api_url)
            existing_collection_names = [c.name for c in collections]
            if collection not in existing_collection_names:
                names_formatted = ", ".join(
                    (f"'{name}'" for name in existing_collection_names)
                )
                logger.warning(
                    f"Collection '{collection}' not found in PanGBank. "
                    f"Available collections are: {names_formatted}."
                )
        raise typer.Exit(code=1)

    df = format_pangenomes_to_dataframe(pangenomes)

    if str(table_path) == "-":
        logger.info("Printing pangenomes information as TSV table to stdout")
        output_handle: TextIO | Path = sys.stdout
    else:
        logger.info(f"Saving pangenomes information as TSV table to file: {table_path}")
        output_handle: TextIO | Path = table_path

    df.to_csv(output_handle, index=False, sep="\t")

    if details:
        display_pangenome_summary_by_collection(pangenomes, True)
        print_pangenome_info(pangenomes)

    if download:
        outdir.mkdir(parents=True, exist_ok=True)
        download_pangenomes(
            api_url, pangenomes, outdir, disable_progress_bar=not progress
        )


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
    logger.info(
        f"Searching a matching pangenome in collection '{collection_name}' for genome '{input_genome_file}'"
    )
    collections = query_collections(api_url, collection_name=collection_name)

    check_mash_availability()

    if not collections:
        logger.warning(f"No collections found for {collection_name}")
        raise typer.Exit(code=1)

    elif len(collections) > 1:
        logger.warning(
            f"Only one collection should be returned. Got {len(collections)} "
            f"when querying collection_name={collection_name}"
        )
        raise typer.Exit(code=1)
    else:
        collection = collections[0]

    logger.debug(f"Collection found: {collection.name}")
    mash_sketch_file = get_mash_sketch_file(api_url, collection, outdir)

    query_to_best_match = compute_mash_distance(mash_sketch_file, [input_genome_file])
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
