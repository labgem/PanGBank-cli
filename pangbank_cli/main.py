from typing import Optional

import typer
from typing_extensions import Annotated

from pangbank_cli import __version__
from rich.logging import RichHandler
import logging

logger = logging.getLogger(__name__)

app = typer.Typer(
    help=f"PanGBank CLI {__version__}: Command-line tool for retrieving pangenomes using the PanGBank API.",
)


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
    typer.echo(
        "PanGBank CLI is under development. Run `pangbank --help` for available commands.",
        color=True,
    )


@app.command(no_args_is_help=True)
def list_collections():
    """List available collections."""
    pass


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
