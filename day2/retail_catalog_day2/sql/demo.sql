-- Day 2 indexing demo (orchestrated by dashboard Run Demo):
-- 1) DROP INDEX IF EXISTS product_name_idx
-- 2) EXPLAIN ANALYZE SELECT ... WHERE product_name LIKE 'Vintage Leather Jacket%'
-- 3) CREATE INDEX product_name_idx ON products (product_name)
-- 4) EXPLAIN ANALYZE again (expect Index Scan / Bitmap Index Scan)
-- 5) Insert one demo SKU so catalog metrics change
SELECT
    COUNT(*) AS product_count,
    COUNT(*) FILTER (WHERE product_name LIKE 'Vintage Leather Jacket%') AS jacket_matches,
    ROUND(SUM(price)::numeric, 2) AS total_inventory_value,
    ROUND(AVG(price)::numeric, 2) AS avg_price
FROM products;
