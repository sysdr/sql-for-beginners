-- Retail catalog schema + bulk seed (Day 2 — indexing)
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;

CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE
);

INSERT INTO categories (category_name) VALUES
    ('Electronics'),
    ('Apparel'),
    ('Home Goods');

CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    description TEXT,
    price NUMERIC(10, 2) NOT NULL CHECK (price > 0),
    stock_quantity INT NOT NULL DEFAULT 0,
    category_id INT REFERENCES categories(category_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Bulk insert via generate_series (fast; enough rows to show Seq Scan vs Index Scan)
INSERT INTO products (product_name, description, price, stock_quantity, category_id)
SELECT
    CASE
        WHEN g % 1000 = 0 THEN 'Vintage Leather Jacket - Model ' || lpad((g / 1000)::text, 3, '0')
        ELSE 'Product ' || lpad(g::text, 6, '0')
    END,
    'Description for product ' || g,
    ROUND(((g % 999) + 1 + ((g % 97) / 100.0))::numeric, 2),
    (g % 1000),
    CASE WHEN g % 1000 = 0 THEN 2 ELSE ((g % 3) + 1) END
FROM generate_series(1, 20000) AS g;

-- Intentionally NO index on product_name yet — created during indexing demo
ANALYZE products;
