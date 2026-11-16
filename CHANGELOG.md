# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

### Added

- `search-pangenomes` now logs a summary of the matching pangenomes, grouped by collection release (up to 10 pangenomes listed per release)
- `CITATION.cff` file, so GitHub shows a "Cite this repository" button pointing to the PanGBank article in Nucleic Acids Research ([#21](https://github.com/labgem/PanGBank-cli/pull/21))


### Changed

- **Breaking:** `search-pangenomes` no longer prints the TSV table to stdout by default. Use `--table` to print it or `--table-path <file>` to save it to a file
- **Breaking:** `search-pangenomes` and `list-collections` now show only the latest release of each collection by default. Use the new `--all-releases`/`-a` flag to include every release. `--release-version` still selects a specific release
- Collection releases are now sorted by version number (e.g. `2.0.0` before `10.0.0`) in the search summary and in `--details` output
- Log messages no longer show the source file and line unless `--verbose` is set
- README: updated the citation to the published PanGBank article and clarified how to use the downloaded pangenome HDF5 files ([#20](https://github.com/labgem/PanGBank-cli/pull/20), [#21](https://github.com/labgem/PanGBank-cli/pull/21))

### Deprecated

- `--latest-only`/`-l` on `search-pangenomes` and `list-collections` is deprecated and has no effect, since the latest release is now the default. It is hidden from `--help`, logs a warning when used, and will be removed in 0.5.


## [0.3.0] - 2026-08-06

### Added

- AI agent documentation (`AGENTS.md`) to help automated tools use PanGBank-cli correctly ([#14](https://github.com/labgem/PanGBank-cli/pull/14))

### Changed

- API calls now go through the official PanGBank SDK, including `--release-version` filtering ([#16](https://github.com/labgem/PanGBank-cli/pull/16))
- Safer pangenome downloads: files are written to a temporary file before replacing an existing one, which prevents data loss when re-downloading modified pangenome files ([#17](https://github.com/labgem/PanGBank-cli/pull/17))
- Improved download progress reporting ([#13](https://github.com/labgem/PanGBank-cli/pull/13))
- Pangenome table generation now reuses the API formatting code ([#15](https://github.com/labgem/PanGBank-cli/pull/15))

## [0.2.0] - 2026-06-19

### Added

- `get-pangenome` command to retrieve a pangenome by its ID ([#10](https://github.com/labgem/PanGBank-cli/pull/10))
- Support for collections with multiple releases ([#11](https://github.com/labgem/PanGBank-cli/pull/11)):
  - `--latest-only` option in `search-pangenomes` to search only the latest release of each collection
  - `--release-version` option to filter pangenomes by a specific collection release version (e.g. `1.0.0`)
- MD5 checksum verification for downloaded Mash sketch files ([#8](https://github.com/labgem/PanGBank-cli/pull/8))
- `--table-path` option in `search-pangenomes` to save the TSV table to a file
- `list-collections` detects terminal vs redirected output: formatted table in an interactive terminal, plain TSV when redirected to a file or pipe

### Changed

- `search-pangenomes` now prints the TSV table to stdout by default instead of writing `pangenomes_information.tsv`; use `--no-table` to disable it ([#9](https://github.com/labgem/PanGBank-cli/pull/9))

## [0.1.1] - 2025-11-19

### Added

- `--table` option in `search-pangenomes` to export results as a TSV table
- Workflow to publish the package to PyPI ([#3](https://github.com/labgem/PanGBank-cli/pull/3))

### Changed

- `match-pangenome` option `--input_genome` renamed to `--input-genome`
- `pangbank-api` dependency is now installed from PyPI instead of a GitHub link ([#2](https://github.com/labgem/PanGBank-cli/pull/2))

## [0.1.0] - 2025-08-20

First release of PanGBank-cli, a command-line tool to search, retrieve and download pangenomes from the PanGBank API.

### Added

- **Search pangenomes by taxon, genome or collection**: query the PanGBank API to find pangenomes matching specific criteria.
- **Retrieve pangenome metrics**: access information on pangenomes, including taxonomy, number of genomes, gene counts and other statistics.
- **Download pangenome files**: fetch pangenome files directly from PanGBank for downstream analysis with PPanGGOLiN.
- **Match an input genome to a pangenome**: identify the most similar pangenome to a given genome using Mash sketches of the selected collection.

[Unreleased]: https://github.com/labgem/PanGBank-cli/compare/0.3.0...HEAD
[0.3.0]: https://github.com/labgem/PanGBank-cli/compare/0.2.0...0.3.0
[0.2.0]: https://github.com/labgem/PanGBank-cli/compare/0.1.1...0.2.0
[0.1.1]: https://github.com/labgem/PanGBank-cli/compare/0.1.0...0.1.1
[0.1.0]: https://github.com/labgem/PanGBank-cli/releases/tag/0.1.0
