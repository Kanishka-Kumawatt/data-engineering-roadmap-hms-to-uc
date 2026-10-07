# Interview Questions by Topic

**How to practise:** Answer out loud in under 2 minutes, using **Concept → Example from my project/capstone → Trade-off**. ⭐ marks questions that come up very often.

## Fundamentals
1. ⭐ What does a Data Engineer do?
2. ⭐ Data lake vs data warehouse vs lakehouse?
3. ⭐ ETL vs ELT? Why is ELT common on Databricks?
4. OLTP vs OLAP?
5. ⭐ Explain the medallion architecture.
6. Batch vs streaming: when would you choose each?
7. Structured vs semi-structured vs unstructured data, and how do you handle each?

## SQL
8. ⭐ WHERE vs HAVING?
9. ⭐ ROW_NUMBER vs RANK vs DENSE_RANK?
10. ⭐ How do you find and remove duplicates, keeping the latest?
11. Find records in A not in B (three ways).
12. Why does `NOT IN` with NULLs return nothing?
13. A LEFT JOIN returned fewer rows than the left table. Why?
14. ⭐ How do you prove two tables are identical?
15. Running totals / moving averages with window functions.
16. How do you approach debugging a 300-line SQL query?
17. Second-highest value per group.

## Python
18. List vs tuple vs set vs dict, with DE use cases.
19. ⭐ How do you handle exceptions in a pipeline? Fail fast or continue?
20. How do you manage configuration across environments?
21. How do you make code reusable across notebooks?
22. How would you call a paginated, rate-limited API reliably?
23. What's wrong with mutable default arguments?

## Spark
24. ⭐ Explain Spark architecture.
25. ⭐ Lazy evaluation: what and why?
26. ⭐ Narrow vs wide transformations; what causes a shuffle?
27. Job vs stage vs task.
28. repartition vs coalesce?
29. ⭐ Broadcast join: how does it work, and when does it fail?
30. ⭐ What is data skew, and how do you fix it?
31. What does AQE do?
32. Cache: when does it help, and when does it hurt?
33. ⭐ Executor OOM: how do you investigate?
34. Why avoid Python UDFs?
35. DataFrame vs RDD?

## Databricks
36. ⭐ All-purpose vs job vs serverless compute?
37. ⭐ Which access modes support Unity Catalog, and why?
38. How do you parameterise notebooks/jobs?
39. How are secrets managed?
40. How do you debug and recover a failed multi-task job?
41. What are system tables, and how have you used them?
42. What are Databricks Asset Bundles?

## Delta Lake
43. ⭐ What is Delta Lake, and how does it give ACID on object storage?
44. What's in `_delta_log`?
45. ⭐ Schema enforcement vs evolution?
46. ⭐ How does MERGE work? Common failure?
47. ⭐ OPTIMIZE vs VACUUM? What does VACUUM do to time travel?
48. Partitioning vs Z-ORDER vs liquid clustering?
49. DEEP vs SHALLOW CLONE?
50. ⭐ How do you implement SCD Type 2?
51. Change Data Feed: what is it for?

## Unity Catalog & HMS → UC migration
52. ⭐ What is the Hive Metastore? What does it store?
53. ⭐ What is Unity Catalog, and how is it different from HMS?
54. ⭐ Why migrate from HMS to UC?
55. Explain the UC object hierarchy.
56. ⭐ Managed vs external tables in UC: what happens on DROP?
57. ⭐ Storage credential vs external location?
58. ⭐ A user has SELECT but gets permission denied. Why?
59. Why should owners be groups?
60. ⭐ How do you migrate an external Delta table? A managed DBFS-root table? A Parquet table?
61. What does SYNC do, and what are its limitations?
62. DEEP CLONE vs CTAS for migration: history, cost, rollback?
63. ⭐ How do you validate a migration?
64. How do you handle views and their dependencies?
65. What code changes does UC usually require?
66. ⭐ What's your rollback plan?
67. How do you find remaining HMS usage after cutover?
68. What is UCX?
69. How do mounts translate into UC?
70. Workspace-local groups vs account groups?
71. ⭐ Tell me about a migration problem you solved. *(Prepare a STAR story from your project.)*

## Pipeline development
72. ⭐ Walk me through building a pipeline from a business requirement.
73. ⭐ How do you handle late-arriving data?
74. ⭐ How do you make a pipeline idempotent?
75. How do you handle bad records?
76. Full vs incremental loads?
77. How do you backfill safely?
78. What do you monitor beyond job success?

## Data modeling
79. ⭐ Fact vs dimension? What is grain?
80. Star vs snowflake?
81. Surrogate vs business keys?
82. SCD types 0/1/2/3?
83. Late-arriving dimensions?

## Git & practices
84. Merge vs rebase?
85. ⭐ What makes a good PR?
86. How do you resolve a merge conflict?
87. ⭐ You committed a secret. What now?
88. How do you structure a Databricks project repo?

## Testing & DQ
89. ⭐ How do you test PySpark code?
90. ⭐ Which DQ checks would you add to a new fact table?
91. Fail vs quarantine vs warn: how do you decide?
92. A job succeeded but the data is wrong. How could you have caught it?
93. Comparing very large tables efficiently?

## CI/CD
94. ⭐ CI vs CD for data pipelines?
95. How do you deploy across dev/qa/prod?
96. How do you manage secrets in CI/CD?
97. Rolling back code vs rolling back data?
98. Why run prod jobs as service principals?

## Performance
99. ⭐ A 10-minute job now takes an hour. Walk me through your investigation.
100. Small files: causes and fixes?
101. How do you optimise a slow MERGE?
102. How do you read the Spark UI to find a bottleneck?

## Troubleshooting & behavioural
103. ⭐ Walk me through how you debug a failed pipeline.
104. ⭐ A stakeholder says "the numbers are wrong". What do you do?
105. Tell me about a production incident you handled.
106. Tell me about a time you disagreed with a technical decision.
107. How do you prioritise when several things break at once?
108. How do you explain a technical problem to a non-technical stakeholder?
109. What did you learn from your migration project?
110. What would you do differently in your capstone?
