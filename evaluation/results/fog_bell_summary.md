# Evaluation Summary: fog_bell

## Overview

本次評估使用人工標準答案與系統輸出的 JSON 報告進行比對。

## Metrics

| Metric | Value |
|---|---:|
| Total Expected | 6 |
| Total Predicted | 6 |
| TP | 6 |
| FP | 0 |
| FN | 0 |
| Precision | 1.0 |
| Recall | 1.0 |
| F1 | 1.0 |
| Duplicate Count | 0 |
| Duplicate Rate | 0.0 |
| Evidence Accuracy | 1.0 |

## Interpretation

系統已能抓到多數核心衝突，但仍可能存在部分誤判與漏抓。後續可針對 false positive、evidence selection 與 character consistency drift 進行改善。

## Missed Conflicts

- （無）

## False Positives

- （無）

## Limitations

此評估為期末專題展示用的簡化比對方式，並非正式學術級 benchmark。
