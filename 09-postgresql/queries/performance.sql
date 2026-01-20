-- ============================================================
-- PostgreSQL Performance Optimization
-- ============================================================

-- ============================================================
-- EXPLAIN ANALYZE: Query Analysis
-- ============================================================

-- Basic explain
EXPLAIN SELECT * FROM orders WHERE total_amount > 100;

-- Explain with execution stats
EXPLAIN ANALYZE SELECT * FROM orders WHERE total_amount > 100;

-- Detailed explain with buffers
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) 
SELECT * FROM orders WHERE total_amount > 100;

-- JSON format for programmatic analysis
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT o.*, c.name 
FROM orders o
JOIN customers c ON o.customer_id = c.id
WHERE o.total_amount > 100;


-- ============================================================
-- Index Types and Creation
-- ============================================================

-- B-tree index (default, good for equality and range)
CREATE INDEX idx_orders_date ON orders (order_date);

-- Composite index
CREATE INDEX idx_orders_customer_date ON orders (customer_id, order_date DESC);

-- Partial index (only indexes rows matching condition)
CREATE INDEX idx_orders_large ON orders (total_amount) 
WHERE total_amount > 1000;

-- Unique index
CREATE UNIQUE INDEX idx_users_email ON users (LOWER(email));

-- Expression index
CREATE INDEX idx_orders_year ON orders (EXTRACT(YEAR FROM order_date));

-- Covering index (includes additional columns)
CREATE INDEX idx_orders_covering ON orders (customer_id) 
INCLUDE (total_amount, order_date);

-- GIN index for array columns
CREATE INDEX idx_products_tags ON products USING GIN (tags);

-- GIN index for full-text search
CREATE INDEX idx_articles_search ON articles 
USING GIN (to_tsvector('english', title || ' ' || content));

-- BRIN index (for naturally ordered data)
CREATE INDEX idx_logs_created ON logs USING BRIN (created_at);

-- Hash index (only for equality, rarely better than B-tree)
CREATE INDEX idx_sessions_token ON sessions USING HASH (token);


-- ============================================================
-- Query Optimization Patterns
-- ============================================================

-- BAD: Using functions on indexed columns
SELECT * FROM users WHERE LOWER(email) = 'test@example.com';
-- GOOD: Create expression index or store normalized
SELECT * FROM users WHERE email_lower = 'test@example.com';

-- BAD: Leading wildcard prevents index use
SELECT * FROM products WHERE name LIKE '%phone%';
-- GOOD: Full-text search
SELECT * FROM products 
WHERE to_tsvector('english', name) @@ to_tsquery('phone');

-- BAD: OR conditions may not use indexes well
SELECT * FROM orders WHERE customer_id = 1 OR status = 'pending';
-- GOOD: UNION for separate index scans
SELECT * FROM orders WHERE customer_id = 1
UNION ALL
SELECT * FROM orders WHERE status = 'pending' AND customer_id != 1;

-- BAD: NOT IN with subquery
SELECT * FROM orders WHERE customer_id NOT IN (SELECT id FROM inactive_customers);
-- GOOD: NOT EXISTS or LEFT JOIN
SELECT o.* FROM orders o
LEFT JOIN inactive_customers ic ON o.customer_id = ic.id
WHERE ic.id IS NULL;


-- ============================================================
-- Table Statistics and Maintenance
-- ============================================================

-- Update table statistics
ANALYZE orders;
ANALYZE VERBOSE orders;

-- Vacuum and analyze
VACUUM ANALYZE orders;

-- Get table size info
SELECT 
    pg_size_pretty(pg_table_size('orders')) AS table_size,
    pg_size_pretty(pg_indexes_size('orders')) AS indexes_size,
    pg_size_pretty(pg_total_relation_size('orders')) AS total_size;

-- Get index usage stats
SELECT 
    indexrelname AS index_name,
    idx_scan AS scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- Find unused indexes
SELECT 
    indexrelname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND schemaname = 'public';


-- ============================================================
-- Partitioning for Large Tables
-- ============================================================

-- Range partitioning by date
CREATE TABLE orders_partitioned (
    id SERIAL,
    customer_id INT NOT NULL,
    order_date DATE NOT NULL,
    total_amount DECIMAL(10, 2),
    PRIMARY KEY (id, order_date)
) PARTITION BY RANGE (order_date);

