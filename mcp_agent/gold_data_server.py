"""
MCP tool server exposing safe, validated query tools against the Gold
layer only. This is the boundary that lets a natural-language agent
answer business questions WITHOUT running arbitrary SQL against raw
or unvalidated data -- every tool here wraps one specific, safe,
parameterized query.

This server is built and testable on its own. Live integration with
the Claude Agent SDK is documented in README.md rather than run
continuously, to keep this project at zero ongoing API cost.
"""

import os
from databricks import sql
from mcp.server.mcpserver import MCPServer
from dotenv import load_dotenv

load_dotenv()

mcp = MCPServer("gold-data-server")

DATABRICKS_SERVER_HOSTNAME = os.environ["DATABRICKS_SERVER_HOSTNAME"]
DATABRICKS_HTTP_PATH = os.environ["DATABRICKS_HTTP_PATH"]
DATABRICKS_TOKEN = os.environ["DATABRICKS_TOKEN"]


def run_query(query: str, params: tuple = ()) -> list[dict]:
    """
    Runs a parameterized query against Databricks and returns rows
    as a list of dicts. Using parameterized queries (the %s + params
    pattern) rather than string-formatting values directly into SQL
    is what prevents SQL injection -- this is the actual safety
    mechanism behind every tool below.
    """
    with sql.connect(
        server_hostname=DATABRICKS_SERVER_HOSTNAME,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


@mcp.tool()
def get_sales_by_category(category: str) -> list[dict]:
    query = """
        SELECT category, total_orders, total_line_items, total_revenue, avg_item_price
        FROM workspace.gold.sales_by_category
        WHERE category = ?
    """
    return run_query(query, (category,))


@mcp.tool()
def get_top_categories(limit: int = 5) -> list[dict]:
    query = """
        SELECT category, total_orders, total_revenue, avg_item_price
        FROM workspace.gold.sales_by_category
        ORDER BY total_revenue DESC
        LIMIT ?
    """
    return run_query(query, (limit,))


@mcp.tool()
def get_top_products(limit: int = 10, category: str = None) -> list[dict]:
    if category:
        query = """
            SELECT product_id, category, total_orders, total_revenue, avg_price
            FROM workspace.gold.top_products
            WHERE category = ?
            ORDER BY total_revenue DESC
            LIMIT ?
        """
        return run_query(query, (category, limit))
    else:
        query = """
            SELECT product_id, category, total_orders, total_revenue, avg_price
            FROM workspace.gold.top_products
            ORDER BY total_revenue DESC
            LIMIT ?
        """
        return run_query(query, (limit,))


if __name__ == "__main__":
    mcp.run()