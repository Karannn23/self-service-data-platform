# Self-Service Data Insights Platform

## The problem

Business stakeholders regularly need answers from data (e.g., "how are we doing in a product category," "what are our top products") but every question currently requires an engineer to translate it into a query. This is slow and doesn't scale, and it's the same bottleneck I handle at IBM day to day, translating stakeholder requests into governed data outputs.

This project builds a small, real version of that platform: automated ingestion, validated and governed data, tested business logic, and a safe, boundary-scoped tool layer designed to let a natural-language agent answer questions directly, without risking an incorrect or ungoverned answer.

## Architecture

```
Olist E-Commerce Dataset
  - orders + order_items (CSV)
  - products (converted to Parquet)
        +
Simulated live order events (replayed via Kafka)
        ↓
   Airflow (batch orchestration)      Kafka (streaming ingestion)
        ↓                                    ↓
   Databricks Free Edition — Bronze (raw landing, Unity Catalog schema: bronze)
        ↓
   Silver (cleaned, validated, deduplicated — Unity Catalog schema: silver)
        ↓
   Gold (business aggregates, Unity Catalog schema: gold) — built and tested via dbt
        ↓
   MCP tool server — safe, parameterized queries against Gold only,
   designed for natural-language agent access
```

Infrastructure (one Azure resource group + storage account) provisioned via Terraform.

## Data sources

- **Orders & order items** (CSV) — [Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), real anonymized commercial data, ~99k orders, 2016–2018. Licensed CC-BY-NC-SA-4.0 (non-commercial), appropriate for this portfolio project.
- **Products** (converted to Parquet) — same dataset's product catalog, used as slower-changing dimension/reference data
- **Streaming order events** — simulated by replaying historical order data through Kafka at an accelerated pace (this is historical data, not a live production feed — noted here for transparency)

## Status: core platform complete

- [x] Batch ingestion (Airflow: CSV + Parquet → Bronze)
- [x] Streaming ingestion (Kafka producer, replaying real order data)
- [x] Data quality gates (Bronze → Silver) — see "What I found" below
- [x] Gold layer + dbt models (2 tested models, 7 passing tests)
- [x] Real Bronze/Silver/Gold Unity Catalog schema separation
- [x] Terraform infrastructure (Azure resource group + storage account)
- [x] MCP tool layer for natural-language access, with guardrail tests
- [ ] Flink real-time anomaly detection — **attempted, descoped** (see below)

## What I found while building this

**A false-positive in my own data quality check.** Early in the Silver layer, a duplicate-detection rule flagged 7,088 "duplicate" order/product combinations. Investigating before quarantining them, I found they were legitimate multi-unit orders (a customer ordering 2+ of the same product), not errors — the check needed a third key (`order_item_id`) to distinguish real duplicates from valid multi-line orders. Fixed the check rather than the data. This mirrors a real fan-out issue I've caught in production: validating your validation logic, not just trusting the first rule you write.

**A SQL injection test against the MCP tool layer.** Passed a malicious payload (`'; DROP TABLE ...; --`) as a query parameter to confirm the parameterized-query pattern neutralizes it — returned an empty result with no error and no damage to the table. This is the concrete proof behind the tool layer's safety design, not just an assumption.

**Flink was descoped after hitting a genuine platform limitation.** PyFlink's Python UDF execution relies on spawning a subprocess (via Apache Beam's portability framework), which has known reliability issues on Windows — confirmed by a "process died with exit code 0" failure after resolving several other setup issues (JAR loading, API version differences). Rather than build a custom Docker image to route around a Windows-specific limitation, I made a scoping call to close out the project with the working components rather than over-invest in one platform-specific rough edge. The Kafka producer built for this (`kafka/producer.py`) works correctly and remains part of the platform.

**A real dependency conflict, tested rather than assumed.** Installing PyFlink downgraded `protobuf` to a version `dbt-core` explicitly flags as incompatible. Rather than assume this broke things, I re-ran the actual dbt build and test suite — everything passed identically to before, confirming the conflict didn't affect this project's actual usage pattern. (This risk assessment is itself worth noting: declared dependency conflicts don't always translate to runtime breakage — worth testing, not assuming.)

## Why each tool

- **Airflow**: orchestrates scheduled batch ingestion of CSV and Parquet sources into Bronze
- **Kafka**: streaming ingestion layer, simulates a live order feed from historical data
- **Databricks + PySpark + Delta Lake**: transformation, storage, and governance — real Unity Catalog schema separation (bronze/silver/gold), not just naming conventions
- **dbt**: version-controlled, tested, documented business logic for the Gold layer (2 models, 7 tests)
- **Terraform**: infrastructure as code — a real Azure resource group and storage account, provisioned and verified
- **MCP tool server**: exposes safe, boundary-scoped query tools against Gold data only, using parameterized queries (tested against SQL injection) so an agent can only run pre-validated query patterns, never arbitrary SQL against raw data

## Agent integration

The MCP tool server (`mcp_agent/gold_data_server.py`) exposes three tools: `get_sales_by_category`, `get_top_categories`, and `get_top_products`. It is built and fully tested standalone — live integration with the Claude Agent SDK is documented conceptually below rather than run continuously, to keep this project at zero ongoing API cost.

**Example conversation (hand-constructed, illustrating the intended flow):**

> **User:** "How is the beleza_saude category doing?"
> **Agent:** _(calls `get_sales_by_category("beleza_saude")`)_
> **Tool result:** `{'category': 'beleza_saude', 'total_orders': 8836, 'total_revenue': 1258681.34, 'avg_item_price': 130.16}`
> **Agent:** "beleza_saude is your top-performing category, with 8,836 orders and R$1,258,681 in total revenue — an average item price of R$130.16."

> **User:** "What if I ask about a category that doesn't exist?"
> **Tool result:** `[]`
> **Agent:** "I don't have data for that category — could you check the name, or would you like to see the list of top categories instead?"

This second example is the deliberate reliability pattern: the tool returns an empty result rather than an error or a guessed answer, and the agent is expected to report that honestly rather than fabricate a number.

## Setup

See `GETTING_THE_DATA.md` for dataset download instructions. Requires Docker Desktop, Python 3.11+, a Databricks Free Edition workspace, and an Azure Free Tier subscription (for the Terraform component).

```
docker compose up -d          # Airflow + Kafka
pip install -r requirements.txt
python kafka/producer.py      # simulate the order event stream
cd retail_gold && dbt run     # build Gold models
cd terraform && terraform apply
cd mcp_agent && python test_guardrails.py
```
