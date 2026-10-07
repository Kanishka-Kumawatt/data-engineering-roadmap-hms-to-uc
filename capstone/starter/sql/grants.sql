-- Grants as code: reviewed in PRs, applied identically to every environment.
-- ${catalog} is replaced at run time. Create the groups first (account console / SCIM), or edit the names
-- to groups that exist in your workspace. In Free Edition you may only be able to grant to `account users`.
--
-- Model:
--   grp_phoenix_engineers : build & operate (owner of schemas)
--   grp_phoenix_bi        : read Gold only
--   the job's run-as identity (service principal in qa/prod) : write bronze/silver/gold/ops

GRANT USE CATALOG ON CATALOG ${catalog} TO `grp_phoenix_bi`;
GRANT USE SCHEMA, SELECT ON SCHEMA ${catalog}.gold TO `grp_phoenix_bi`;

GRANT USE CATALOG ON CATALOG ${catalog} TO `grp_phoenix_engineers`;
GRANT USE SCHEMA, SELECT, MODIFY, CREATE TABLE ON SCHEMA ${catalog}.legacy TO `grp_phoenix_engineers`;

ALTER SCHEMA ${catalog}.legacy OWNER TO `grp_phoenix_engineers`;
ALTER SCHEMA ${catalog}.gold   OWNER TO `grp_phoenix_engineers`;
