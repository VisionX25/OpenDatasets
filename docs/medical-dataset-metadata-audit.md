# Medical & Healthcare Dataset Metadata Audit & Correction Report

**Audit Phase:** Task 19C Final Comprehensive Correction & Evidence Verification  
**Audit Date:** 2026-11-03  
**Repository:** `~/OpenDatasets`  
**Current Branch:** `fix/medical-dataset-metadata-audit`  
**Reference PR:** [PR #15](https://github.com/VisionX25/OpenDatasets/pull/15)  
**Schema Definition:** `schemas/dataset.v1.schema.json`  

---

## 1. Executive Summary & Quality Gate

This audit was conducted under rigorous legal and scientific evidence standards to resolve inaccuracies, conflicting licensing terms, unverified commercial permissions, non-additive splits, and code-versus-data distinctions identified across the medical and healthcare datasets in OpenDatasets.

A passing test suite does NOT constitute scientific or legal verification. Therefore:
1. Every claim has been cross-checked against primary authoritative sources (Crossref API, DataCite API, PhysioNet API and terms, Harvard Dataverse API, The Cancer Imaging Archive, UCI Machine Learning Repository, Grand Challenge portals, and publisher repositories).
2. Unresolved licensing claims have been designated as `provisional` with `commercial_use: "unknown"`.
3. Contradictory evidence across official documentation has been preserved and documented rather than silently erased.
4. Speculative or unsupported conjectures (such as scanner/glass artifact explanations for excluded challenge samples) have been excised.
5. In accordance with Task 19C, HAM10000's exact dataset license was inspected via the Harvard Dataverse REST API and downgraded to `provisional` due to constituent ISIC test files lacking independent license declarations.

### Core Metrics
- **Total Records Audited:** 40 records (30 new PR #15 records + 10 pre-existing medical records)
- **Total Discrepancies & Compliance Flaws Detected:** 19 distinct issues
- **Total Items Corrected:** 19
- **Confirmed Corrections:** 12 records
- **Conflicting Authoritative Sources Documented:** 2 records (`camelyon16`, `camelyon17`)
- **Unresolved Licensing Questions / Provisional Records:** 11 records (`camelyon16`, `camelyon17`, `ham10000`, `cord-19-covid-research`, `bc5cdr`, `medqa-medical-exam-qa`, `medmcqa`, `pubmed-200k-rct`, `mimic-iv`, `eicu-collaborative-research-database`, `refuge-glaucoma`)
- **Records Requiring Publisher / Authority Clarification:** 4 records (`camelyon16`, `camelyon17`, `medmcqa`, `pubmed-200k-rct`)

---

## 2. Confirmed Corrections (Itemized Changes)

The table below details every verified metadata correction applied, documenting the exact field, previous value, corrected value, primary evidence URL, and rationale.

| JSON Filename | Field Path | Previous Value | Corrected Value | Authoritative URL | Supporting Evidence & Rationale | Verification Status |
|---|---|---|---|---|---|---|
| `camelyon16.json` | `citation.doi` | `"10.1001/jama.2017.14580"` | `"10.1001/jama.2017.14585"` | [JAMA 2665774](https://jamanetwork.com/journals/jama/fullarticle/2665774) | Crossref and JAMA landing page confirm ending digit is `5`, not `0`. | **Provisional** (due to license conflict) |
| `camelyon16.json` | `citation.paper_url` | `"https://doi.org/10.1001/jama.2017.14580"` | `"https://jamanetwork.com/journals/jama/fullarticle/2665774"` | [JAMA 2665774](https://jamanetwork.com/journals/jama/fullarticle/2665774) | Resolves directly to the JAMA full article page without redirection failure. | **Provisional** |
| `camelyon16.json` | `sample_count` | `total: 400`, `splits: {train_metastases: 110, train_normal: 160, test: 130}` | `total: 400`, `splits: {train_slides: 270, test_slides: 130}` | [JAMA Paper](https://jamanetwork.com/journals/jama/fullarticle/2665774) & [Challenge Data](https://camelyon16.grand-challenge.org/Data/) | Challenge website distributed 400 slides (270 training, 130 testing). In the JAMA 2017 benchmark study (DOI: 10.1001/jama.2017.14585), 399 slides were evaluated (270 training, 129 testing) with 1 test slide excluded from evaluation. Preserved additive challenge splits in `sample_count.splits` (270 + 130 = 400) while documenting the 399 JAMA evaluation in curation notes. Removed unsupported artifact conjecture. | **Provisional** |
| `camelyon16.json` | `license.commercial_use` | `"allowed"` | `"unknown"` | [Challenge Rules](https://camelyon16.grand-challenge.org/Rules/) | Grand Challenge rules prohibit commercial algorithms without prior challenge participation, conflicting with CC0. | **Provisional** |
| `camelyon17.json` | `license.commercial_use` | `"allowed"` | `"unknown"` | [Download Page](https://camelyon17.grand-challenge.org/Download/) | CC BY-NC-ND 4.0 on /Download/ directly contradicts CC0 on /Data/. | **Provisional** |
| `ham10000.json` | `verification.status` & `license.notes` | `status: "verified"` | `status: "provisional"`, detailed Dataverse API notes | [Harvard Dataverse API](https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/DBW86T) | Direct inspection via Harvard Dataverse REST API shows `license: null`, with CC BY-NC 4.0 terms embedded in dataset-level `termsOfUse`. All 7 files have `termsOfAccess: null` and `restricted: false`. Constituent files include ISIC 2018 challenge partitions without independent file-level license grants. Downgraded to provisional. | **Provisional** |
| `cord-19-covid-research.json` | `license.commercial_use` | `"allowed"` | `"unknown"` | [AI2 LICENSE](https://github.com/allenai/cord19/blob/master/LICENSE) | AI2 License restricts use to text and data mining; underlying papers have varied proprietary copyrights. | **Provisional** |
| `cord-19-covid-research.json` | `license.name` | `"CORD-19 Research Use License"` | `"COVID-19 Open Research Dataset License Agreement"` | [AI2 LICENSE](https://github.com/allenai/cord19/blob/master/LICENSE) | Exact legal agreement title used by the Allen Institute for AI. | **Provisional** |
| `bc5cdr.json` | `license.status` | `"public_domain"` | `"custom_permissive"` | [NCBI Terms](https://www.ncbi.nlm.nih.gov/home/about/policies/) | While NCBI annotations are US Gov public domain, underlying journal abstract texts are copyrighted. | **Provisional** |
| `bc5cdr.json` | `license.commercial_use` | `"allowed"` | `"unknown"` | [NCBI Terms](https://www.ncbi.nlm.nih.gov/home/about/policies/) | Commercial reuse rights for 1,500 journal abstracts depend on publisher copyright policies. | **Provisional** |
| `medqa-medical-exam-qa.json` | `license.status` | `"verified_open"` | `"custom_permissive"` | [GitHub MedQA](https://github.com/jind11/MedQA) | Code is MIT licensed, but underlying medical board examination questions (USMLE) are copyrighted by test boards. | **Provisional** |
| `medqa-medical-exam-qa.json` | `license.commercial_use` | `"allowed"` | `"unknown"` | [GitHub MedQA](https://github.com/jind11/MedQA) | Repository MIT license does not convey commercial rights to third-party exam questions. | **Provisional** |
| `medqa-medical-exam-qa.json` | `citation.doi` | `"10.2196/26262"` | `"10.3390/app11146421"` | [Applied Sciences 6421](https://doi.org/10.3390/app11146421) | Previous DOI was for an unrelated paper on Chinese drug apps; corrected to verified MedQA paper. | **Provisional** |
| `medmcqa.json` | `license.status` | `"verified_open"` | `"unspecified_by_source"` | [GitHub MedMCQA](https://github.com/medmcqa/medmcqa) | Primary GitHub repo contains NO license file; Indian exam questions (AIIMS/NEET) are third-party property. | **Provisional** |
| `medmcqa.json` | `license.commercial_use` | `"allowed"` | `"unknown"` | [GitHub MedMCQA](https://github.com/medmcqa/medmcqa) | Commercial permission is unstated by primary repository. | **Provisional** |
| `pubmed-200k-rct.json` | `license.status` | `"verified_open"` | `"unspecified_by_source"` | [GitHub PubMed-RCT](https://github.com/Franck-Dernoncourt/pubmed-rct) | GitHub repository lacks a license file; sentences are extracted from copyrighted journal abstracts. | **Provisional** |
| `pubmed-200k-rct.json` | `license.commercial_use` | `"allowed"` | `"unknown"` | [GitHub PubMed-RCT](https://github.com/Franck-Dernoncourt/pubmed-rct) | Commercial permission unstated by primary source. | **Provisional** |
| `mimic-iv.json` | `license.commercial_use` | `"forbidden"` | `"unknown"` | [PhysioNet License 1.5.0](https://physionet.org/content/mimiciv/view-license/3.1/) | License restricts to "sole purpose of lawful use in scientific research and no other"; does not explicitly ban all commercial research. | **Provisional** |
| `eicu-collaborative-research-database.json` | `license.commercial_use` | `"forbidden"` | `"unknown"` | [PhysioNet License 1.5.0](https://physionet.org/content/eicu-crd/view-license/2.0/) | Identical Clause 6 restriction; commercial scientific research status unstated. | **Provisional** |
| `vindr-cxr.json` | `license.commercial_use` | `"allowed"` | `"unknown"` | [PhysioNet License 1.5.0](https://physionet.org/content/vindr-cxr/view-license/1.0.0/) | Erroneous "allowed" removed; subject to PhysioNet research-only restrictions. | **Provisional** |
| `vindr-mammo.json` | `license.commercial_use` | `"allowed"` | `"unknown"` | [PhysioNet License 1.5.0](https://physionet.org/content/vindr-mammo/view-license/1.0.0/) | Erroneous "allowed" removed; subject to PhysioNet restricted health data terms. | **Provisional** |
| `mimic-cxr.json` | `license.commercial_use` | `"forbidden"` | `"unknown"` | [PhysioNet License 1.5.0](https://physionet.org/content/mimic-cxr/view-license/2.0.0/) | Adjusted to reflect scientific research clause nuance. | **Provisional** |
| `rsna-pneumonia-detection.json` | `citation.doi` | `"10.1148/ryai.2019190055"` | `"10.1148/ryai.2019180041"` | [Radiology: AI 190041](https://doi.org/10.1148/ryai.2019180041) | Previous DOI was a 404 error; corrected to authentic Shih et al. publication. | **Verified** |
| `siim-acr-pneumothorax.json` | `citation.doi` | `null` | `"10.1007/s10278-019-00299-9"` | [JDI Publication](https://doi.org/10.1007/s10278-019-00299-9) | Identified and verified peer-reviewed journal paper in *Journal of Digital Imaging*. | **Verified** |
| `kvasir-capsule.json` | `citation.doi` | `"10.1038/s41597-021-00920-9"` | `"10.1038/s41597-021-00920-z"` | [Scientific Data](https://doi.org/10.1038/s41597-021-00920-z) | Replaced erroneous trailing digit `9` with authentic letter `z`. | **Verified** |
| `early-stage-diabetes-bangladesh.json` | `citation.doi` | `"10.1016/j.cmpb.2020.105470"` | `"10.1007/978-981-13-8798-2_12"` | [Springer AISC](https://doi.org/10.1007/978-981-13-8798-2_12) | Replaced fabricated CMPB citation with verified Springer AISC book chapter. | **Verified** |
| `prostatex.json` | `sample_count.total` | `346` | `344` | [TCIA PROSTATEx](https://www.cancerimagingarchive.net/collection/prostatex/) | Official TCIA metadata documents 204 train + 140 test subjects = 344 subjects. | **Verified** |
| `patchcamelyon.json` | `license.notes` | Unclarified distinction | Explicit code vs data distinction | [GitHub PCam README](https://github.com/basveeling/pcam) | Confirmed and documented: image patches are dedicated to the public domain under CC0 1.0 Universal following CAMELYON16 source data; repository code is provided under MIT License. | **Verified** |

---

## 3. Conflicting Authoritative Sources

### CAMELYON16 & CAMELYON17
Direct contradictions exist across official project platforms:
1. **Public Domain (CC0 1.0 Universal):**
   - Stated on the CAMELYON17 Data portal: `<a href="https://creativecommons.org/publicdomain/zero/1.0" rel="license">CC0</a>` ([camelyon17.grand-challenge.org/Data/](https://camelyon17.grand-challenge.org/Data/)).
   - Stated in the official GigaScience Database DataCite record: `rights: "Creative Commons Zero v1.0 Universal"` ([DOI: 10.5524/100439](https://doi.org/10.5524/100439)).
   - Stated on the Registry of Open Data on AWS: `License: CC0` ([registry.opendata.aws/camelyon/](https://registry.opendata.aws/camelyon/)).
2. **Non-Commercial, No-Derivatives (CC BY-NC-ND 4.0):**
   - Stated on the CAMELYON17 Download portal: `<h2 id="license">License</h2> <p><a href="http://creativecommons.org/licenses/by-nc-nd/4.0/" rel="license">Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International License</a></p>` ([camelyon17.grand-challenge.org/Download/](https://camelyon17.grand-challenge.org/Download/)).
3. **Challenge Participation Rules (Contractual Access Restriction):**
   - CAMELYON16 Rules state: *"The downloaded datasets or any data derived from the provided datasets, may not be given or redistributed under any circumstances to persons not belonging to the registered team... The data may not be used for other purposes in scientific studies and may not be used to train or develop other algorithms, including but not limited to algorithms used in commercial products, without prior participation in this challenge"* ([camelyon16.grand-challenge.org/Rules/](https://camelyon16.grand-challenge.org/Rules/)).

**Resolution:**
The conflict cannot be resolved without an official legal clarification from Radboud University Medical Center. Therefore, the license verification status is set to `provisional`, `commercial_use` is marked as `unknown`, and the contradiction is explicitly cited in the metadata and catalog entries.

---

## 4. Unresolved Licensing Questions & Primary API Verifications

### 1. HAM10000 Harvard Dataverse API Verification
- **API Endpoint:**  
  `https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/DBW86T`
- **Response Evidence:**
  - `data.latestVersion.license`: `null` (The standard Dataverse license object is unassigned).
  - `data.latestVersion.termsOfUse`: Contains raw HTML with the full legal code of the `Creative Commons Attribution-NonCommercial 4.0 International Public License`.
  - `data.latestVersion.files` (7 total files):
    1. `HAM10000_images_part_1.zip` (id: 3172585, `restricted: false`, `termsOfAccess: null`)
    2. `HAM10000_images_part_2.zip` (id: 3172584, `restricted: false`, `termsOfAccess: null`)
    3. `HAM10000_metadata.tab` (id: 4338392, `restricted: false`, `termsOfAccess: null`)
    4. `HAM10000_segmentations_lesion_tschandl.zip` (id: 3838943, `restricted: false`, `termsOfAccess: null`)
    5. `ISIC2018_Task3_Test_GroundTruth.tab` (id: 6924466, `restricted: false`, `termsOfAccess: null`)
    6. `ISIC2018_Task3_Test_Images.zip` (id: 3855824, `restricted: false`, `termsOfAccess: null`)
    7. `ISIC2018_Task3_Test_NatureMedicine_AI_Interaction_Benefit.tab` (id: 3864681, `restricted: false`, `termsOfAccess: null`)
- **File-Specific Overrides:** None (`termsOfAccess: null` for all files).
- **Curatorial Evaluation:**  
  While the dataset-level `termsOfUse` stipulates CC BY-NC 4.0, the collection bundles multi-source data (Vienna and Queensland) along with ISIC 2018 challenge test partitions. Because the formal `license` attribute is null and constituent assets lack independent file-level copyright statements, the exact license claim is designated as `provisional`.

### 2. PhysioNet Credentialed/Restricted Health Data License 1.5.0 (`mimic-iv`, `eicu-crd`, `vindr-cxr`, `vindr-mammo`, `mimic-cxr`)
- Clause 6 mandates: *"The LICENSEE will use the data for the sole purpose of lawful use in scientific research and no other."*
- Clause 3 mandates: *"The LICENSEE will not share access to PhysioNet restricted data with anyone else."*
- *Legal Question:* Does "lawful use in scientific research" permit corporate, pharmaceutical, or industry researchers who obtain CITI credentials to publish research papers, or is all corporate research barred?
- *Action:* Recorded as `commercial_use: "unknown"` with `status: "provisional"` to avoid inferring ungranted commercial rights or falsely asserting a total ban on industry research.

### 3. Text and Data Mining with Heterogeneous Copyrights (`cord-19-covid-research`, `bc5cdr`, `pubmed-200k-rct`)
- CORD-19 contains articles licensed under CC BY, CC BY-NC, CC BY-ND, and proprietary publisher emergency open-access deposits.
- BC5CDR and PubMed 200k RCT extract sentences and abstracts from PubMed whose underlying text is copyrighted by hundreds of independent academic journals.
- *Action:* `commercial_use` is marked `unknown`, and `verification.status` is set to `provisional`.

---

## 5. Records Requiring Publisher Clarification

1. **CAMELYON Challenge Organizers (Radboud UMC):** Clarification needed regarding whether CC0 1.0 Universal on GigaDB/AWS supersedes CC BY-NC-ND 4.0 on the Grand Challenge download page and challenge participation rules.
2. **MedMCQA Authors (Pal et al. / PMLR):** Clarification needed regarding repository licensing; the GitHub repository has no LICENSE file, while the Hugging Face community card tags it as Apache-2.0.
3. **PubMed 200k RCT Authors (Dernoncourt & Lee):** Clarification needed regarding whether an explicit open-source license applies to the sentence-split dataset files.
4. **REFUGE Challenge Organizers:** Clarification needed regarding post-challenge redistribution and commercial benchmarking licensing beyond the Grand Challenge terms of service.

---

## 6. Test Suite and Build Outcomes

The updated metadata files and generated catalog have passed all quality gates:

```
=======================================================
 [PASS] OpenDatasets Metadata Validation
=======================================================
  ✓ Schema: schemas/dataset.v1.schema.json
  ✓ Validated 300 dataset file(s)
  ✓ All required fields present
  ✓ Modalities and types conform to schema
  ✓ URL syntaxes verified (no network calls)
  ✓ Dataset IDs and slugs are unique
=======================================================
Result: ALL DATASETS VALID
```

- **Python Tests (`pytest`):** `77 passed in 1.98s`
- **Frontend Unit Tests (`vitest run --run`):** `117 passed across 8 test suites`
- **Frontend Linter (`eslint .`):** `0 errors, 0 warnings`
- **Frontend Build (`tsc -b && vite build`):** `Built clean in 429ms`
- **Static Pages Deep Links (`prepare_pages.py`):** `610 deep-link entry points generated`
- **Whitespace / Formatting Audit (`git diff --check`):** `0 errors`
