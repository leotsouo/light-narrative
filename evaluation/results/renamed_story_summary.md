# Evaluation Summary: renamed_story

## Overview

本次評估使用人工標準答案與系統輸出的 JSON 報告進行比對。

## Metrics

| Metric | Value |
|---|---:|
| Total Expected | 5 |
| Total Predicted | 7 |
| TP | 5 |
| FP | 2 |
| FN | 0 |
| Precision | 0.714 |
| Recall | 1.0 |
| F1 | 0.833 |
| Duplicate Count | 0 |
| Duplicate Rate | 0.0 |
| Evidence Accuracy | 1.0 |

## Interpretation

系統已能抓到多數核心衝突，但仍可能存在部分誤判與漏抓。後續可針對 false positive、evidence selection 與 character consistency drift 進行改善。

## Missed Conflicts

- （無）

## False Positives

- item_location_conflict：物品「青銅印」持有人不一致
- character_consistency_drift：角色「韓逐」能力或性格表現出現漂移

## Limitations

此評估為期末專題展示用的簡化比對方式，並非正式學術級 benchmark。
