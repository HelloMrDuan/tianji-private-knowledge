# Tianji Private Knowledge

**Restricted knowledge-data repository.** All 11 data areas were imported from
`HelloMrDuan/tianji-knowledge-base` at pinned public commit
`da3aef06ad03a02c94770689f7cc1510b0d4593e`.

- 235 versioned data files, 13,518,179 bytes.
- `private-data-manifest.json` records file-level SHA256 and source provenance.
- `data/` contains Canonical, Quarantine, indices, product knowledge, upstream
  sources, provenance, research, state and registry files.
- `.github/workflows/import-public-knowledge.yml` is pinned to the original
  snapshot. It does not continuously import moving public source branches.
- `.github/workflows/private-knowledge-validation.yml` validates isolated
  private backend assembly and runs the real knowledge and Python regression
  suite in PRIVATE Actions; consult the latest run result before declaring
  production readiness.

Do not mirror this repository, its manifests or Actions artifacts into public
frontends, public repositories, public logs or unprotected object stores. Review
third-party licensing and provenance before redistributing content.

**Historical warning:** making this destination private does not retract files
previously published in the public repository or its Git history. Public-data
removal and deployment cutover require separate verification.
