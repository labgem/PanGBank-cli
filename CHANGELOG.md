# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

### Added

- Mash sketch files are now validated using MD5 checksum to ensure integrity
- Added `--table-path` option to save TSV output to a file
- Added `--no-table` flag to disable table output completely

### Changed

- Table output now defaults to stdout instead of a file (previous default was `pangenomes_information.tsv`)
- Renamed `--table` option to `--table-path` for clarity

## [0.1.1] - 2025-11-09

### Added

- Added `--table` option to search-pangenomes for exporting results as a TSV table
- Added a workflow to publish the package to PyPI in P

### Changed

- Change the match-pangenome command option `--input_genome` by `--input-genome`
- Updated dependencies: `pangbank-api` is now referenced from PyPI instead of a GitHub link in PR 

## [0.1.0] - 2025-08-20

### Added

- **Search pangenomes by taxon, genome, or collection**: Query PanGBank API to find relevant pangenomes matching specific criteria.
- **Retrieve pangenome metrics**: Access information on pangenomes, including taxonomy, number of genomes, gene counts, and other statistics.
- **Download pangenome files**: Fetch pangenome files directly from PanGBank for downstream analysis with PPanGGOLiN.
- **Match an input genome to a pangenome**: Identify the most similar pangenome to a given genome using mash sketches of the selected collection.
