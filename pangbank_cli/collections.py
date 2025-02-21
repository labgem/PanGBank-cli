import requests
from rich.console import Console
from rich.table import Table
from datetime import datetime
from pydantic import HttpUrl


def query_collections(api_url:HttpUrl):

    console = Console()

    response = requests.get(f"{api_url}/collections/" )

    if response.status_code == 200:
        collections = response.json()


        if not collections:
            console.print("[bold red]No collections found in the database.[/bold red]")
        else:
            table = Table(
                title="Avalaible collections of PanGBank:",
                header_style="bold magenta",
                show_lines=True,
                title_justify="left",
            )

            table.add_column("Collection", style="bold cyan")
            table.add_column("Lastest release", style="bold cyan")
            table.add_column("Date", justify="center")
            table.add_column("Release Note", style="dim")
            table.add_column("PangBank WF", justify="center")
            table.add_column("PPanGGOLiN", justify="center")

            for collection in collections:

                for release in collection["collection_releases"]:

                    raw_date = release["date"]
                    formatted_date = datetime.fromisoformat(raw_date).strftime("%d %b %Y")  


                    table.add_row(

                        collection["name"],
                        release["version"],
                        formatted_date,
                        release["release_note"],
                        release["pangbank_wf_version"],
                        release["ppanggolin_version"],
                    )

            console.print(table)
    else:
        console.print(f"[bold red]Error: {response.status_code}[/bold red]\n{response.text}")
