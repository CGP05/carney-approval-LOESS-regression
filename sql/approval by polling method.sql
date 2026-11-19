SELECT 
    Polling_method,
    AVG(CAST(Replace(Approve, '%', '') AS REAL)) as avg_approval,
    COUNT(*) as poll_count
FROM carney_polls
GROUP BY Polling_method
ORDER BY poll_count DESC;