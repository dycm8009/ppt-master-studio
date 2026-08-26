# PPT Master Studio v3.2.0 — Regression Policy

The Studio must not regress into repeated card grids, >2 consecutive identical compositions, image-as-diversity behavior, dark-tech raster backgrounds, blanket long-deck `-a auto`, or unreviewed export.

Static UI regressions are blocking when they: fabricate official receipts; lose digest binding; skip Stage 1/2 user confirmation; omit Deck Review before QA; require Motion Review on a static deck; reduce Stage 2 to prose+swatches; omit fixed icon samples; conflate Mode with Visual Style; silently rewrite `image_notes`; or allow `image_usage:none` with another source.

Portable Recovery regressions are blocking when they: skip recovery after host reset; reconstruct missing evidence from chat; omit planning/reviewed/final snapshots; fail to hash files; accept path traversal/checksum drift; or treat Deck Review HTML as complete recovery.

GitHub-first regressions are blocking when they: omit project commit pinning; silently upgrade an in-progress project; allow runtime commit mismatch; let uploaded ZIP authority override the GitHub pin; or place Studio policy changes directly on upstream-mirror `main`.
