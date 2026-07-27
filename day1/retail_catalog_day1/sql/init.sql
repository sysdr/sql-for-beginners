-- Retail catalog schema + seed data (Day 1)
DROP TABLE IF EXISTS products;

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price NUMERIC(10, 2) NOT NULL CHECK (price > 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO products (name, description, price) VALUES
('Echo Dot (5th Gen)', 'Our best-sounding Echo Dot yet. Enjoy an improved audio experience.', 49.99),
('Fire TV Stick 4K Max', 'Stream over 1 million movies and TV episodes from Netflix, Prime Video.', 59.99),
('Kindle Paperwhite', 'Now with a 6.8" display and a battery life of up to 10 weeks.', 139.99);
