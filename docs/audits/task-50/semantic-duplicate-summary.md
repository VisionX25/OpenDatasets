# OpenDatasets Cross-Dataset Semantic Duplicate Audit Summary

> **Audit Task:** Task 50 — Cross-Dataset Semantic Duplicate Detection and 1,000-Dataset Readiness<br>
> **Audit Date:** 2026-11-21<br>
> **Total Records Scanned:** 700<br>
> **Total Candidate Pairs Flagged:** 118<br>
> **Confidence Breakdown:** High: **0**, Medium: **84**, Low: **34**<br>
> **Methodology:** Offline, evidence-based pairwise semantic similarity inspection across 7 detection dimensions.

---

## Executive Summary

This audit performs a systematic, reproducible semantic duplicate inspection across all **700** dataset records in the OpenDatasets catalog. It analyzes exact identifiers, normalized titles, acronyms, canonical URLs, citation DOIs, repository endpoints, and multi-attribute metadata alignments.

### Key Audit Findings
- **Zero High-Confidence Duplicate Flags (0):** Algorithmic screening identified zero exact duplicate records, identical copy-paste dataset definitions, or unverified duplicate registrations in the catalog. Note that zero algorithmic flags does not guarantee the complete absence of subtle semantic overlap across all domains; ongoing manual curation remains essential.
- **Medium-Confidence Candidate Pairs (84):** Represent legitimate multi-track benchmark suites (e.g., Argoverse 2, Waymo Open), classic split variants (CIFAR-10 vs CIFAR-100), chronological annual challenge iterations (ISIC 2018 vs 2019, Plant Pathology 2020 vs 2021), and major version evolutions (KolektorSDD vs KolektorSDD2, MIMIC-III vs MIMIC-IV).
- **Low-Confidence Overlaps (34):** Represent shared foundational research publications, shared institutional portals (SpaceNet, NOAA), or coincidental lexical task phrasing across independent organizations.
- **Preservation of Scientific Lineage:** Subsets, variants, and chronological versions are preserved as distinct records with cross-referencing rather than destructive merging or automatic deletion.

---

## 1. Candidate Pairs Distribution by Confidence Tier

| Confidence Tier | Candidate Pairs | Catalog Interpretation | Recommended Maintainer Policy |
| :--- | :---: | :--- | :--- |
| **High Confidence** | **0** | Strong evidence of identical duplicate dataset | Deprecate or merge redundant record |
| **Medium Confidence** | **84** | Valid benchmark subsets, versions, or shared suite landing pages | Maintain separate records; document lineage & cross-references |
| **Low Confidence** | **34** | Shared foundational paper or coincidental phrasing | No action required; independent benchmarks |
| **Total Evaluated** | **118** | Evaluated across all 244,650 exhaustive pairwise comparisons (700 × 699 / 2) | Deterministic review complete |

---

## 2. High-Confidence Candidate Pairs

**No high-confidence duplicate pairs detected.**

Algorithmic screening identified zero candidate pairs meeting high-confidence duplicate thresholds across all 700 dataset records.

---

## 3. Medium-Confidence Candidate Pairs (Maintainer Review Candidates)

Medium-confidence candidate pairs require manual review to establish scientific distinctness. Pairs in this tier share significant title, URL, repository, or citation tokens, and typically represent valid benchmark suites, multi-modal task tracks, parent project landing pages, or chronological releases, but require individual verification against primary publisher documentation before making any metadata adjustments.

