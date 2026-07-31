<!-- Shared header — identical in all three repos. Keep in sync. -->
# AGENTS.md

Guidance for AI agents working in this repository or with the PanGBank resource.

## Read the agent skill first

**<https://raw.githubusercontent.com/labgem/PanGBank-api/main/skills/pangbank/SKILL.md>** documents the REST API and its filters, the query traps that silently return wrong results, how to download and analyse a pangenome with PPanGGOLiN, how to project a user's own genome, and the citation requirements. Several of its traps produce plausible but incorrect answers with no visible symptom, so read it before writing any PanGBank query.

Short web entry point: <https://pangbank.genoscope.cns.fr/llms.txt>

## Always true

- **Never scrape <https://pangbank.genoscope.cns.fr>.** Single-page app; the HTML carries no data, and dynamic routes return HTTP 404 server-side while rendering fine in a browser. Use <https://pangbank-api.genoscope.cns.fr>.
- **Pin the release** with `only_latest_release=true`, or filter client-side on `collection_release.version`. Without it results are summed across every release.
- **`taxon_name` needs the GTDB rank prefix** and is an exact match: `g__Escherichia` works, `Escherichia` returns nothing.
- **At most 1 HTTP request every 30 seconds**, across all routes, never parallelised across agents or threads. PanGBank runs on a shared Genoscope machine with no dedicated resources and no monitoring: an overload is invisible until the service goes down for everyone. Call `/pangenomes/count/` before any listing, filter server-side, use `limit=100`, and download a pangenome once rather than re-fetching it.

## Citation

Results derived from PanGBank must cite PanGBank and PPanGGOLiN, plus panRGP when RGPs or insertion spots are used, and panModule when conserved modules are used. Full references in the skill. Data are CC BY-SA 4.0 (attribution *and* share-alike); source is CeCILL v2.1.

## Specific to this repository

The CLI's flag semantics are **inverted relative to the raw API** in two places, and both silently change results:

- `search-pangenomes` defaults to *substring* taxon matching; `--exact-match` opts into exact. The API is the opposite.
- `--latest-only` defaults to **False**, so without `-l` you get every release. Use `-l` for "what is current" and `--release-version` for reproducible work — the latter is applied client-side, because the API parameter of that name does nothing.
- The TSV `name` column holds the deepest taxon name *with spaces*, while the API/SDK `name` field holds the *underscored* pangenome name. Joining on `name` fails silently; join on `pangenome_id`.

`match-pangenome` requires **Mash** on `PATH` (not pulled in by `pip install pangbank-cli`), handles one genome per invocation, and hardcodes `mash dist -p 1 -d 0.05`. It downloads the collection sketch on first use (16–38 MB) into `--outdir`, so the cache is per-outdir.

**Destructive behaviour to be aware of when editing `get_pangenome_file()`:** an existing file whose md5 differs from `file_md5sum` is treated as corrupt and `unlink()`ed *before* the replacement download is attempted. Since `ppanggolin metadata` rewrites a pangenome in place, a user who annotated their download and re-runs the same command loses that work — and loses it entirely if the download then fails. Do not make this worse; ideally download to a temporary name and swap on success.
