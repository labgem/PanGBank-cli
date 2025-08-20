# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-08-20

### Added

- **Search pangenomes by taxon, genome, or collection**: Query PanGBank API to find relevant pangenomes matching specific criteria.
- **Retrieve pangenome metrics**: Access information on pangenomes, including taxonomy, number of genomes, gene counts, and other statistics.
- **Download pangenome files**: Fetch pangenome files directly from PanGBank for downstream analysis with PPanGGOLiN.
- **Match an input genome to a pangenome**: Identify the most similar pangenome to a given genome using mash sketches of the selected collection.
