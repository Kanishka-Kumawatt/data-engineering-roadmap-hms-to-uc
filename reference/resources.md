# Resources & Documentation

> Databricks reorganises its docs often. If a link moves, search the page title on docs.databricks.com. **Official docs beat blog posts** for UC behaviour and limitations.

## Must-read for your project (HMS → UC)
| Resource | Why |
|---|---|
| Databricks docs: **What is Unity Catalog?** (`docs.databricks.com` → Data governance → Unity Catalog) | Core concepts, object model |
| Databricks docs: **Upgrade Hive tables and views to Unity Catalog** | Official migration methods |
| Databricks docs: **SYNC** (SQL reference) | Options, dry run, limitations |
| Databricks docs: **Unity Catalog privileges and securable objects** | Privilege list, inheritance |
| Databricks docs: **External locations** and **Storage credentials** | Storage access model per cloud |
| Databricks docs: **Compute access modes** and **UC limitations on standard access mode** | Why legacy code breaks |
| Databricks docs: **Volumes** | Replacing DBFS/mount file access |
| Databricks docs: **Workspace-catalog binding** | Environment isolation |
| Databricks docs: **Hive metastore federation** | Gradual migration option |
| **UCX (Databricks Labs)**: https://github.com/databrickslabs/ucx (docs: https://databrickslabs.github.io/ucx/) | Assessment, group/table/code migration |
| Databricks docs: **System tables** (audit, lineage, billing, lakeflow) | Validation and monitoring |
| Databricks docs: **Row filters and column masks** | Fine-grained governance |

## Spark & Delta
| Resource | Notes |
|---|---|
| Apache Spark docs: https://spark.apache.org/docs/latest/ (SQL guide, Structured Streaming guide, tuning) | Reference |
| *Learning Spark, 2nd ed.* (Damji et al., O'Reilly; free PDF from Databricks) | The best intro book |
| *Spark: The Definitive Guide* (Chambers & Zaharia) | Deeper reference |
| Delta Lake docs: https://docs.delta.io/ | Protocol concepts, MERGE, CDF |
| *Delta Lake: The Definitive Guide* (O'Reilly) | Deeper reference |
| Databricks docs: **Spark UI** / **query profile** / **Optimization recommendations** | Phase 13 |
| Databricks docs: **Liquid clustering**, **Predictive optimization**, **Deletion vectors** | Modern layout |

## Databricks development
| Resource | Notes |
|---|---|
| Databricks **Free Edition** (databricks.com → Learn → Free Edition) | Your practice workspace |
| **Databricks Academy** (customer/partner learning paths, often free) | Data Engineer learning path |
| Databricks docs: **Lakeflow Jobs**, **Auto Loader**, **Lakeflow Declarative Pipelines** | Phase 5, 8, 15 |
| Databricks docs: **Databricks Asset Bundles** + `databricks bundle init` templates | Phase 12 |
| Databricks docs: **Git folders**, **Databricks Connect**, **VS Code extension** | IDE development |
| Databricks docs: **Secret management** | Phase 5 |
| Certification: **Databricks Certified Data Engineer Associate** → later **Professional** | Good after week 12–16 |

## SQL practice
- LeetCode "SQL 50" study plan; DataLemur; StrataScratch
- Mode SQL tutorial (beginner → advanced)
- `sqlfluff` docs (formatting/linting)

## Python
- Official Python tutorial (docs.python.org/3/tutorial), chapters 1–10
- *Automate the Boring Stuff with Python* (free online). Good for scripting fluency
- `pytest` docs (fixtures, parametrize); PySpark testing utilities (`pyspark.testing`)
- Real Python articles on logging, packaging and dataclasses

## Data engineering & modeling
- *Fundamentals of Data Engineering* (Reis & Housley). **Read this one first**
- *The Data Warehouse Toolkit* (Kimball & Ross). Dimensional modeling, chapters 1–6
- *Designing Data-Intensive Applications* (Kleppmann). Read after 3 months; it will change how you think

## Git & practices
- *Pro Git* (free): https://git-scm.com/book. Chapters 1–3
- Learn Git Branching (interactive): https://learngitbranching.js.org
- GitHub Actions docs (workflow syntax, environments, secrets)

## Cloud basics (pick your project's cloud)
- Azure: ADLS Gen2 overview, RBAC for storage, Access Connector for Azure Databricks
- AWS: S3 + IAM roles basics; UC storage credentials on AWS
- GCP: GCS + service accounts

## Communities
- Databricks Community forums; r/dataengineering; the Delta Lake Slack
- Data Engineering Weekly / Seattle Data Guy (newsletters/videos)
