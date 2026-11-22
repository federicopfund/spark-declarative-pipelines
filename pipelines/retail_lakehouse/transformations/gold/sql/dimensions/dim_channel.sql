-- gold.dim_channel - dimension de canales de venta.
--
-- Grano: un canal. Lista cerrada: los canales los define el negocio, no los datos.
-- channel_code es el valor que traen los pedidos (orders.channel); channel_key es la clave del modelo.
-- La fila -1 es el miembro desconocido (pedidos con un canal que no esta en la lista).

CREATE MATERIALIZED VIEW dim_channel
COMMENT 'Sales channels. Grain: one channel. channel_key -1 = unknown.'
AS SELECT
  channel_key,
  channel_code,
  channel_name,
  channel_type,
  current_timestamp() AS _loaded_at
FROM VALUES
  ( 1, 'web',     'Web',         'Online'),
  ( 2, 'store',   'Tienda',      'Presencial'),
  (-1, 'unknown', 'Desconocido', 'Desconocido')
  AS channels(channel_key, channel_code, channel_name, channel_type);
