# Task 38 Metadata Audit — Correction Evidence Log

This log records every targeted metadata correction made during Task 38. In accordance with OpenDatasets curation principles, corrections are applied strictly when directly supported by primary publisher documentation, official terms of service, or foundational research publications.

---

## 1. Cora Citation Network (`data/datasets/cora-citation-network.json`)

* **Dataset ID:** `cora-citation-network`
* **Field Corrected:** `license`
* **Original Values:**
  - `license.status`: `"custom_permissive"`
  - `license.name`: `"Open Academic Research Use"`
  - `license.commercial_use`: `"allowed"`
  - `license.notes`: `"Freely available for academic research and evaluation."`
* **Corrected Values:**
  - `license.status`: `"unspecified_by_source"`
  - `license.name`: `"Unspecified by Source (LINQS Academic Research)"`
  - `license.commercial_use`: `"unknown"`
  - `license.notes`: `"Hosted by LINQS (UC Santa Cruz / University of Maryland) for academic research and citation network benchmarking. The primary publisher website does not declare a standardized open data license or explicit commercial use authorization; commercial usability is cataloged as unknown."`
* **Primary Source Evidence:**
  - Official Repository URL: `https://linqs.org/datasets/#cora`
  - Foundational Paper: McCallum et al., *Automating the Construction of Internet Portals with Machine Learning*, Information Retrieval (2000), DOI: [10.1023/A:1009953814988](https://doi.org/10.1023/A:1009953814988).
* **Rationale:**
  The LINQS project portal distributes the Cora citation network for academic machine learning research and benchmarking. The primary authors provide no formal open data grant or express commercial authorization for downstream commercial exploitation of the crawled bibliographic records. Claiming `commercial_use: "allowed"` was an unsupported inference. The record is now accurately cataloged as `unknown` commercial use and `unspecified_by_source`.

---

## 2. UCR Time Series Classification Archive (`data/datasets/ucr-time-series-archive.json`)

* **Dataset ID:** `ucr-time-series-archive`
* **Field Corrected:** `license`
* **Original Values:**
  - `license.status`: `"custom_permissive"`
  - `license.name`: `"Open Academic Research Use"`
  - `license.commercial_use`: `"allowed"`
  - `license.notes`: `"Freely provided to the research community for algorithmic benchmarking and evaluation."`
* **Corrected Values:**
  - `license.status`: `"unspecified_by_source"`
  - `license.name`: `"Unspecified by Source (UCR / UEA Academic Research Archive)"`
  - `license.commercial_use`: `"unknown"`
  - `license.notes`: `"Hosted at timeseriesclassification.com for academic research benchmarking and reproducibility. The archive aggregates diverse time-series datasets from various domain donors without an explicit universal commercial use authorization; commercial usability is cataloged as unknown."`
* **Primary Source Evidence:**
  - Official Repository URL: `https://www.timeseriesclassification.com/`
  - Foundational Paper: Bagnall et al., *The UEA & UCR Time Series Classification Repository*, Data Mining and Knowledge Discovery (2019), DOI: [10.1007/s10618-019-00619-1](https://doi.org/10.1007/s10618-019-00619-1).
* **Rationale:**
  The UCR/UEA archive aggregates time-series benchmarks contributed by hundreds of independent research groups and domain donors over two decades. The hosting portal requests academic citation and benchmarking use, but does not possess or issue a blanket commercial license covering all third-party datasets in the archive. Reconciling `commercial_use` to `unknown` and `status` to `unspecified_by_source` upholds OpenDatasets' strict evidentiary standard.

---

## 3. Multi-Vehicle Stereo Event Camera Dataset (`data/datasets/mvsec-event-camera.json`)

* **Dataset ID:** `mvsec-event-camera`
* **Field Corrected:** `license.notes`
* **Original Value:**
  - `license.notes`: `"Freely available under CC BY 4.0 for commercial and non-commercial research and development."`
* **Corrected Value:**
  - `license.notes`: `"Freely available under CC BY-SA 4.0 for commercial and non-commercial research and development."`
* **Primary Source Evidence:**
  - Official Project Portal: `https://daniilidis-group.github.io/mvsec/`
  - Canonical Paper: Zhu et al., *The Multi-Vehicle Stereo Event Camera Dataset: An Event Camera Dataset for 3D Perception*, IEEE Robotics and Automation Letters (2018), DOI: [10.1109/LRA.2018.2800793](https://doi.org/10.1109/LRA.2018.2800793).
* **Rationale:**
  The dataset's declared license name is `Creative Commons Attribution-ShareAlike 4.0 International` with `spdx_id: "CC-BY-SA-4.0"`, matching the official project portal terms. The explanatory text in `notes` contained a typographical discrepancy omitting `-SA` (`CC BY 4.0` instead of `CC BY-SA 4.0`). The note was harmonized with the canonical SPDX license grant.

---

## 4. Abdominal and Direct Fetal ECG Database (`data/datasets/abdominal-direct-fetal-ecg.json`)

* **Dataset ID:** `abdominal-direct-fetal-ecg`
* **Fields Corrected:** `citation` (`paper_title`, `paper_url`, `doi`, `bibtex`), `source_references` (original_paper title and URL), and `verification.notes`.
* **Original Values:**
  - `citation.paper_url`: `"https://doi.org/10.1109/TBME.2011.2179934"` (Returned HTTP 404 Not Found on doi.org)
  - `citation.doi`: `"10.13026/C2RP4B"` (Merged dataset DOI into citation object)
  - `citation.bibtex`: Declared journal as `IEEE Transactions on Biomedical Engineering`, Vol 59, No 3, pp 686-694, 2012.
  - `source_references[1].url`: `"https://doi.org/10.1109/TBME.2011.2179934"`
  - `source_references[1].title`: `"Jezewski et al. IEEE Transactions on Biomedical Engineering 2012 Publication"`
* **Corrected Values:**
  - `citation.paper_title`: `"Determination of fetal heart rate from abdominal signals: evaluation of beat-to-beat accuracy in relation to the direct fetal electrocardiogram"`
  - `citation.paper_url`: `"https://doi.org/10.1515/bmt-2011-0130"` (Resolves via HTTP 302 to De Gruyter with HTTP 200)
  - `citation.doi`: `"10.1515/bmt-2011-0130"`
  - `citation.bibtex`: Corrected to `Biomedizinische Technik / Biomedical Engineering`, Vol 57, No 5, pp 383–394, 2012, Publisher: De Gruyter, DOI: `10.1515/bmt-2011-0130`.
  - `source_references[1].url`: `"https://doi.org/10.1515/bmt-2011-0130"`
  - `source_references[1].title`: `"Jezewski et al. Biomedizinische Technik / Biomedical Engineering 2012 Publication"`
  - Dataset Identifier Preservation: Preserved PhysioNet repository DOI `10.13026/C2RP4B` in `source_references[0]`.
* **Primary Source Evidence:**
  - PubMed Central / NLM Record: [PMID: 25854665](https://pubmed.ncbi.nlm.nih.gov/25854665/)
  - De Gruyter Publisher Record: DOI [10.1515/bmt-2011-0130](https://doi.org/10.1515/bmt-2011-0130)
  - PhysioNet Archive: [ADFECGDB Repository (DOI: 10.13026/C2RP4B)](https://doi.org/10.13026/C2RP4B)
* **Rationale:**
  Automated HTTP pilot checks identified DOI `10.1109/TBME.2011.2179934` as non-existent (HTTP 404). Primary literature investigation through PubMed and De Gruyter confirmed that the foundational validation study by Jezewski, Matonia, Kupka, Roj, and Czabanski was published in *Biomedizinische Technik / Biomedical Engineering* (2012, 57(5):383–394, DOI: 10.1515/bmt-2011-0130). The citation was corrected to the authentic De Gruyter DOI while explicitly retaining the distinct PhysioNet dataset DOI (`10.13026/C2RP4B`).

---

## 5. Agriculture-Vision: Aerial Farmland Pattern Analysis Benchmark (`data/datasets/agriculture-vision.json`)

* **Dataset ID:** `agriculture-vision`
* **Fields Corrected:** `license.url`, `license.notes`, `source_references`, `description`, `verification.notes`.
* **Original Values:**
  - `license.url`: `"https://www.agriculture-vision.com/dataset"` (Returned HTTP 404 Not Found)
  - `license.notes`: `"Available for academic research and educational competition use under the Agriculture-Vision DUA."`
  - `source_references`: Lacked direct URL to the original 2020 dataset release.
* **Corrected Values:**
  - `license.url`: `"https://www.agriculture-vision.com/dataset-terms"` (Active, HTTP 200)
  - `license.notes`: `"Subject to IntelinAir Agriculture-Vision Dataset Terms. Permitted use is strictly limited to internal non-commercial academic research and participation in the Agriculture-Vision Challenge/creating a submission. Commercial use, developing commercial products/services, or creating derivative works other than the challenge submission is strictly forbidden. The agreement requires users to delete all copies of the dataset within ninety (90) days after the completion date of the Challenge, or immediately upon termination. The terms do not grant permanent unrestricted academic use."`
  - `source_references`: Added `"Agriculture-Vision 2020 Original Dataset Release"` pointing to `"https://www.agriculture-vision.com/agriculture-vision-2020/dataset"` (Active, HTTP 200).
  - `description`: Explicitly distinguishes the foundational 2020 benchmark release (94,986 multi-spectral patches) from subsequent annual challenge iterations.
  - License Terms: Preserved strict non-commercial research terms (`commercial_use: "forbidden"`), document usage period and 90-day post-challenge deletion mandate.
* **Primary Source Evidence:**
  - Agriculture-Vision Official Portal: `https://www.agriculture-vision.com/`
  - Active Dataset Terms: `https://www.agriculture-vision.com/dataset-terms`
  - Original 2020 Dataset Repository: `https://www.agriculture-vision.com/agriculture-vision-2020/dataset`
  - Foundational CVPR 2020 Paper: Chiu et al., DOI: [10.1109/CVPR42600.2020.00290](https://doi.org/10.1109/CVPR42600.2020.00290).
* **Rationale:**
  The Agriculture-Vision challenge website reorganized its URL hierarchy, deprecating `/dataset` in favor of `/dataset-terms` for licensing and `/agriculture-vision-2020/dataset` for the original 2020 dataset download. Both active URLs were verified with HTTP 200. A comprehensive legal review of IntelinAir's Dataset Terms established that permissions are tied to participation in the Challenge and internal non-commercial research, mandating complete data deletion within 90 days after Challenge completion, and prohibiting commercial development or permanent unrestricted retention.

---

## 6. Alzheimer's Disease Neuroimaging Initiative (ADNI) (`data/datasets/adni.json`)

* **Dataset ID:** `adni`
* **Fields Corrected:** `license.url`, `source_references`, `verification.notes`.
* **Original Values:**
  - `license.url`: `"https://adni.loni.usc.edu/data-samples/access-data/"` (Returned HTTP 404 Not Found)
* **Corrected Values:**
  - `license.url`: `"https://adni.loni.usc.edu/data-samples/adni-data/"` (Active, HTTP 200)
  - `source_references`: Added `"ADNI Data Access Application & Portal (LONI IDA)"` pointing to `"https://adni.loni.usc.edu/data-samples/adni-data/"`.
  - License Restrictions: Preserved strict ADNI Data Use Agreement (DUA) restrictions prohibiting commercial exploitation, raw participant redistribution, and uncontained public AI tool submission.
* **Primary Source Evidence:**
  - Official ADNI Access Portal: `https://adni.loni.usc.edu/data-samples/adni-data/`
  - LONI Image & Data Archive (IDA): `https://ida.loni.usc.edu/`
  - Foundational Paper: Mueller et al., Neuroimaging Clinics of North America (2005), DOI: [10.1016/j.nic.2005.09.008](https://doi.org/10.1016/j.nic.2005.09.008).
* **Rationale:**
  The ADNI website migrated its access documentation from `/data-samples/access-data/` to `/data-samples/adni-data/`. The active URL directly provides the online DUA instructions and application gateway to the LONI IDA platform. The specific application path was preserved rather than genericizing to the root domain.

---

## 7. APTOS 2019 Blindness Detection (`data/datasets/aptos-2019-blindness-detection.json`)

* **Dataset ID:** `aptos-2019-blindness-detection`
* **Audit Determination:**
  - Canonical URL: `https://www.kaggle.com/competitions/aptos2019-blindness-detection/data`
  - Audit Result: Unauthenticated programmatic HTTP requests return 404 because Kaggle enforces an active authenticated user session for competition data tabs.
  - Action Taken: **No URL alteration.** The canonical URL is preserved. The audit checker classifies this response as `is_conclusive: false` (authenticated session required) rather than a broken or dead URL.
