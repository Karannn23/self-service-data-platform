{{
    config(
        materialized='table'
    )
}}

-- Gold model: total sales, order count, and average order value
-- per product category. This answers a real business question
-- ("how are we doing by category") using data that's already
-- passed through Silver's validation checks.

select
    product_category_name as category,
    count(distinct order_id) as total_orders,
    count(*) as total_line_items,
    round(sum(price), 2) as total_revenue,
    round(avg(price), 2) as avg_item_price

from {{ source('silver', 'silver_orders_items_products') }}

where product_category_name is not null

group by product_category_name
order by total_revenue desc