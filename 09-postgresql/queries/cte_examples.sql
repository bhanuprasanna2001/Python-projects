-- ============================================================
-- Common Table Expressions (CTEs) Examples
-- ============================================================

-- Basic CTE
WITH active_users AS (
    SELECT id, username, email, created_at
    FROM users
    WHERE is_active = true
)
SELECT * FROM active_users
WHERE created_at > NOW() - INTERVAL '30 days';


-- Multiple CTEs
WITH 
monthly_sales AS (
    SELECT 
        DATE_TRUNC('month', order_date) AS month,
        SUM(total_amount) AS revenue,
        COUNT(*) AS order_count
    FROM orders
    GROUP BY DATE_TRUNC('month', order_date)
),
monthly_growth AS (
    SELECT 
        month,
        revenue,
        order_count,
        LAG(revenue) OVER (ORDER BY month) AS prev_revenue,
        revenue - LAG(revenue) OVER (ORDER BY month) AS growth
    FROM monthly_sales
)
SELECT 
    month,
    revenue,
    order_count,
    growth,
    ROUND(growth / NULLIF(prev_revenue, 0) * 100, 2) AS growth_percent
FROM monthly_growth
ORDER BY month;


-- Recursive CTE (hierarchical data)
WITH RECURSIVE category_tree AS (
    -- Base case: top-level categories
    SELECT 
        id, 
        name, 
        parent_id,
        1 AS level,
        name::text AS path
    FROM categories
    WHERE parent_id IS NULL
    
    UNION ALL
    
    -- Recursive case: child categories
    SELECT 
        c.id,
        c.name,
        c.parent_id,
        ct.level + 1,
        ct.path || ' > ' || c.name
    FROM categories c
    INNER JOIN category_tree ct ON c.parent_id = ct.id
)
SELECT * FROM category_tree
ORDER BY path;


-- CTE for deduplication
WITH ranked_records AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (
            PARTITION BY email 
            ORDER BY created_at DESC
        ) AS rn
    FROM users
)
SELECT * FROM ranked_records WHERE rn = 1;


-- ============================================================
-- Window Functions Examples
-- ============================================================

-- ROW_NUMBER: Assign unique sequential numbers
SELECT 
    id,
    name,
    category,
    price,
    ROW_NUMBER() OVER (ORDER BY price DESC) AS price_rank
FROM products;


-- RANK and DENSE_RANK
SELECT 
    id,
    name,
    category,
    price,
    RANK() OVER (PARTITION BY category ORDER BY price DESC) AS rank,
    DENSE_RANK() OVER (PARTITION BY category ORDER BY price DESC) AS dense_rank
FROM products;


-- LAG and LEAD: Access previous/next rows
SELECT 
    order_date,
    total_amount,
    LAG(total_amount) OVER (ORDER BY order_date) AS prev_day_sales,
    LEAD(total_amount) OVER (ORDER BY order_date) AS next_day_sales,
    total_amount - LAG(total_amount) OVER (ORDER BY order_date) AS daily_change
FROM daily_sales;


-- Running totals
SELECT 
    order_date,
    amount,
    SUM(amount) OVER (ORDER BY order_date) AS running_total,
    AVG(amount) OVER (ORDER BY order_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS moving_avg_7day
FROM orders;


-- FIRST_VALUE, LAST_VALUE
SELECT 
    category,
    name,
    price,
    FIRST_VALUE(name) OVER (PARTITION BY category ORDER BY price) AS cheapest,
    LAST_VALUE(name) OVER (
        PARTITION BY category 
        ORDER BY price
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS most_expensive
FROM products;


-- NTILE: Distribute rows into buckets
SELECT 
    name,
    price,
    NTILE(4) OVER (ORDER BY price) AS price_quartile
FROM products;


-- Percent rank
SELECT 
    name,
    price,
    PERCENT_RANK() OVER (ORDER BY price) AS percent_rank,
    CUME_DIST() OVER (ORDER BY price) AS cumulative_dist
FROM products;
