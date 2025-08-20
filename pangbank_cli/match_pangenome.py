import requests
from pydantic import BaseModel, HttpUrl
from typing import Dict, List
import logging
from pathlib import Path
from collections import defaultdict
import subprocess
from pangbank_api.models import (  # type: ignore
    CollectionPublicWithReleases,
    PangenomePublic,
)
from pangbank_cli.pangenomes import (
    query_pangenomes,
    download_pangenomes,
    print_pangenome_info,
)

# from pangbank_cli.utils import compute_md5


logger = logging.getLogger(__name__)


class MashError(Exception):
    """Custom exception for Mash-related errors."""

    pass


class MashResult(BaseModel):
    """Class to represent the result of a mash command."""

    query: str
    reference: str
    distance: float
    p_value: float


def get_mash_sketch_file(
    api_url: HttpUrl, collection: CollectionPublicWithReleases, outdir: Path
):
    """ """
    latest_release = next(
        (release for release in collection.releases if release.latest), None
    )

    if not latest_release:
        raise ValueError(f"No latest release found for collection '{collection.name}'")

    output_file_path = (
        outdir
        / "mash_sketch"
        / f"collection_{collection.name}_{latest_release.version}.msh"
    )
    output_file_path.parent.mkdir(parents=True, exist_ok=True)

    if output_file_path.exists():
        # TODO apply when md5 will be in CollectionReleasePublicWithCount model
        # md5_hash_existing_file = compute_md5(output_file_path)
        # if md5_hash_existing_file == latest_release.mash_sketch_md5sum:
        logger.info(
            f"Mash sketch file for collection '{collection.name}' already exists at '{output_file_path}'. No re-download."
        )
        return output_file_path
        # else:
        #     logger.warning(
        #         f"Mash sketch file for collection '{collection.name}' exists but MD5 mismatch. Re-downloading."
        #     )

    logger.info(
        f"Downloading mash sketch file for collection to '{collection.name}' release {latest_release.version}"
    )
    download_mash_sketch(
        api_url=api_url,
        collection_id=collection.id,
        output_file_path=output_file_path,
    )

    if not output_file_path.exists():
        raise FileNotFoundError(
            f"Failed to download mash sketch file to '{output_file_path}'"
        )

    # TODO check if md5 matches when md5 is available in CollectionReleasePublicWithCount
    return output_file_path


def download_mash_sketch(api_url: HttpUrl, collection_id: int, output_file_path: Path):
    """ """

    try:
        response = requests.get(
            f"{api_url}/collections/{collection_id}/mash_sketch",
            timeout=10,
            stream=True,
        )
        response.raise_for_status()

        with open(output_file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"Mash sketch file saved to {output_file_path}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        exit(1)


def launch_mash_dist(
    mash_sketch_file: Path,
    input_genome_files: List[Path],
    max_distance: float = 0.05,
    threads: int = 1,
) -> str:

    cmd = [
        "mash",
        "dist",
        "-p",
        str(threads),
        "-d",
        str(max_distance),
        mash_sketch_file.as_posix(),
    ]
    cmd += [input_file.as_posix() for input_file in input_genome_files]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    except FileNotFoundError as e:
        logger.error("Mash command not found. Please install Mash.")
        raise MashError("Mash command not found. Please install Mash.") from e

    except subprocess.CalledProcessError as e:
        logger.error(
            f"Mash command failed with return code {e.returncode}:\n{e.stderr}"
        )
        raise MashError(
            f"Mash command failed with return code {e.returncode}:\n{e.stderr}"
        ) from e

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise MashError("An unexpected error occurred while running Mash.") from e

    logger.debug("Mash distance computed successfully.")

    return result.stdout


def compute_mash_distance(
    mash_sketch_file: Path,
    input_genome_files: List[Path],
    max_distance: float = 0.05,
    threads: int = 1,
):
    """ """

    mash_result = launch_mash_dist(
        mash_sketch_file=mash_sketch_file,
        input_genome_files=input_genome_files,
        max_distance=max_distance,
        threads=threads,
    )
    if mash_result == "":
        input_genome_files_str = "\n".join(
            [genome.as_posix() for genome in input_genome_files]
        )
        logger.warning(
            f"No matching pangenome found for the input genome files: '{input_genome_files_str}'"
        )
        return

    genome_to_mash_hits: Dict[str, List[MashResult]] = defaultdict(list)

    for result_line in mash_result.strip().split("\n"):
        reference, query, distance, p_value, _matching_hashes = result_line.split()
        mash_result = MashResult(
            query=query,
            reference=reference,
            distance=float(distance),
            p_value=float(p_value),
        )

        if mash_result.distance <= max_distance:
            genome_to_mash_hits[query].append(mash_result)

    query_to_best_match = {
        query: min(results, key=lambda x: x.distance)
        for query, results in genome_to_mash_hits.items()
    }

    for input_genome_file in input_genome_files:
        if input_genome_file.as_posix() not in query_to_best_match:
            logger.warning(
                f"No matching reference found for {input_genome_file.as_posix()}"
            )
            continue

    return query_to_best_match


def get_matching_pangenome(
    api_url: HttpUrl,
    collection: CollectionPublicWithReleases,
    query_to_best_match: Dict[str, MashResult],
    outdir: Path,
    download: bool = False,
    progress: bool = True,
):

    pangenome_to_download: List[PangenomePublic] = []

    for query, mash_result in query_to_best_match.items():
        pangenome_name = get_pangenome_name_from_mash_reference(mash_result.reference)
        logger.info(
            f"Genome '{query}' matches pangenome '{pangenome_name}' with a distance of {mash_result.distance:.6f}"
        )

        matching_pangenomes = query_pangenomes(
            api_url,
            collection_name=collection.name,
            pangenome_name=pangenome_name,
            only_latest_release=True,
            disable_progress_bar=not progress,
        )

        if len(matching_pangenomes) == 0:
            raise ValueError(
                f"No matching pangenome found for {pangenome_name} extracted from mash reference {mash_result.reference}"
            )

        print_pangenome_info(matching_pangenomes)

        if len(matching_pangenomes) > 1:
            logger.warning(
                f"{len(matching_pangenomes)} pangenomes found for {pangenome_name}. Using the first one."
            )

        pangenome = matching_pangenomes[0]

        pangenome_to_download.append(pangenome)

    if download:
        download_pangenomes(
            api_url=api_url,
            pangenomes=pangenome_to_download,
            outdir=outdir,
            disable_progress_bar=not progress,
        )
    else:
        logger.info("Download option is set to False. Skipping download.")


def get_pangenome_name_from_mash_reference(mash_reference: str) -> str:
    """Extract the pangenome name from the mash reference string."""
    # Assuming the mash reference is in the format "collection_id/pangenome_name[.fasta][.gz]"
    mash_ref_path = Path(mash_reference)
    if ".gz" in mash_ref_path.suffix:
        mash_ref_path = mash_ref_path.with_suffix("")
    if mash_ref_path.suffix in ["fna", ".fa", ".fasta"]:
        mash_ref_path = mash_ref_path.with_suffix("")

    return mash_ref_path.name
