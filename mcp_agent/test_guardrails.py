"""
Guardrail tests for the Gold data MCP tools -- proving the tool
boundary is actually safe, not just convenient. These are the tests
that matter most for the "why parameterized queries, why not raw
SQL passthrough" story.
"""

from gold_data_server import get_sales_by_category

print("--- Test 1: SQL injection attempt ---")
injection_attempt = "'; DROP TABLE workspace.gold.sales_by_category; --"
result = get_sales_by_category(injection_attempt)
print(f"Result: {result}")
print(f"Expected: [] (empty list, no error, no damage)\n")

print("--- Test 2: Nonexistent category ---")
result = get_sales_by_category("this_category_does_not_exist")
print(f"Result: {result}")
print(f"Expected: [] (empty list, clean handling)\n")

print("--- Tests complete. Now verify the table still exists: ---")
print("Run in Databricks: SELECT COUNT(*) FROM workspace.gold.sales_by_category;")