-- Create partitions
CREATE TABLE orders_2024_q1 PARTITION OF orders_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');
    
CREATE TABLE orders_2024_q2 PARTITION OF orders_partitioned
    FOR VALUES FROM ('2024-04-01') TO ('2024-07-01');

CREATE TABLE orders_2024_q3 PARTITION OF orders_partitioned
    FOR VALUES FROM ('2024-07-01') TO ('2024-10-01');

CREATE TABLE orders_2024_q4 PARTITION OF orders_partitioned
    FOR VALUES FROM ('2024-10-01') TO ('2025-01-01');

-- Default partition for unmatched values
CREATE TABLE orders_default PARTITION OF orders_partitioned DEFAULT;

-- List partitioning
CREATE TABLE customers_regional (
    id SERIAL,
    name VARCHAR(255),
    region VARCHAR(50) NOT NULL,
    PRIMARY KEY (id, region)
) PARTITION BY LIST (region);

CREATE TABLE customers_na PARTITION OF customers_regional
    FOR VALUES IN ('US', 'CA', 'MX');

CREATE TABLE customers_eu PARTITION OF customers_regional
    FOR VALUES IN ('UK', 'DE', 'FR', 'IT');


-- ============================================================
-- Connection and Query Settings
-- ============================================================

-- Session-level settings for complex queries
SET work_mem = '256MB';  -- More memory for sorts/hashes
SET maintenance_work_mem = '512MB';  -- For VACUUM, CREATE INDEX
SET random_page_cost = 1.1;  -- SSD optimization (default 4.0)
SET effective_cache_size = '4GB';  -- OS cache hint

-- Check current settings
SHOW work_mem;
SHOW shared_buffers;

-- Reset to default
RESET work_mem;


-- ============================================================
-- Monitoring Active Queries
-- ============================================================

-- View active queries
SELECT 
    pid,
    usename,
    application_name,
    state,
    query_start,
    NOW() - query_start AS duration,
    LEFT(query, 100) AS query_preview
FROM pg_stat_activity
WHERE state != 'idle'
  AND pid != pg_backend_pid()
ORDER BY query_start;

-- Find long-running queries
SELECT 
    pid,
    NOW() - query_start AS duration,
    query
FROM pg_stat_activity
WHERE state = 'active'
  AND NOW() - query_start > INTERVAL '5 minutes';

-- Cancel a query (graceful)
SELECT pg_cancel_backend(12345);

-- Terminate a connection (forceful)
SELECT pg_terminate_backend(12345);


-- ============================================================
-- Lock Analysis
-- ============================================================

-- View current locks
SELECT 
    l.pid,
    l.locktype,
    l.mode,
    l.granted,
    a.usename,
    a.query
FROM pg_locks l
JOIN pg_stat_activity a ON l.pid = a.pid
WHERE l.relation IS NOT NULL;

-- Find blocking queries
SELECT 
    blocked.pid AS blocked_pid,
    blocked.query AS blocked_query,
    blocking.pid AS blocking_pid,
    blocking.query AS blocking_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_stat_activity blocked ON blocked.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks 
    ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.relation = blocked_locks.relation
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_stat_activity blocking ON blocking.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;


-- ============================================================
-- Common Performance Issues
-- ============================================================

-- 1. Missing indexes: Check seq scans on large tables
SELECT 
    schemaname,
    relname,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch
FROM pg_stat_user_tables
WHERE seq_scan > 0
ORDER BY seq_tup_read DESC
LIMIT 20;

-- 2. Table bloat: Check dead tuples
SELECT 
    relname,
    n_live_tup,
    n_dead_tup,
    ROUND(n_dead_tup::numeric / NULLIF(n_live_tup, 0) * 100, 2) AS dead_pct,
    last_vacuum,
    last_autovacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;

-- 3. Cache hit ratio (should be > 99%)
SELECT 
    sum(heap_blks_read) AS heap_read,
    sum(heap_blks_hit) AS heap_hit,
    ROUND(sum(heap_blks_hit) / NULLIF(sum(heap_blks_hit) + sum(heap_blks_read), 0) * 100, 2) AS cache_hit_ratio
FROM pg_statio_user_tables;
