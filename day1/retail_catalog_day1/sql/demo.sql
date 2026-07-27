-- Demo mutation: bump prices and add one new SKU (executed dynamically by dashboard)
-- UPDATE products SET price = ROUND(price + 1.00, 2);
-- INSERT INTO products (name, description, price) VALUES (...);
SELECT COUNT(*) AS product_count,
       ROUND(SUM(price)::numeric, 2) AS total_inventory_value,
       ROUND(AVG(price)::numeric, 2) AS avg_price,
       ROUND(MIN(price)::numeric, 2) AS min_price,
       ROUND(MAX(price)::numeric, 2) AS max_price
FROM products;
