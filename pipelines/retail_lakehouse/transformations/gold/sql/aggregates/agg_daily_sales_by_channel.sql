-- gold.agg_daily_sales_by_channel - ventas por dia y canal.
--
-- Grano: un dia x un canal. Se calcula desde fact_orders con dim_date y dim_channel.

CREATE MATERIALIZED VIEW agg_daily_sales_by_channel
COMMENT 'Sales per day and channel. Grain: one day x one channel. Derived from fact_orders.'
AS SELECT
  d.date            AS order_date,
  ch.channel_code   AS channel,
  count(*)          AS orders,
  sum(f.amount)     AS total_amount
FROM fact_orders f
JOIN dim_date d
  ON d.date_key = f.date_key
JOIN dim_channel ch
  ON ch.channel_key = f.channel_key
GROUP BY d.date, ch.channel_code;