| Pair ID | Dataset A | Dataset B | Shared Signal | Distinguishing Factors | Potential False-Positive Reason | Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `argoverse-2-lidar__argoverse-2-motion-forecasting` | `argoverse-2-lidar` | `argoverse-2-motion-forecasting` | Homepage: `argoverse.org/av2.html`; Shared refs (1) | `lidar, motion` | `distinct_benchmark_subsets_under_shared_project_umbrella` | `maintain_as_distinct_with_cross_reference` |
| `argoverse-2-lidar__argoverse-2-sensor` | `argoverse-2-lidar` | `argoverse-2-sensor` | Homepage: `argoverse.org/av2.html`; Shared refs (1) | `lidar, sensor` | `distinct_benchmark_subsets_under_shared_project_umbrella` | `maintain_as_distinct_with_cross_reference` |
| `argoverse-2-motion-forecasting__argoverse-2-sensor` | `argoverse-2-motion-forecasting` | `argoverse-2-sensor` | Homepage: `argoverse.org/av2.html`; Shared refs (1) | `motion, sensor` | `distinct_benchmark_subsets_under_shared_project_umbrella` | `maintain_as_distinct_with_cross_reference` |
| `camelyon16__camelyon17` | `camelyon16` | `camelyon17` | Shared refs (2) | `2016` | `shared_challenge_or_platform_repository` | `maintain_as_distinct_with_cross_reference` |
| `cic-ids2017__cse-cic-ids2018` | `cic-ids2017` | `cse-cic-ids2018` | DOI: `10.5220/0006639801080116`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `cifar-10__cifar-100` | `cifar-10` | `cifar-100` | Homepage: `cs.toronto.edu/~kriz/cifar.html`; Shared refs (2) | `10, 100` | `distinct_benchmark_subsets_under_shared_project_umbrella` | `maintain_as_distinct_with_cross_reference` |
| `esa-worldcereal-global-maps__worldcereal-reference-data` | `esa-worldcereal-global-maps` | `worldcereal-reference-data` | DOI: `10.5194/essd-15-5491-2023`; Shared refs (1) | `reference` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `isic-2018__isic-2019` | `isic-2018` | `isic-2019` | Fuzzy Title (0.98) | `2018, 2019` | `chronological_challenge_or_version_evolution` | `verify_version_deprecation` |
| `kleister-charity__kleister-nda` | `kleister-charity` | `kleister-nda` | DOI: `10.1007/978-3-030-86540-5_37`; Shared refs (1) | `charity, nda` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `kolektorsdd__kolektorsdd2` | `kolektorsdd` | `kolektorsdd2` | Fuzzy Title (0.97) | `2` | `related_benchmark_family_from_same_publisher` | `maintain_as_distinct_with_cross_reference` |
| `mag240m__pcqm4mv2` | `mag240m` | `pcqm4mv2` | DOI: `10.48550/arxiv.2103.09430`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `mag240m__wikikg90mv2` | `mag240m` | `wikikg90mv2` | DOI: `10.48550/arxiv.2103.09430`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `mimic-iii__mimic-iv` | `mimic-iii` | `mimic-iv` | Fuzzy Title (0.94) | `iii, iv` | `related_benchmark_family_from_same_publisher` | `maintain_as_distinct_with_cross_reference` |
| `mvtec-3d-ad__mvtec-ad` | `mvtec-3d-ad` | `mvtec-ad` | Fuzzy Title (0.94) | `3d` | `related_benchmark_family_from_same_publisher` | `maintain_as_distinct_with_cross_reference` |
| `noaa-ghcn-hourly__noaa-ghcn-monthly` | `noaa-ghcn-hourly` | `noaa-ghcn-monthly` | Fuzzy Title (0.91) | `1, 4, hourly` | `related_benchmark_family_from_same_publisher` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-code2__ogbg-molpcba` | `ogbg-code2` | `ogbg-molpcba` | Homepage: `ogb.stanford.edu/docs/graphprop`; DOI: `10.48550/arxiv.2005.00687`; Shared refs (2) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-code2__ogbg-moltox21` | `ogbg-code2` | `ogbg-moltox21` | Homepage: `ogb.stanford.edu/docs/graphprop`; DOI: `10.48550/arxiv.2005.00687`; Shared refs (2) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-code2__ogbg-ppa` | `ogbg-code2` | `ogbg-ppa` | Homepage: `ogb.stanford.edu/docs/graphprop`; DOI: `10.48550/arxiv.2005.00687`; Shared refs (2) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-code2__ogbl-citation2` | `ogbg-code2` | `ogbl-citation2` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-code2__ogbl-collab` | `ogbg-code2` | `ogbl-collab` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-code2__ogbl-ppa` | `ogbg-code2` | `ogbl-ppa` | DOI: `10.48550/arxiv.2005.00687`; Repo: `github:snap-stanford/ogb`; Shared refs (2) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-code2__ogbl-wikikg2` | `ogbg-code2` | `ogbl-wikikg2` | DOI: `10.48550/arxiv.2005.00687`; Repo: `github:snap-stanford/ogb`; Shared refs (2) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-code2__ogbn-mag` | `ogbg-code2` | `ogbn-mag` | DOI: `10.48550/arxiv.2005.00687`; Repo: `github:snap-stanford/ogb`; Shared refs (2) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-code2__ogbn-papers100m` | `ogbg-code2` | `ogbn-papers100m` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-code2__ogbn-products` | `ogbg-code2` | `ogbn-products` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-code2__ogbn-proteins` | `ogbg-code2` | `ogbn-proteins` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-molpcba__ogbg-moltox21` | `ogbg-molpcba` | `ogbg-moltox21` | Homepage: `ogb.stanford.edu/docs/graphprop`; DOI: `10.48550/arxiv.2005.00687`; Shared refs (2) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-molpcba__ogbg-ppa` | `ogbg-molpcba` | `ogbg-ppa` | Homepage: `ogb.stanford.edu/docs/graphprop`; DOI: `10.48550/arxiv.2005.00687`; Shared refs (2) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-molpcba__ogbl-citation2` | `ogbg-molpcba` | `ogbl-citation2` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-molpcba__ogbl-collab` | `ogbg-molpcba` | `ogbl-collab` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-molpcba__ogbl-ppa` | `ogbg-molpcba` | `ogbl-ppa` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-molpcba__ogbl-wikikg2` | `ogbg-molpcba` | `ogbl-wikikg2` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-molpcba__ogbn-mag` | `ogbg-molpcba` | `ogbn-mag` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-molpcba__ogbn-papers100m` | `ogbg-molpcba` | `ogbn-papers100m` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-molpcba__ogbn-products` | `ogbg-molpcba` | `ogbn-products` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-molpcba__ogbn-proteins` | `ogbg-molpcba` | `ogbn-proteins` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-moltox21__ogbg-ppa` | `ogbg-moltox21` | `ogbg-ppa` | Homepage: `ogb.stanford.edu/docs/graphprop`; DOI: `10.48550/arxiv.2005.00687`; Shared refs (2) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-moltox21__ogbl-citation2` | `ogbg-moltox21` | `ogbl-citation2` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-moltox21__ogbl-collab` | `ogbg-moltox21` | `ogbl-collab` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-moltox21__ogbl-ppa` | `ogbg-moltox21` | `ogbl-ppa` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-moltox21__ogbl-wikikg2` | `ogbg-moltox21` | `ogbl-wikikg2` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-moltox21__ogbn-mag` | `ogbg-moltox21` | `ogbn-mag` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-moltox21__ogbn-papers100m` | `ogbg-moltox21` | `ogbn-papers100m` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-moltox21__ogbn-products` | `ogbg-moltox21` | `ogbn-products` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-moltox21__ogbn-proteins` | `ogbg-moltox21` | `ogbn-proteins` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-ppa__ogbl-citation2` | `ogbg-ppa` | `ogbl-citation2` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-ppa__ogbl-collab` | `ogbg-ppa` | `ogbl-collab` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-ppa__ogbl-ppa` | `ogbg-ppa` | `ogbl-ppa` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-ppa__ogbl-wikikg2` | `ogbg-ppa` | `ogbl-wikikg2` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-ppa__ogbn-mag` | `ogbg-ppa` | `ogbn-mag` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-ppa__ogbn-papers100m` | `ogbg-ppa` | `ogbn-papers100m` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-ppa__ogbn-products` | `ogbg-ppa` | `ogbn-products` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbg-ppa__ogbn-proteins` | `ogbg-ppa` | `ogbn-proteins` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbl-citation2__ogbl-collab` | `ogbl-citation2` | `ogbl-collab` | Homepage: `ogb.stanford.edu/docs/linkprop`; DOI: `10.48550/arxiv.2005.00687`; Shared refs (2) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbl-citation2__ogbl-ppa` | `ogbl-citation2` | `ogbl-ppa` | Homepage: `ogb.stanford.edu/docs/linkprop`; DOI: `10.48550/arxiv.2005.00687`; Shared refs (2) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbl-citation2__ogbl-wikikg2` | `ogbl-citation2` | `ogbl-wikikg2` | Homepage: `ogb.stanford.edu/docs/linkprop`; DOI: `10.48550/arxiv.2005.00687`; Shared refs (2) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbl-citation2__ogbn-mag` | `ogbl-citation2` | `ogbn-mag` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbl-citation2__ogbn-papers100m` | `ogbl-citation2` | `ogbn-papers100m` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbl-citation2__ogbn-products` | `ogbl-citation2` | `ogbn-products` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbl-citation2__ogbn-proteins` | `ogbl-citation2` | `ogbn-proteins` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbl-collab__ogbl-ppa` | `ogbl-collab` | `ogbl-ppa` | Homepage: `ogb.stanford.edu/docs/linkprop`; DOI: `10.48550/arxiv.2005.00687`; Shared refs (2) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbl-collab__ogbl-wikikg2` | `ogbl-collab` | `ogbl-wikikg2` | Homepage: `ogb.stanford.edu/docs/linkprop`; DOI: `10.48550/arxiv.2005.00687`; Shared refs (2) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbl-collab__ogbn-mag` | `ogbl-collab` | `ogbn-mag` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbl-collab__ogbn-papers100m` | `ogbl-collab` | `ogbn-papers100m` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbl-collab__ogbn-products` | `ogbl-collab` | `ogbn-products` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbl-collab__ogbn-proteins` | `ogbl-collab` | `ogbn-proteins` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbl-ppa__ogbl-wikikg2` | `ogbl-ppa` | `ogbl-wikikg2` | Homepage: `ogb.stanford.edu/docs/linkprop`; DOI: `10.48550/arxiv.2005.00687`; Repo: `github:snap-stanford/ogb`; Shared refs (3) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbl-ppa__ogbn-mag` | `ogbl-ppa` | `ogbn-mag` | DOI: `10.48550/arxiv.2005.00687`; Repo: `github:snap-stanford/ogb`; Shared refs (2) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbl-ppa__ogbn-papers100m` | `ogbl-ppa` | `ogbn-papers100m` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbl-ppa__ogbn-products` | `ogbl-ppa` | `ogbn-products` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbl-ppa__ogbn-proteins` | `ogbl-ppa` | `ogbn-proteins` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbl-wikikg2__ogbn-mag` | `ogbl-wikikg2` | `ogbn-mag` | DOI: `10.48550/arxiv.2005.00687`; Repo: `github:snap-stanford/ogb`; Shared refs (2) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbl-wikikg2__ogbn-papers100m` | `ogbl-wikikg2` | `ogbn-papers100m` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbl-wikikg2__ogbn-products` | `ogbl-wikikg2` | `ogbn-products` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbl-wikikg2__ogbn-proteins` | `ogbl-wikikg2` | `ogbn-proteins` | DOI: `10.48550/arxiv.2005.00687`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbn-mag__ogbn-papers100m` | `ogbn-mag` | `ogbn-papers100m` | Homepage: `ogb.stanford.edu/docs/nodeprop`; DOI: `10.48550/arxiv.2005.00687`; Shared refs (2) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbn-mag__ogbn-products` | `ogbn-mag` | `ogbn-products` | Homepage: `ogb.stanford.edu/docs/nodeprop`; DOI: `10.48550/arxiv.2005.00687`; Shared refs (2) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbn-mag__ogbn-proteins` | `ogbn-mag` | `ogbn-proteins` | Homepage: `ogb.stanford.edu/docs/nodeprop`; DOI: `10.48550/arxiv.2005.00687`; Shared refs (2) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbn-papers100m__ogbn-products` | `ogbn-papers100m` | `ogbn-products` | Homepage: `ogb.stanford.edu/docs/nodeprop`; DOI: `10.48550/arxiv.2005.00687`; Shared refs (2) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbn-papers100m__ogbn-proteins` | `ogbn-papers100m` | `ogbn-proteins` | Homepage: `ogb.stanford.edu/docs/nodeprop`; DOI: `10.48550/arxiv.2005.00687`; Shared refs (2) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `ogbn-products__ogbn-proteins` | `ogbn-products` | `ogbn-proteins` | Homepage: `ogb.stanford.edu/docs/nodeprop`; DOI: `10.48550/arxiv.2005.00687`; Shared refs (2) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `pcqm4mv2__wikikg90mv2` | `pcqm4mv2` | `wikikg90mv2` | DOI: `10.48550/arxiv.2103.09430`; Shared refs (1) | `None identified` | `shared_foundational_or_benchmark_suite_publication` | `maintain_as_distinct_with_cross_reference` |
| `pku-market-pcb__pku-market-phone` | `pku-market-pcb` | `pku-market-phone` | Homepage: `robotics.pkusz.edu.cn/resources/datasetENG`; Shared refs (1) | `pcb, phone` | `distinct_benchmark_subsets_under_shared_project_umbrella` | `maintain_as_distinct_with_cross_reference` |
| `waymo-open-end-to-end__waymo-open-perception` | `waymo-open-end-to-end` | `waymo-open-perception` | Homepage: `waymo.com/open`; Shared refs (1) | `perception` | `distinct_benchmark_subsets_under_shared_project_umbrella` | `maintain_as_distinct_with_cross_reference` |

---

## 4. Low-Confidence Candidate Pairs

Low-confidence candidate pairs exhibit superficial or incidental overlaps (e.g. shared foundational citations, common challenge hosting platforms, or shared vocabulary across independent organizations). No database action is required.

| Pair ID | Dataset A | Dataset B | Overlap Category | Maintainer Rationale |
| :--- | :--- | :--- | :--- | :--- |
| `a2d2-audi-autonomous-driving__boreas` | `a2d2-audi-autonomous-driving` | `boreas` | `cross_institution_lexical_similarity` | Coincidental lexical phrasing across independent research institutions (e.g. shared generic task words). |
| `bigearthnet__reben-bigearthnet-v2` | `bigearthnet` | `reben-bigearthnet-v2` | `shared_umbrella_portal_or_challenge_repository` | Shared source documentation or challenge download link without title collision. |
| `bike-sharing__seoul-bike-sharing-demand` | `bike-sharing` | `seoul-bike-sharing-demand` | `shared_institutional_catalog_family` | Shared institutional publisher with moderate title or modality overlap. |
| `brats__polypgen` | `brats` | `polypgen` | `shared_umbrella_portal_or_challenge_repository` | Shared source documentation or challenge download link without title collision. |
| `btad-beantech-anomaly-detection__mvtec-ad` | `btad-beantech-anomaly-detection` | `mvtec-ad` | `cross_institution_lexical_similarity` | Coincidental lexical phrasing across independent research institutions (e.g. shared generic task words). |
| `cic-ids2017__unsw-nb15` | `cic-ids2017` | `unsw-nb15` | `cross_institution_lexical_similarity` | Coincidental lexical phrasing across independent research institutions (e.g. shared generic task words). |
| `dair-v2x__v2x-seq` | `dair-v2x` | `v2x-seq` | `shared_institutional_catalog_family` | Shared institutional publisher with moderate title or modality overlap. |
| `docvqa__mp-docvqa` | `docvqa` | `mp-docvqa` | `shared_institutional_catalog_family` | Shared institutional publisher with moderate title or modality overlap. |
| `kinetics-400__ucf101` | `kinetics-400` | `ucf101` | `cross_institution_lexical_similarity` | Coincidental lexical phrasing across independent research institutions (e.g. shared generic task words). |
| `mimic-iv__mimic-iv-note` | `mimic-iv` | `mimic-iv-note` | `shared_umbrella_portal_or_challenge_repository` | Shared source documentation or challenge download link without title collision. |
| `mit-bih-arrhythmia__mit-bih-svdb` | `mit-bih-arrhythmia` | `mit-bih-svdb` | `cross_institution_lexical_similarity` | Coincidental lexical phrasing across independent research institutions (e.g. shared generic task words). |
| `mit-bih-normal-sinus-rhythm__normal-sinus-rhythm-rr-interval` | `mit-bih-normal-sinus-rhythm` | `normal-sinus-rhythm-rr-interval` | `shared_institutional_catalog_family` | Shared institutional publisher with moderate title or modality overlap. |
| `mit-bih-svdb__st-petersburg-incart-arrhythmia` | `mit-bih-svdb` | `st-petersburg-incart-arrhythmia` | `shared_umbrella_portal_or_challenge_repository` | Shared source documentation or challenge download link without title collision. |
| `mvtec-ad__mvtec-ad-2` | `mvtec-ad` | `mvtec-ad-2` | `shared_institutional_catalog_family` | Shared institutional publisher with moderate title or modality overlap. |
| `mvtec-ad__mvtec-loco-ad` | `mvtec-ad` | `mvtec-loco-ad` | `shared_institutional_catalog_family` | Shared institutional publisher with moderate title or modality overlap. |
| `noaa-ghcn-daily__noaa-ghcn-hourly` | `noaa-ghcn-daily` | `noaa-ghcn-hourly` | `shared_institutional_catalog_family` | Shared institutional publisher with moderate title or modality overlap. |
| `noaa-ghcn-daily__noaa-ghcn-monthly` | `noaa-ghcn-daily` | `noaa-ghcn-monthly` | `shared_institutional_catalog_family` | Shared institutional publisher with moderate title or modality overlap. |
| `ogbg-code2__ogbg-molhiv` | `ogbg-code2` | `ogbg-molhiv` | `shared_umbrella_portal_or_challenge_repository` | Shared source documentation or challenge download link without title collision. |
| `ogbg-molhiv__ogbg-molpcba` | `ogbg-molhiv` | `ogbg-molpcba` | `shared_umbrella_portal_or_challenge_repository` | Shared source documentation or challenge download link without title collision. |
| `ogbg-molhiv__ogbg-moltox21` | `ogbg-molhiv` | `ogbg-moltox21` | `shared_umbrella_portal_or_challenge_repository` | Shared source documentation or challenge download link without title collision. |
| `ogbg-molhiv__ogbg-ppa` | `ogbg-molhiv` | `ogbg-ppa` | `shared_umbrella_portal_or_challenge_repository` | Shared source documentation or challenge download link without title collision. |
| `ogbg-molhiv__ogbn-arxiv` | `ogbg-molhiv` | `ogbn-arxiv` | `shared_umbrella_portal_or_challenge_repository` | Shared source documentation or challenge download link without title collision. |
| `ogbn-arxiv__ogbn-mag` | `ogbn-arxiv` | `ogbn-mag` | `shared_umbrella_portal_or_challenge_repository` | Shared source documentation or challenge download link without title collision. |
| `ogbn-arxiv__ogbn-papers100m` | `ogbn-arxiv` | `ogbn-papers100m` | `shared_umbrella_portal_or_challenge_repository` | Shared source documentation or challenge download link without title collision. |
| `ogbn-arxiv__ogbn-products` | `ogbn-arxiv` | `ogbn-products` | `shared_umbrella_portal_or_challenge_repository` | Shared source documentation or challenge download link without title collision. |
| `ogbn-arxiv__ogbn-proteins` | `ogbn-arxiv` | `ogbn-proteins` | `shared_umbrella_portal_or_challenge_repository` | Shared source documentation or challenge download link without title collision. |
| `plant-pathology-2020__plant-pathology-2021` | `plant-pathology-2020` | `plant-pathology-2021` | `cross_institution_lexical_similarity` | Coincidental lexical phrasing across independent research institutions (e.g. shared generic task words). |
| `spacenet-2__spacenet-6` | `spacenet-2` | `spacenet-6` | `shared_umbrella_portal_or_challenge_repository` | Shared source documentation or challenge download link without title collision. |
| `spacenet-2__spacenet-7` | `spacenet-2` | `spacenet-7` | `shared_umbrella_portal_or_challenge_repository` | Shared source documentation or challenge download link without title collision. |
| `spacenet-2__spacenet-8` | `spacenet-2` | `spacenet-8` | `shared_umbrella_portal_or_challenge_repository` | Shared source documentation or challenge download link without title collision. |
| `spacenet-6__spacenet-7` | `spacenet-6` | `spacenet-7` | `shared_umbrella_portal_or_challenge_repository` | Shared source documentation or challenge download link without title collision. |
| `spacenet-6__spacenet-8` | `spacenet-6` | `spacenet-8` | `shared_umbrella_portal_or_challenge_repository` | Shared source documentation or challenge download link without title collision. |
| `spacenet-7__spacenet-8` | `spacenet-7` | `spacenet-8` | `shared_umbrella_portal_or_challenge_repository` | Shared source documentation or challenge download link without title collision. |
| `waymo-open-motion__waymo-open-perception` | `waymo-open-motion` | `waymo-open-perception` | `shared_institutional_catalog_family` | Shared institutional publisher with moderate title or modality overlap. |

---

## 5. False-Positive Prevention & Safeguards

To prevent improper merging or deletion of legitimately related research datasets, the semantic duplicate detection engine enforces the following strict safeguards:

1. **Domain Blacklist on Generic Hosting Portals:** Exact matches on root domains or generic directories (e.g., `github.com`, `zenodo.org`, `kaggle.com`, `archive.ics.uci.edu`, `spacenet.ai/datasets`, `disc.gsfc.nasa.gov/datasets`) are excluded from exact URL matching.
2. **Safe URL Canonicalization:** Ignores tracking parameters (`utm_*`, `ref`, `fbclid`, `gclid`) while preserving functional identifiers (`id=` on OpenReview, `ch=` on ICDAR RRC) and explicit version paths (`/v1`, `/v2.1`).
3. **Shared Paper DOI Context:** A shared publication DOI (e.g. `10.5194/essd-15-5491-2023` for WorldCereal, `10.1007/978-3-030-86540-5_37` for Kleister) does not trigger high-confidence duplication because multiple distinct benchmarks are regularly introduced in a single paper.
4. **Discriminating Keyword Detection:** Automatic detection of versions (`v1` vs `v2`, `2018` vs `2019`, `III` vs `IV`), class scales (`10` vs `100`), and sensor modalities (`lidar` vs `sensor`, `pcb` vs `phone`) automatically downgrades pairs from high confidence to medium or low confidence.
5. **Zero Unreliable Automatic Deletions:** Audit outputs are purely advisory and prioritized for human maintainer review.

---

## 6. Actionable Recommendations for Maintainers

1. **Argoverse 2 Suite (`argoverse-2-lidar`, `argoverse-2-motion-forecasting`, `argoverse-2-sensor`):** Maintain all three records as independent benchmarks. Add reciprocal cross-references in `description` or `provenance.curation_notes`.
2. **CIFAR Family (`cifar-10`, `cifar-100`):** Maintain both records. They evaluate distinct 10-class vs 100-class tasks.
3. **Version Progressions (`kolektorsdd` / `kolektorsdd2`, `mimic-iii` / `mimic-iv`, `isic-2018` / `isic-2019`):** Preserve both versions to support historical benchmark comparisons. Explicitly annotate version progression in notes.
4. **Complementary Data Products (`worldcereal-reference-data` vs `esa-worldcereal-global-maps`):** Maintain both. One contains ground-truth point training data; the other contains harmonized global raster crop products.
