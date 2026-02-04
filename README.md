[![PyPI version](https://badge.fury.io/py/pangbank-cli.svg?cache-control=no-cache)](https://pypi.org/project/pangbank-cli/) [![install with bioconda](https://img.shields.io/badge/install%20with-bioconda-brightgreen.svg?style=flat)](http://bioconda.github.io/recipes/pangbank-cli/README.html) [![Anaconda-Server Badge](https://anaconda.org/bioconda/pangbank-cli/badges/version.svg)](https://anaconda.org/bioconda/pangbank-cli) [![Anaconda-Server Badge](https://anaconda.org/bioconda/pangbank-cli/badges/license.svg)](https://anaconda.org/bioconda/pangbank-cli)


# PanGBank-cli

**PanGBank-cli** is a command-line interface to **search, retrieve, and download pangenomes** from [PanGBank](https://pangbank.genoscope.cns.fr/) via the [PanGBank REST API](https://pangbank-api.genoscope.cns.fr/).
It acts as a convenient wrapper around the API, making PanGBank data easily accessible directly from the terminal.

[PanGBank](https://pangbank.genoscope.cns.fr/) is a large-scale resource that hosts collections of microbial **pangenomes** constructed from diverse genome sources using [PPanGGOLiN](https://github.com/labgem/PPanGGOLiN).

With **PanGBank-cli** you can:

* Search pangenomes by **taxon**, **genome**, or **collection**
* Retrieve detailed metrics for selected pangenomes
* Download pangenome files for downstream analyses
* Map an input genome to its corresponding pangenome in PanGBank and fetch it automatically

For interactive exploration, you can also browse PanGBank collections through the web application:
**PanGBank Web**: https://pangbank.genoscope.cns.fr/


## Installation

### Option 1: Install from Bioconda

The easiest way to install PanGBank-cli with all dependencies (including Mash):

```bash
conda create -n pangbank-cli pangbank-cli
conda activate pangbank-cli
```

### Option 2: Install from PyPI

Install using pip:

```bash
pip install PanGBank-cli
```

> \[!WARNING]
> Installing **PanGBank-cli** with pip will only set up the Python dependencies. The external tool [**Mash**](https://github.com/marbl/Mash) (required for the `match-pangenome` command) is **not** included and must be installed separately to enable full functionality.

### Option 3: Install from source using `conda`

```bash
# Create a new conda environment with Python
conda create -n pangbank-cli python=3.12 mash=2.3

# Activate the environment
conda activate pangbank-cli

# Clone the repository
git clone https://github.com/labgem/PanGBank-cli.git
cd PanGBank-cli

# Install PanGBank-cli
pip install .
```

### Option 4: Install from source with `pip`

```bash
# Clone the repository
git clone https://github.com/labgem/PanGBank-cli.git
cd PanGBank-cli

# create and activate a virtual environment:
python -m venv venv

# Activate the virtual environment
# On Linux/macOS:
source venv/bin/activate

# Install PanGBank-cli
pip install .
```

> \[!WARNING]
> Installing **PanGBank-cli** from source with pip will only set up the Python dependencies. The external tool [**Mash**](https://github.com/marbl/Mash) (required for the `match-pangenome` command) is **not** included and must be installed separately to enable full functionality.


## Usage

Once installed, you can access the CLI by running:

```bash
pangbank --help
```

This will display the list of available commands and options.

![`pangbank --help`](docs/img/pangbank-help.svg)

Each command has a dedicated help section. For example:

```bash
pangbank search-pangenomes --help
```

![`pangbank search-pangenomes --help`](docs/img/pangbank-search-pangenomes_help.svg)


### List available collections

```bash
pangbank list-collections
```

Displays the list all pangenome collections available in PanGBank, along with their description and the number of pangenomes they contain.

Output is formatted as a rich table in the terminal, or as plain TSV when redirected (e.g., `pangbank list-collections > collections.tsv`).

<!-- RICH-CODEX hide_command: true -->
![`TERMINAL_WIDTH=110 pangbank list-collections`](docs/img/pangbank-list-collections.svg)

### Search for pangenomes

```bash
pangbank search-pangenomes --taxon "g__Escherichia"
```

Searches PanGBank for pangenomes matching the given taxon.
Results are printed to **stdout** as plain TSV by default (suitable for piping or redirection). Use `--table-path <file>` to save directly to a file (e.g., `--table-path pangenomes_information.tsv`), or `--no-table` to disable table output.


![`pangbank search-pangenomes --taxon "g__Escherichia" --no-progress --table-path pangenome_information.tsv`](docs/img/pangbank-search-pangenomes_taxon_Escherichia.svg)

### Download pangenomes

```bash
pangbank search-pangenomes --taxon "g__Chlamydia" \
    --collection GTDB_refseq \
    --outdir Chlamydia_pangenomes/ \
    --download
```

Searches for **Chlamydia** pangenomes in the `GTDB_refseq` collection, then downloads the corresponding pangenome files into `Chlamydia_pangenomes/`.

![`pangbank search-pangenomes --taxon "g__Chlamydia" --collection GTDB_refseq --outdir Chlamydia_pangenomes/ --download --no-progress`](docs/img/pangbank-search-pangenomes_taxon_Chlamydia_download.svg)

### Match a genome to an existing pangenome

```bash
pangbank match-pangenome --input-genome <genome.fasta> --collection GTDB_all
```

Matches the given input genome (FASTA format) to the most similar pangenome in the selected collection using [**Mash**](https://github.com/marbl/Mash) and a precomputed sketch of the collection to identify the closest pangenome.
The command outputs detailed information about the best matching pangenome.


> \[!NOTE]
> * Add the `--download` flag to download the corresponding pangenome file.
> * The downloaded file can then be used with **PPanGGOLiN’s** `projection` command to annotate the input genome.
  See the [PPanGGOLiN documentation](https://ppanggolin.readthedocs.io/en/latest/user/projection.html) for details.


# Citation

PanGBank pangenomes are constructed with PPanGGOLiN and its companion tools. If you use PanGBank or PanGBank-cli in your research, please cite the following references:


> **PPanGGOLiN: Depicting microbial diversity via a partitioned pangenome graph**
> Gautreau G et al. (2020)
> *PLOS Computational Biology 16(3): e1007732.*
> doi: [10.1371/journal.pcbi.1007732](https://doi.org/10.1371/journal.pcbi.1007732)


> **panRGP: a pangenome-based method to predict genomic islands and explore their diversity**
> Bazin et al. (2020)
> *Bioinformatics, Volume 36, Issue Supplement_2, Pages i651–i658*
> doi: [10.1093/bioinformatics/btaa792](https://doi.org/10.1093/bioinformatics/btaa792)


> **panModule: detecting conserved modules in the variable regions of a pangenome graph**
> Bazin et al. (2021)
> *bioRxiv* 
> doi: [10.1101/2021.12.06.471380](https://doi.org/10.1101/2021.12.06.471380)