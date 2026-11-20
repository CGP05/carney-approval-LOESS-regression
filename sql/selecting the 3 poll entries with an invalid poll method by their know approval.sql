SELECT *
FROM carney_polls
WHERE Approve IN ('45', '42', '41')
ORDER BY 
    CASE Approve
        WHEN Approve = '45' THEN 1
        WHEN Approve = '42' THEN 2
        WHEN Approve = '41' THEN 3
    END;