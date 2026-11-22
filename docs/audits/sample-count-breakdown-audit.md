# OpenDatasets Sample Count Split and Breakdown Audit (Phase 1A)

> **Audit Task:** Phase 1A — Sample Count Split & Breakdown Migration  
> **Total Records Scanned:** 725 datasets  
> **Datasets with Splits:** 328 datasets  
> **Execution Mode:** APPLIED (Committed)  

---

## 1. Executive Summary & Inventory

| Audit Metric | Count | Proportion |
| :--- | :--- | :--- |
| **Total Datasets Scanned** | **725** | 100.0% |
| **Datasets with Partition Splits** | **328** | 45.2% |
| **Standard Pure Partitions (train/val/test)** | **208** | 28.7% |
| **Datasets with Nonstandard Split Keys** | **120** | 16.6% |
| • **Safely Migrated to Structured Breakdown** | **56** | 7.7% |
| • **Requiring Maintainer Manual Review** | **64** | 8.8% |
| **Datasets without Splits (Continuous / Benchmark Suites)** | **397** | 54.8% |

---

## 2. Safely Migrated Datasets (56 records)

The following datasets contained non-partition physical measurements, secondary entity counts, or redundant totals erroneously stored inside `sample_count.splits`. These were cleanly separated into `breakdown` items preserving all numerical facts without fabrication:

| Dataset ID | Classification | Action Taken |
| :--- | :--- | :--- |
| `a2d2-audi-autonomous-driving` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `aflw` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `apolloscape` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `behavior-1k-2026-demos` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `betel-leaf-bangladesh` | `mixed_partitions_and_metrics` | Separated non-partition metrics to breakdown while preserving true partitions in splits |
| `bigearthnet` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `boreas` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `cadc-snow` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `california-housing` | `redundant_total` | Split key 'total' redundantly duplicates sample_count.total |
| `cityscapes` | `mixed_partitions_and_metrics` | Separated non-partition metrics to breakdown while preserving true partitions in splits |
| `contactpose` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `cropharvest` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `deepweeds` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `dex-ycb` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `docvqa` | `mixed_partitions_and_metrics` | Separated non-partition metrics to breakdown while preserving true partitions in splits |
| `dsec-stereo-event` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `dude` | `mixed_partitions_and_metrics` | Separated non-partition metrics to breakdown while preserving true partitions in splits |
| `eurosat` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `furniture-bench` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `graspnet-1billion` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `h3d-honda` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `hmdb51` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `homes-of-new-york-dobb-e` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `iam-handwriting` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `inaturalist-2021` | `mixed_partitions_and_metrics` | Separated non-partition metrics to breakdown while preserving true partitions in splits |
| `infographicvqa` | `mixed_partitions_and_metrics` | Separated non-partition metrics to breakdown while preserving true partitions in splits |
| `iris` | `redundant_total` | Split key 'total' redundantly duplicates sample_count.total |
| `khatt` | `mixed_partitions_and_metrics` | Separated non-partition metrics to breakdown while preserving true partitions in splits |
| `kitti-360` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `lfw` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `mbpp` | `mixed_partitions_and_metrics` | Separated non-partition metrics to breakdown while preserving true partitions in splits |
| `milk10k` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `mimic-iii` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `mimic-iv-ecg` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `mimic-iv-ed` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `mimicgen` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `mp-docvqa` | `mixed_partitions_and_metrics` | Separated non-partition metrics to breakdown while preserving true partitions in splits |
| `ntu-rgbd` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `oasis-3` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `openlane-v2` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `pandaset` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `plantdoc` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `plantvillage` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `radiate` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `rellis-3d` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `robocasa-365` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `robomind` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `robonet` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `semanticposs` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `st-petersburg-incart-arrhythmia` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `total-text` | `mixed_partitions_and_metrics` | Separated non-partition metrics to breakdown while preserving true partitions in splits |
| `ucf101` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `v2x-seq` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |
| `waymo-open-perception` | `mixed_partitions_and_metrics` | Separated non-partition metrics to breakdown while preserving true partitions in splits |
| `xfund` | `mixed_partitions_and_metrics` | Separated non-partition metrics to breakdown while preserving true partitions in splits |
| `zod-zenseact` | `pure_metric_in_splits` | Splits represent physical/sensor metrics or entity counts; migrated to breakdown |

---

## 3. Candidates Requiring Manual Review (64 records)

In accordance with Phase 1A guidelines, fields whose partition semantics cannot be unambiguously proven from existing metadata were left unchanged to prevent unverified assumptions:

