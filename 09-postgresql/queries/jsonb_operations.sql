-- ============================================================
-- JSONB Operations in PostgreSQL
-- ============================================================

-- Create table with JSONB column
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100),
    payload JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);


-- ============================================================
-- Inserting JSONB Data
-- ============================================================

INSERT INTO products (name, data) VALUES
('Laptop', '{"brand": "Dell", "specs": {"ram": 16, "storage": 512}, "tags": ["electronics", "computer"]}'),
('Phone', '{"brand": "Apple", "specs": {"ram": 8, "storage": 256}, "tags": ["electronics", "mobile"], "colors": ["black", "white"]}'),
('Headphones', '{"brand": "Sony", "specs": {"wireless": true, "noise_cancelling": true}, "tags": ["audio", "electronics"]}');


-- ============================================================
-- Querying JSONB Data
-- ============================================================

-- Extract value as JSONB (->)
SELECT name, data->'brand' AS brand_json FROM products;

-- Extract value as text (->>)
SELECT name, data->>'brand' AS brand_text FROM products;

-- Nested access
SELECT name, data->'specs'->>'ram' AS ram FROM products;

-- Path access (#> and #>>)
SELECT name, data #>> '{specs, ram}' AS ram FROM products;


-- ============================================================
-- Filtering with JSONB
-- ============================================================

-- Exact match on nested value
SELECT * FROM products 
WHERE data->>'brand' = 'Dell';

-- Check if key exists
SELECT * FROM products 
WHERE data ? 'colors';

-- Check if any of keys exist
SELECT * FROM products 
WHERE data ?| array['colors', 'sizes'];

-- Check if all keys exist
SELECT * FROM products 
WHERE data ?& array['brand', 'specs'];

-- Contains operator (@>)
SELECT * FROM products 
WHERE data @> '{"brand": "Apple"}';

-- Contained by (<@)
SELECT * FROM products 
WHERE '{"brand": "Dell", "specs": {"ram": 16}}'::jsonb @> data->'specs';

-- Array contains value
SELECT * FROM products 
WHERE data->'tags' ? 'mobile';


-- ============================================================
-- Modifying JSONB Data
-- ============================================================

-- Set/update a key (jsonb_set)
UPDATE products 
SET data = jsonb_set(data, '{price}', '999.99')
WHERE name = 'Laptop';

-- Add/update nested key
UPDATE products 
SET data = jsonb_set(data, '{specs, cpu}', '"Intel i7"')
WHERE name = 'Laptop';

-- Remove a key
UPDATE products 
SET data = data - 'colors'
WHERE name = 'Phone';

-- Remove nested key
UPDATE products 
SET data = data #- '{specs, wireless}'
WHERE name = 'Headphones';

-- Append to array
UPDATE products 
SET data = jsonb_set(
    data, 
    '{tags}', 
    data->'tags' || '"new_tag"'::jsonb
)
WHERE name = 'Laptop';

-- Merge objects (||)
UPDATE products 
SET data = data || '{"sale": true, "discount": 10}'::jsonb
WHERE name = 'Phone';


-- ============================================================
-- JSONB Aggregation Functions
-- ============================================================

-- Build object from rows
SELECT jsonb_object_agg(name, data->'brand') AS brands
FROM products;

-- Build array from rows
SELECT jsonb_agg(data->'brand') AS all_brands
FROM products;

-- Build array with full objects
SELECT jsonb_agg(
    jsonb_build_object(
        'name', name,
        'brand', data->>'brand'
    )
) AS products_summary
FROM products;


-- ============================================================
-- JSONB Expansion Functions
-- ============================================================

-- Expand object to rows (each key-value pair)
SELECT 
    p.name,
    kv.key,
    kv.value
FROM products p,
     jsonb_each(p.data) AS kv
WHERE p.name = 'Laptop';

-- Expand object to text rows
SELECT 
    p.name,
    kv.key,
    kv.value
FROM products p,
     jsonb_each_text(p.data->'specs') AS kv;

-- Expand array to rows
SELECT 
    p.name,
    tag.value AS tag
FROM products p,
     jsonb_array_elements_text(p.data->'tags') AS tag;


-- ============================================================
-- JSONB Indexes for Performance
-- ============================================================

-- GIN index for containment queries (@>, ?, ?|, ?&)
CREATE INDEX idx_products_data_gin ON products USING GIN (data);

-- GIN index with jsonb_path_ops (smaller, only @>)
CREATE INDEX idx_products_data_path ON products USING GIN (data jsonb_path_ops);

-- Expression index for specific key
CREATE INDEX idx_products_brand ON products ((data->>'brand'));

-- Expression index for nested value
CREATE INDEX idx_products_ram ON products (((data->'specs'->>'ram')::int));


-- ============================================================
-- JSON Path Queries (PostgreSQL 12+)
-- ============================================================

-- Check path existence
SELECT * FROM products 
WHERE data @? '$.specs.ram';

-- Get values by path
SELECT jsonb_path_query(data, '$.specs.*') FROM products;

-- Filter with path predicate
SELECT * FROM products 
WHERE data @? '$.specs ? (@.ram > 8)';

-- Extract with filter
SELECT jsonb_path_query(data, '$.tags[*] ? (@ like_regex "elec")')
FROM products;


-- ============================================================
-- Complex Example: Event Analytics
-- ============================================================

-- Insert sample events
INSERT INTO events (event_type, payload, metadata) VALUES
('page_view', '{"page": "/home", "user_id": 1, "duration": 45}', '{"browser": "Chrome", "os": "Windows"}'),
('click', '{"element": "buy_button", "user_id": 1, "page": "/product/123"}', '{"browser": "Chrome"}'),
('page_view', '{"page": "/checkout", "user_id": 1, "duration": 120}', '{"browser": "Chrome"}'),
('purchase', '{"order_id": 456, "user_id": 1, "total": 99.99, "items": [{"id": 1, "qty": 2}]}', '{}');

-- Aggregate event data
SELECT 
    event_type,
    COUNT(*) as count,
    jsonb_agg(payload->'page') FILTER (WHERE payload ? 'page') as pages,
    AVG((payload->>'duration')::float) FILTER (WHERE payload ? 'duration') as avg_duration
FROM events
GROUP BY event_type;

-- Complex filtering
SELECT * FROM events
WHERE payload @> '{"user_id": 1}'
  AND metadata->>'browser' = 'Chrome'
  AND event_type = 'page_view';
