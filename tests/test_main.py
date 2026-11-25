"""Offline unit tests: none of these reach the PanGBank API."""

from pathlib import Path

import pytest
import typer
from pangbank_api.models import TaxonPublic
from typer.testing import CliRunner

from pangbank_cli import __version__, match_pangenome
from pangbank_cli.main import app, check_deprecated_latest_only
from pangbank_cli.match_pangenome import (
    compute_mash_distance,
)
from pangbank_cli.pangenomes import get_common_taxonomy, version_sort_key

runner = CliRunner()


def test_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


@pytest.mark.parametrize(
    "command",
    ["list-collections", "search-pangenomes", "get-pangenome", "match-pangenome"],
)
def test_command_help(command: str) -> None:
    result = runner.invoke(app, [command, "--help"])
    assert result.exit_code == 0


def test_latest_only_conflicts_with_all_releases() -> None:
    with pytest.raises(typer.BadParameter):
        check_deprecated_latest_only(latest_only=True, all_releases=True)


def test_version_sort_key_is_numeric() -> None:
    versions = ["10.0.0", "2.0.0", "2.0.0-beta", "1.1.0"]
    assert sorted(versions, key=version_sort_key) == [
        "1.1.0",
        "2.0.0",
        "2.0.0-beta",
        "10.0.0",
    ]


def _taxon(name: str, depth: int) -> TaxonPublic:
    return TaxonPublic(id=depth, name=name, rank=str(depth), depth=depth)


def test_common_taxonomy_stops_at_first_divergence() -> None:
    bacteria, proteo = _taxon("d__Bacteria", 0), _taxon("p__Proteobacteria", 1)
    lineages = [
        [proteo, bacteria, _taxon("c__Gamma", 2)],  # unsorted on purpose
        [bacteria, proteo, _taxon("c__Alpha", 2)],
    ]
    assert get_common_taxonomy(lineages) == [bacteria, proteo]


def test_compute_mash_distance_keeps_best_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    mash_output = (
        "ref/A.fna\tquery.fna\t0.03\t0\t500/1000\n"
        "ref/B.fna\tquery.fna\t0.01\t0\t800/1000\n"
        "ref/C.fna\tquery.fna\t0.04\t0\t400/1000\n"
    )

    def fake_launch_mash_dist(**_: object) -> str:
        return mash_output

    monkeypatch.setattr(match_pangenome, "launch_mash_dist", fake_launch_mash_dist)

    best = compute_mash_distance(Path("sketch.msh"), [Path("query.fna")])
    assert best is not None
    assert best["query.fna"].reference == "ref/B.fna"


def test_compute_mash_distance_no_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_launch_mash_dist(**_: object) -> str:
        return ""

    monkeypatch.setattr(match_pangenome, "launch_mash_dist", fake_launch_mash_dist)

    assert compute_mash_distance(Path("sketch.msh"), [Path("query.fna")]) is None