| Dataset ID | Existing Split Keys | Scientific Review Reason |
| :--- | :--- | :--- |
| `ai2-arc` | `easy`, `challenge` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `aitex-fabric-image-database` | `defect_free`, `defective` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `ava-action` | `train_clips`, `val_clips`, `test_clips` | Unit mismatch: declared total is 1.62M action labels, while splits represent 430 movie clips |
| `bangla-human-ai-text-classification` | `human`, `ai_generated` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `bangla-nlp-multi-task` | `sentiment_analysis`, `topic_classification`, `hate_speech_detection` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `bangla-tense` | `past`, `present`, `future` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `bangladeshi-currency-recognition` | `taka_2`, `taka_5`, `taka_10`, `taka_20`, `taka_50`, `taka_100`, `taka_200`, `taka_500`, `taka_1000` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `bangladeshi-medicinal-plant-leaves-7` | `raw_images`, `preprocessed_images` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `bangladigit` | `bangladigit_20k`, `bangladigit_60k` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `banknote-authentication` | `genuine`, `forged` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `bijie-landslide` | `landslide`, `non_landslide` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `bracol-coffee-leaf` | `full_leaves`, `symptom_patches` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `btad-beantech-anomaly-detection` | `train`, `test`, `train_01`, `test_01`, `train_02`, `test_02`, `train_03`, `test_03` | Multi-subset benchmark: splits include both aggregate train/test and per-product subsets train_01..03, test_01..03 |
| `bus-bra` | `benign`, `malignant` | Splits represent class label frequencies rather than train/test partitions |
| `calvin-robot-manipulation` | `env_A_hours`, `env_B_hours`, `env_C_hours`, `env_D_hours` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `cap-sleep-database` | `normal`, `pathological` | Splits represent class label frequencies rather than train/test partitions |
| `dagm-2007-industrial-optical-inspection` | `development_classes_1_to_6`, `competition_classes_7_to_10` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `dair-v2x` | `vehicle_infrastructure_pairs`, `infrastructure_only`, `vehicle_only` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `deepglobe` | `road_tiles`, `building_tiles`, `landcover_tiles` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `docile` | `annotated_real`, `synthetic` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `droid-robot-manipulation` | `successful_episodes`, `calibrated_episodes` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `early-stage-diabetes-bangladesh` | `positive`, `negative` | Splits represent class label frequencies rather than train/test partitions |
| `hotpotqa` | `train`, `dev_distractor`, `dev_fullwiki`, `test` | Multi-evaluation benchmark: splits include both dev_distractor and dev_fullwiki evaluation settings |
| `human-vs-ai-rewritten-bengali-text` | `human`, `ai_rewritten` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `hyperkvasir` | `labeled_images`, `unlabeled_images`, `segmented_images`, `videos` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `isic-2018` | `task1_train`, `task1_val`, `task1_test`, `task2_train`, `task3_train`, `task3_val`, `task3_test` | Multi-task benchmark: splits represent task1, task2, and task3 subsets with overlapping sample images |
| `ithaca365` | `repeat_route_runs`, `labeled_cam_frames`, `labeled_lidar_frames` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `jaaltaka` | `genuine`, `counterfeit` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `kolektorsdd` | `defective`, `non_defective` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `kvasir-capsule` | `labeled_frames`, `video_sequences` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `language-table` | `real_robot_relabeled`, `simulation_human`, `simulation_oracle` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `libero` | `libero_spatial`, `libero_object`, `libero_goal`, `libero_10`, `libero_90` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `m6doc` | `textbook`, `test_paper`, `magazine`, `scientific_article`, `newspaper`, `note`, `book` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `magnetic-tile-defect-datasets` | `blowhole`, `crack`, `fray`, `break`, `uneven`, `free` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `marmot` | `chinese_pages`, `english_pages` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `medqa-medical-exam-qa` | `usmle_english`, `mcmqe_simplified_chinese`, `twmle_traditional_chinese` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `mimic-iv-note` | `discharge`, `radiology` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `mobile-aloha` | `wipe_wine`, `cook_shrimp`, `rinse_pan`, `serve_food`, `push_chairs`, `use_elevator`, `high_five` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `ms-coco` | `train`, `validation`, `test` | Benchmark subset partition: splits represent 2017 detection train/val/test subset (163,957 images) of 330k raw archive |
| `mvsec-event-camera` | `car_sequences`, `drone_sequences`, `motorcycle_sequences` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `neu-surface-defect-database` | `crazing`, `inclusion`, `patches`, `pitted_surface`, `rolled_in_scale`, `scratches` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `once-autonomous-driving` | `annotated_frames`, `unlabeled_frames` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `physionet-cinc-2017-af` | `normal`, `af`, `other`, `noisy` | Splits represent class label frequencies rather than train/test partitions |
| `pku-market-phone` | `oil_stains`, `scratches`, `spots` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `polypgen` | `positive_frames`, `negative_frames` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `pubmed-200k-rct` | `train`, `dev`, `test` | Unit/version mismatch: declared total is abstracts (195,654) while splits record sentences (237,690) from 20k subset |
| `pubmedqa` | `labeled`, `unlabeled`, `artificial` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `robomimic` | `proficient_human`, `multi_human`, `machine_generated`, `can_paired` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `roboset` | `teleoperated_trajectories`, `kinesthetic_replay_trajectories` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `skin-disease-classification` | `sjs_ten`, `nail_psoriasis`, `vitiligo`, `acne`, `hyperpigmentation` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `soybean-leaf-pest-damage` | `caterpillar`, `diabrotica_speciosa`, `healthy` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `sunflower-disease-dataset` | `original`, `augmented` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `swat` | `normal`, `attack` | Splits represent class label frequencies rather than train/test partitions |
| `sweet-pumpkin-disease` | `original`, `augmented` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `taiwan-tomato-leaves` | `taiwan_field_original`, `taiwan_field_augmented`, `plantvillage_benchmark` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `uci-chronic-kidney-disease` | `ckd`, `not_ckd` | Splits represent class label frequencies rather than train/test partitions |
| `uci-raisin-classification` | `kecimen`, `besni` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `uci-rice-leaf-diseases` | `bacterial_leaf_blight`, `brown_spot`, `leaf_smut` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `uci-seeds-wheat-kernels` | `kama`, `rosa`, `canadian` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `unsw-nb15` | `train`, `test` | Benchmark subset partition: splits represent official partitioned subset (257,673 flows) of raw archive (2,540,044 flows) |
| `visa-visual-anomaly` | `normal`, `anomalous` | Splits represent class label frequencies rather than train/test partitions |
| `wadi` | `normal`, `attack` | Splits represent class label frequencies rather than train/test partitions |
| `wavcaps` | `freesound`, `audioset_strong`, `bbc_sound_effects`, `soundbible` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |
| `wine-quality` | `red`, `white` | Uncertain split semantics or class/subset distribution; requires primary source confirmation |

---

*Report generated automatically by `scripts/migrate_sample_count_breakdowns.py`.*