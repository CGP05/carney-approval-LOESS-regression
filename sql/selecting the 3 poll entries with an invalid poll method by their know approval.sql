SELECT 
    Polling_firm,
    Last_date_of_polling,
    Approve,
    Disapprove,
    "Unsure/neither",
    Margin_of_error,
    Sample_size,
    Polling_method,
    Net_approval
FROM my_table
WHERE Approve IN ('45', '42', '41')
ORDER BY 
    CASE 
        WHEN Approve = '45' THEN 1
        WHEN Approve = '42' THEN 2
        WHEN Approve = '41' THEN 3
    END;