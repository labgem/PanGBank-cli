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
)
from pangbank_cli.utils import print_dataframe_as_rich_table

from pangbank_cli.pangenomes import (
    query_pangenomes,
    format_pangenomes_to_dataframe,
    download_pangenomes,
    display_pangenome_info_by_collection,
)


logger = logging.getLogger(__name__)
err_console = Console(stderr=True)

app = typer.Typer(
    help=f"PanGBank CLI {__version__}: Command-line tool for retrieving pangenomes using the PanGBank API.",
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
        handlers=[RichHandler()],
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
    taxon: str = typer.Option(
        None,
        help="Filter pangenomes by taxonomy.",
    ),
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

    display_pangenome_info_by_collection(pangenomes, False)

    df = format_pangenomes_to_dataframe(pangenomes)

    print_dataframe_as_rich_table(
        df, title=f"Pangenome in PanGBank matching taxon={taxon}:"
    )
    if download:
        download_pangenomes(api_url, pangenomes, outdir)


@app.command(no_args_is_help=True)
def match_pangenome():
    """Match a pangenome from an input genome."""
    pass


if __name__ == "__main__":
    app()
