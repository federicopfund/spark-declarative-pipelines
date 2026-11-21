-- gold.daily_sales_by_channel - ventas por dia y canal.

CREATE MATERIALIZED VIEW daily_sales_by_channel
COMMENT 'Sales per day and sales channel.'
AS SELECT
  order_date,
  channel,
  count(*)              AS orders,
  sum(amount)           AS total_amount
FROM orders_enriched
GROUP BY order_date, channel;
