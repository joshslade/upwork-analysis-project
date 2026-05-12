with searches as (SELECT 
       scr.query,
       ser.job_id,
       MAX(scr.query_timestamp) query_timestamp
FROM public.scrape_requests scr
JOIN public.search_results ser 
    on ser.search_id = scr.search_id
GROUP BY
    scr.query,
    ser.job_id)
SELECT
    query,
    COUNT(job_id)
FROM
    searches
GROUP BY
    query
ORDER BY
    COUNT(job_id) desc;