# Metabase Starter Queries

## Open tasks by priority

```sql
SELECT priority, COUNT(*) AS total
FROM tasks
WHERE status NOT IN ('done', 'archived')
GROUP BY priority
ORDER BY total DESC;
```

## Tasks due today or overdue

```sql
SELECT id, title, priority, status, due_date
FROM tasks
WHERE due_date IS NOT NULL
  AND due_date <= CURRENT_DATE
  AND status NOT IN ('done', 'archived')
ORDER BY due_date ASC, priority DESC;
```

## Content pipeline by stage

```sql
SELECT stage, COUNT(*) AS total
FROM content_items
GROUP BY stage
ORDER BY total DESC;
```

## New documents by day

```sql
SELECT DATE(created_at) AS day, COUNT(*) AS total
FROM documents
GROUP BY DATE(created_at)
ORDER BY day DESC;
```

## Trades by symbol

```sql
SELECT symbol,
       COUNT(*) AS trades,
       SUM(CASE WHEN side = 'buy' THEN quantity * price ELSE 0 END) AS gross_buys,
       SUM(CASE WHEN side = 'sell' THEN quantity * price ELSE 0 END) AS gross_sells
FROM trades
GROUP BY symbol
ORDER BY trades DESC, symbol;
```

## Venture workload

```sql
SELECT v.name AS venture,
       COUNT(t.id) AS task_count
FROM ventures v
LEFT JOIN tasks t ON t.venture_id = v.id
GROUP BY v.name
ORDER BY task_count DESC, venture;
```
