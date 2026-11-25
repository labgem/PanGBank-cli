import pytest

from pangbank_cli.match_pangenome import get_pangenome_name_from_mash_reference


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        ("collection/s__Escherichia_coli.fna", "s__Escherichia_coli"),
        ("collection/s__Escherichia_coli.fna.gz", "s__Escherichia_coli"),
        ("collection/s__Escherichia_coli.fasta", "s__Escherichia_coli"),
        ("collection/s__Escherichia_coli.fa.gz", "s__Escherichia_coli"),
        ("s__Escherichia_coli", "s__Escherichia_coli"),
    ],
)
def test_pangenome_name_from_mash_reference(reference: str, expected: str) -> None:
    assert get_pangenome_name_from_mash_reference(reference) == expected
