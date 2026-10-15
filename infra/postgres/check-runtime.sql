-- Run with migrator connection after every migration; failure blocks release.
DO $$
DECLARE bad boolean;
BEGIN
 SELECT rolsuper OR rolbypassrls OR rolcreatedb OR rolcreaterole OR rolreplication INTO bad FROM pg_roles WHERE rolname='capexly_runtime';
 IF bad IS DISTINCT FROM false THEN RAISE EXCEPTION 'Unsafe runtime attributes'; END IF;
 IF EXISTS (SELECT 1 FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member WHERE r.rolname='capexly_runtime') THEN RAISE EXCEPTION 'Runtime has role membership'; END IF;
 IF has_database_privilege('capexly_runtime','capexly','CREATE') OR has_database_privilege('capexly_runtime','capexly','TEMP') THEN RAISE EXCEPTION 'Runtime has database DDL/temp privilege'; END IF;
 IF has_schema_privilege('capexly_runtime','public','CREATE') THEN RAISE EXCEPTION 'Runtime can create schema objects'; END IF;
 IF EXISTS (SELECT 1 FROM pg_database d JOIN pg_roles r ON r.oid=d.datdba WHERE r.rolname='capexly_runtime') THEN RAISE EXCEPTION 'Runtime owns a database'; END IF;
 IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_roles r ON r.oid=c.relowner WHERE r.rolname='capexly_runtime') THEN RAISE EXCEPTION 'Runtime owns objects'; END IF;
 IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','p') AND EXISTS (SELECT 1 FROM (VALUES ('SELECT'),('INSERT'),('UPDATE'),('DELETE')) AS required(priv) WHERE NOT has_table_privilege('capexly_runtime',c.oid,required.priv))) THEN RAISE EXCEPTION 'Missing runtime table grants'; END IF;
 IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='S' AND NOT has_sequence_privilege('capexly_runtime',c.oid,'USAGE')) THEN RAISE EXCEPTION 'Missing runtime sequence grants'; END IF;
END $$;
SELECT rolname, rolsuper, rolbypassrls, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname IN ('capexly_runtime','capexly_migrator');
