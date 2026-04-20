-- ===========================================================================
-- Silver: clickstream / customer activity events.
--
-- The source contains referential orphans (customer ids that never existed).
-- Rather than deleting them - which would quietly understate traffic - we keep
-- the event, null the broken key and flag it. The data-quality report counts
-- them; the funnel marts join on the flagged column and so stay correct.
-- ===========================================================================

DROP TABLE IF EXISTS silver.customer_events;
CREATE TABLE silver.customer_events AS
SELECT
    e.event_id,
    CASE WHEN c.customer_id IS NULL THEN NULL ELSE e.customer_id END AS customer_id,
    CASE WHEN c.customer_id IS NULL THEN TRUE ELSE FALSE END         AS is_orphan_customer,
    e.event_ts,
    CAST(e.event_ts AS DATE)                                         AS event_date,
    CAST(DATE_TRUNC('month', e.event_ts) AS DATE)                    AS event_month,
    CAST(EXTRACT(HOUR FROM e.event_ts) AS INTEGER)                   AS event_hour,
    LOWER(TRIM(e.event_type))                                        AS event_type,
    e.session_id,
    LOWER(TRIM(e.device))                                            AS device,
    CASE WHEN LOWER(TRIM(e.device)) IN ('ios', 'android') THEN 'Mobile'
         WHEN LOWER(TRIM(e.device)) = 'tablet'            THEN 'Tablet'
         ELSE 'Desktop' END                                          AS device_class,
    CAST(e.product_id AS INTEGER)                                    AS product_id,
    e.page_url,
    GREATEST(COALESCE(e.duration_seconds, 0), 0)                     AS duration_seconds,
    -- Funnel stage ordering, used by the conversion-funnel mart.
    CASE LOWER(TRIM(e.event_type))
        WHEN 'app_open'         THEN 1
        WHEN 'page_view'        THEN 2
        WHEN 'search'           THEN 3
        WHEN 'product_view'     THEN 4
        WHEN 'add_to_cart'      THEN 5
        WHEN 'checkout_start'   THEN 6
        WHEN 'purchase'         THEN 7
        ELSE 0
    END                                                              AS funnel_step
FROM (
    SELECT b.*, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY _loaded_at DESC) AS _rn
    FROM bronze.customer_events b
    WHERE event_id IS NOT NULL AND event_ts IS NOT NULL
) e
LEFT JOIN silver.customers c ON c.customer_id = e.customer_id
WHERE e._rn = 1;
