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
👉 **PanGBank Web**: https://pangbank.genoscope.cns.fr/


## Installation


### Option 1: Install using `conda`


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

### Option 2: Install with `pip`


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
> Installing **PanGBank-cli** with this method will only set up the Python dependencies. The external tool [**Mash**](https://github.com/marbl/Mash) (required for the `match-pangenome` command) is **not** included and must be installed separately to enable full functionality.

## Usage

After installation, you can run the CLI using:

```bash
pangbank --help
```


### Example: List collections of pangenomes

```bash
pangbank list-collections
```

### Example: Search for pangenomes

```bash
pangbank search-pangenomes --taxon "g__Escherichia"
```
### Example: Search for pangenomes and print some metrics

```bash
pangbank search-pangenomes --taxon "diabolicus" --details
```

### Example: Download pangenomes

```bash
pangbank search-pangenomes --taxon "Streptococcus" --download --outdir strepto_pangenomes/
```

### Example: Map input genome with a corresponding pangenome 

```bash
pangbank match-pangenome --input_genome <input genome in FASTA format> --collection GTDB_all
```


# Licence

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