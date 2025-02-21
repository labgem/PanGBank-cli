from typing import Optional

import typer
from typing_extensions import Annotated

from pangbank_cli import __version__
from rich.logging import RichHandler
import logging

logger = logging.getLogger(__name__)

app = typer.Typer(
    help="PanGBank CLI: Command-line tool for retrieving pangenomes using the PanGBank API."
)


def version_callback(value: bool):
    """Prints the version and exits if --version is passed."""
    if value:
        typer.echo(f"PanGBank {__version__}")
        raise typer.Exit()


@app.command(no_args_is_help=True)
def main(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version", callback=version_callback, help="Show the version and exit."
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


if __name__ == "__main__":
    app()
