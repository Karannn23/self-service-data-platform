# Self-Service Data Insights Platform

## The problem

Business stakeholders regularly need answers from data (e.g., "why did sales drop in a region last month," "which products are trending") but every question currently requires an engineer to translate it into a query. This is slow and doesn't scale.

This project explores whether a governed, self-service natural-language layer can reduce that bottleneck, without sacrificing the reliability and governance discipline real production data platforms require.

## Architecture

```
Olist E-Commerce Dataset (CSV: orders, order_items)
Olist Products Dataset (converted to Parquet: dimension/reference data)
        +
Simulated live order events (replayed via Kafka)
        ↓
   Airflow (batch orchestration)          Kafka (streaming ingestion)
        ↓                                       ↓
   Databricks Free Edition — Bronze (raw landing)
        ↓
   Silver (cleaned, validated, deduplicated — data quality gates)
        ↓
   Gold (business aggregates) — built and tested via dbt
        ↓
   ┌─────────────────────────┬──────────────────────────────┐
   Flink (real-time anomaly       MCP tool server (safe, validated
   detection on the Kafka          queries against Gold only, for
   stream)                         natural-language agent access)
```

Infrastructure (one Azure storage account / resource group) provisioned via Terraform.

## Data sources

- **Orders & order items** (CSV) — [Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), real anonymized commercial data, ~100k orders, 2016–2018
- **Products** (converted to Parquet) — same dataset's product catalog, used as slower-changing dimension/reference data
- **Streaming order events** — simulated in real time by replaying historical order data through Kafka at an accelerated pace (this is historical data, not a live production feed — noted here for transparency)

## Status

Actively being built. See commit history for progress; each component below will be checked off and documented as it's completed.

- [ ] Batch ingestion (Airflow: CSV + Parquet → Bronze)
- [ ] Streaming ingestion (Kafka → Bronze)
- [ ] Data quality gates (Bronze → Silver)
- [ ] Gold layer + dbt models
- [ ] Terraform infrastructure
- [ ] Flink real-time anomaly detection
- [ ] MCP tool layer for natural-language access
- [ ] Monitoring & final documentation

## Why each tool

- **Airflow**: orchestrates scheduled batch ingestion, standard for production pipeline scheduling
- **Kafka**: streaming ingestion layer, simulates a live order feed
- **Databricks + PySpark + Delta Lake**: transformation, storage, and governance (Unity Catalog patterns)
- **dbt**: version-controlled, tested, documented business logic for the Gold layer
- **Terraform**: infrastructure as code, reproducible environment setup
- **Flink**: real-time stream processing, added as an extension to catch anomalies in the live order feed as they happen (added after the core platform was built, to gain hands-on real-time processing experience)
- **MCP tool server**: exposes safe, boundary-scoped query tools against Gold data only, designed to plug into a Claude Agent SDK-based natural-language interface — built and fully tested; live agent integration is documented rather than run continuously, to keep the project at zero ongoing cost
