{{
    config(
        materialized='table'
    )
}}

-- Gold model: top products by total revenue, joined with category
-- for context. Answers a different business question than
-- sales_by_category -- this is product-level, not category-level.

select
    product_id,
    product_category_name as category,
    count(distinct order_id) as total_orders,
    round(sum(price), 2) as total_revenue,
    round(avg(price), 2) as avg_price

from {{ source('silver', 'silver_orders_items_products') }}

where product_id is not null

group by product_id, product_category_name
order by total_revenue desc