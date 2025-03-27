from pathlib import Path
from typing import Optional

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
    get_mash_sketch_file,
)
from pangbank_cli.utils import print_dataframe_as_rich_table, check_mash_availability

from pangbank_cli.pangenomes import (
    query_pangenomes,
    format_pangenomes_to_dataframe,
    download_pangenomes,
    display_pangenome_info_by_collection,
)

logger = logging.getLogger(__name__)
err_console = Console(stderr=True)

app = typer.Typer(
    name="PanGBank CLI",
    help=f"PanGBank CLI {__version__}: Command-line tool for retrieving pangenomes using the PanGBank API.",
    context_settings={"help_option_names": ["-h", "--help"]},
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

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=err_console)],
    )

    """Main entry point for PanGBank CLI."""


ApiUrlOption = typer.Option(
    HttpUrl("http://127.0.0.1:8000"),
    envvar="PANGBANK_URL_API",
    parser=validate_api_url,
    help="URL of the PanGBank API.",
)


@app.command(no_args_is_help=False)
def list_collections(
    api_url: HttpUrl = ApiUrlOption,
):
    """List available collections."""
    collections = query_collections(api_url)
    df = format_collections_to_dataframe(collections)

    print_dataframe_as_rich_table(df, title="Avalaible collections of PanGBank:")


@app.command(no_args_is_help=True)
def search_pangenomes(
    api_url: HttpUrl = ApiUrlOption,
    taxon: Annotated[
        Optional[str],
        typer.Option("--taxon", "-t", help="Filter pangenomes by taxonomy."),
    ] = None,
    download: bool = typer.Option(
        False,
        help="Download the pangenomes.",
    ),
    outdir: Path = typer.Option(
        Path("pangbank"),
        help="Output directory for downloaded pangenomes.",
    ),
):
    """Search for pangenomes."""
    pangenomes = query_pangenomes(api_url, taxon_name=taxon)

    df = format_pangenomes_to_dataframe(pangenomes)

    logger.info(f"Saving pangenomes information to {outdir}")
    outdir.mkdir(parents=True, exist_ok=True)
    df.to_csv(outdir / "pangenomes.tsv", index=False, sep="\t")

    display_pangenome_info_by_collection(pangenomes, False)

    if download:
        download_pangenomes(api_url, pangenomes, outdir)


@app.command(no_args_is_help=True)
def match_pangenome(
    collection_name: Annotated[
        str,
        typer.Option(
            "--collection",
            "-c",
            help="The pangenome collection to match in.",
        ),
    ],
    # input_genome_file: Annotated[
    #     str,
    #     typer.Option(
    #         "--input_genome",
    #         "-i",
    #         help="Input genome to search a matching pangenome from.",
    #     ),
    # ],
    api_url: HttpUrl = ApiUrlOption,
    download: bool = typer.Option(
        False,
        help="Download the pangenome.",
    ),
    outdir: Path = typer.Option(
        Path("pangbank"),
        help="Output directory for downloaded pangenomes.",
    ),
):
    """Match a pangenome from an input genome."""

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

    mash_sketch_file = get_mash_sketch_file(api_url, collection, outdir)
    print(mash_sketch_file)


if __name__ == "__main__":
    app()
