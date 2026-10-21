-- Run after provisioning a restricted sentinel_runtime LOGIN (no superuser/DDL).
GRANT USAGE ON SCHEMA sentinel TO sentinel_runtime;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA sentinel TO sentinel_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA sentinel TO sentinel_runtime;
CREATE POLICY runtime_access ON sentinel.observations TO sentinel_runtime USING (true) WITH CHECK (true);
CREATE POLICY runtime_access ON sentinel.incidents TO sentinel_runtime USING (true) WITH CHECK (true);
CREATE POLICY runtime_access ON sentinel.audit TO sentinel_runtime USING (true) WITH CHECK (true);
CREATE POLICY runtime_access ON sentinel.outbox TO sentinel_runtime USING (true) WITH CHECK (true);
