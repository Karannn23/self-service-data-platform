# Self-Service Data Insights Platform

## The problem

I noticed a pattern in my own job: business stakeholders constantly need answers from data (how's a product category doing, what are our top sellers), and every single time, someone on the data team has to translate that into a query. It works, but it doesn't scale, and it means the same routine questions keep eating engineering time.

So I built a small, real version of a platform that could fix that: data that's ingested automatically, cleaned and validated before anyone sees it, business logic that's tested rather than trusted, and a safe query layer designed to let a natural-language agent answer questions directly, without ever guessing at a number it can't back up.

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
   Databricks Free Edition: Bronze (raw landing, Unity Catalog schema: bronze)
        ↓
   Silver (cleaned, validated, deduplicated; Unity Catalog schema: silver)
        ↓
   Gold (business aggregates, Unity Catalog schema: gold), built and tested via dbt
        ↓
   MCP tool server: safe, parameterized queries against Gold only,
   designed for natural-language agent access
```

Infrastructure (one Azure resource group + storage account) provisioned via Terraform.

## Data sources

- **Orders & order items** (CSV): from the [Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Real, anonymized commercial data, about 99k orders from 2016 to 2018. It's licensed CC-BY-NC-SA-4.0 (non-commercial), which fits fine for a portfolio project like this.
- **Products** (converted to Parquet): the same dataset's product catalog. I used this as reference data that doesn't change often, which is exactly the kind of thing Parquet's columnar format suits well.
- **Streaming order events**: I don't have a real live feed to pull from, so I replay the historical order data through Kafka at an accelerated pace to simulate one. Worth being upfront about that, it's not a live production stream, just an honest way to demo the streaming architecture.

## Status: core platform complete

- [x] Batch ingestion (Airflow: CSV + Parquet → Bronze)
- [x] Streaming ingestion (Kafka producer, replaying real order data)
- [x] Data quality gates (Bronze to Silver), see "What I found" below
- [x] Gold layer + dbt models (2 tested models, 7 passing tests)
- [x] Real Bronze/Silver/Gold Unity Catalog schema separation
- [x] Terraform infrastructure (Azure resource group + storage account)
- [x] MCP tool layer for natural-language access, with guardrail tests

## Things I actually ran into while building this

**I caught a false-positive in my own data quality check.** Early on in the Silver layer, a duplicate-detection rule I'd written flagged 7,088 "duplicate" order/product combinations. Before I just quarantined them, I went and looked at an actual example, and it turned out they were completely legitimate, a customer ordering two of the same product in one order. My check needed a third key (`order_item_id`) to tell real duplicates apart from valid multi-line orders, so I fixed the check instead of touching the data. It's a small thing, but it's the same lesson behind a real fan-out bug I've caught at work: validate your validation logic too, don't just trust the first rule you write.

**I actually tested whether my MCP tool layer was safe, instead of assuming it.** I passed a classic SQL injection payload (`'; DROP TABLE ...; --`) into one of the query tools to see what would happen. Because the query uses proper parameterization, it came back as an empty result, no error, and the table was completely untouched. That's the real proof behind the "this tool layer is safe" claim, not just something I believed because it seemed right.

**I hit a real dependency conflict, and tested it rather than panicking.** At one point, installing another tool during development downgraded `protobuf` to a version `dbt-core` explicitly says it doesn't support. Rather than assume everything was now broken, I went back and re-ran my actual dbt build and test suite, everything passed exactly like before. Turned out the conflict didn't touch anything I was actually using. Worth remembering: a declared dependency conflict doesn't always mean something's actually broken, it's worth checking before you panic and start reworking your environment.

## Why each tool

- **Airflow**: schedules the batch pipeline that pulls CSV and Parquet sources into Bronze
- **Kafka**: the streaming ingestion layer, simulating a live order feed off historical data
- **Databricks + PySpark + Delta Lake**: where the real transformation, storage, and governance happens, including actual Unity Catalog schema separation (bronze/silver/gold), not just naming conventions pretending to be one
- **dbt**: gives the Gold layer's business logic real tests and documentation instead of leaving it buried in a notebook (2 models, 7 passing tests)
- **Terraform**: provisions the one piece of real cloud infrastructure (an Azure resource group and storage account) as code instead of clicking through the portal
- **MCP tool server**: exposes a handful of safe, parameterized query tools against Gold data only, tested against SQL injection, so an agent can only ever run pre-approved query patterns, never arbitrary SQL against raw data

## Agent integration

The MCP tool server (`mcp_agent/gold_data_server.py`) exposes three tools: `get_sales_by_category`, `get_top_categories`, and `get_top_products`. It's built and fully tested on its own. I haven't wired it up to live Claude API calls though, that would mean ongoing API cost, and I wanted to keep this whole project free. So instead, here's how it's actually meant to be used, worked through by hand:

**Here's roughly what a conversation with it would look like:**

> **User:** "How is the beleza_saude category doing?"
> **Agent:** *(calls `get_sales_by_category("beleza_saude")`)*
> **Tool result:** `{'category': 'beleza_saude', 'total_orders': 8836, 'total_revenue': 1258681.34, 'avg_item_price': 130.16}`
> **Agent:** "beleza_saude is your top-performing category, with 8,836 orders and R$1,258,681 in total revenue, an average item price of R$130.16."

> **User:** "What if I ask about a category that doesn't exist?"
> **Tool result:** `[]`
> **Agent:** "I don't have data for that category, could you check the name, or would you like to see the list of top categories instead?"

That second example is the part I actually care about. The tool comes back empty instead of erroring or guessing, and the agent is expected to just say so honestly, rather than making up a plausible-sounding number.

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
