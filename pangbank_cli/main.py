from typing import Optional

import typer
from typing_extensions import Annotated

from pangbank_cli import __version__
from rich.logging import RichHandler
import logging
import requests

from pydantic import HttpUrl
from rich.console import Console
from pangbank_cli.collections import query_collections

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
    except ValueError as e:
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


@app.command(no_args_is_help=False)
def list_collections(
    api_url: Annotated[
        HttpUrl,
        typer.Option(
            envvar="PANGBANK_URL_API",
            parser=validate_api_url,
            callback=version_callback,
        ),
    ] = HttpUrl("http://127.0.0.1:8000")
):
    """List available collections."""
    query_collections(api_url)


@app.command(no_args_is_help=True)
def search_pangenomes():
    """Search for pangenomes."""
    pass


@app.command(no_args_is_help=True)
def match_pangenome():
    """Match a pangenome from an input genome."""
    pass


if __name__ == "__main__":
    app()
