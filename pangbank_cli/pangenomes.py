import requests
from pydantic import HttpUrl, ValidationError
from typing import Any, List, Dict, Optional
import logging
import pandas as pd
from pathlib import Path
from pangbank_api.models import PangenomePublic

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


def get_pangenomes(
    api_url: HttpUrl,
    taxon_name: Optional[str],
    substring_match: bool = True,
    offset: int = 0,
    limit: int = 20,
):
    """Fetch pangenomes from the API with filtering options."""
    params: Dict[str, Any] = {
        "taxon_name": taxon_name,
        "substring_match": str(
            substring_match
        ).lower(),  # Convert bool to 'true'/'false'
        "offset": offset,
        "limit": limit,
    }

    try:
        response = requests.get(f"{api_url}/pangenomes/", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.warning(f"Request failed: {e}")
        raise requests.HTTPError(f"Failed to fetch pangenomes from {api_url}") from e


def query_pangenomes(api_url: HttpUrl, taxon_name: Optional[str] = None):
    responses_pangenomes = get_pangenomes(
        api_url=api_url,
        taxon_name=taxon_name,
    )

    pangenomes = validate_pangenomes(responses_pangenomes)

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


def format_pangenomes_to_dataframe(
    pangenomes: List[PangenomePublic],
) -> pd.DataFrame:
    """Convert a list of CollectionPublicWithReleases objects into a pandas DataFrame."""

    data: List[Dict[str, Any]] = []

    for pangenome in pangenomes:

        taxonomy_string = ";".join(taxon.name for taxon in pangenome.taxonomy.taxa)

        data.append(
            {
                "Collection": pangenome.collection_release.collection_name,
                "Release": pangenome.collection_release.version,
                "Genomes": pangenome.genome_count,
                "Taxonomy": taxonomy_string,
            }
        )

    return pd.DataFrame(data)


def get_pangenome_file(api_url: HttpUrl, pangenome_id: int, output_file: Path):
    try:
        response = requests.get(
            f"{api_url}/pangenomes/{pangenome_id}/file", timeout=10, stream=True
        )
        response.raise_for_status()

        with open(output_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"Pangenome file saved to {output_file}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Request failed: {e}")
        raise requests.HTTPError(
            f"Failed to fetch pangenome file from {api_url}"
        ) from e


def download_pangenomes(api_url: HttpUrl, pangenomes: List[PangenomePublic], outdir:Path):

    for pangenome in pangenomes:
        output_file_path = outdir / pangenome.file_name 
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        get_pangenome_file(api_url, pangenome.id, output_file_path)
