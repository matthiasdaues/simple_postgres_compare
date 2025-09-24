---------------------------------------------------
-- 1) database level queries
---------------------------------------------------

-- name: a_01_database
-- returns the current database and its properties
select json_build_object(
        'database',
        json_build_object(
            'name',
            current_database(),
           'properties',
            row_to_json(t)
           )
       )
  from pg_database t
 where datname = current_database()
;


-- name: a_02_version
-- returns the PostgreSQL version
select json_build_object(
        'database',
        json_build_object(
            'version',     
            trim(substring(version(), 12, 5))
        )
       )
;


-- name: a_03_settings
-- returns current PostgreSQL settings
select json_build_object(
        'database',
        json_build_object(
            'settings', 
            json_object_agg(
                name, 
                row_to_json(t)
            )
       )
      )
 from (select * from pg_settings order by name) t
;

/*
-- name: a_04_casts
-- returns list of casts in the current database
select json_build_object(
        'database',
        json_build_object(
            'casts', 
            json_object_agg(
                oid, 
                row_to_json(t) 
            )
        )
       )
from pg_cast t
;
-- TODO: do later.
*/

-- name: a_05_event_triggers
-- returns list of event triggers in the current database
select json_build_object(
        'database',
        json_build_object(
            'event_triggers', 
            json_object_agg(
                evtname, 
                row_to_json(t) 
            )
        )
       )
from pg_event_trigger t
;

-- name: a_06_extensions
-- returns list of extensions in the current database
select json_build_object(
        'database',
        json_build_object(
            'extensions', 
            json_object_agg(
                extname, 
                row_to_json(t) 
            )
        )
       )
from pg_extension t
;

/*
-- name: a_07_foreign_data_wrappers
-- returns list of foreign data wrappers in the current database
select json_build_object(
        'database',
        json_build_object(
            'foreign_data_wrappers', 
            json_object_agg(
                oid, 
                row_to_json(t) 
            )
        )
       )
from pg_foreign_data_wrapper t
;

-- name: a_08_foreign_servers
-- returns list of foreign servers in the current database
select json_build_object(
        'database',
        json_build_object(
            'foreign_servers', 
            json_object_agg(
                oid, 
                row_to_json(t) 
            )
        )
     )
from pg_foreign_server t
;

-- name: a_09_foreign_tables
-- returns list of foreign tables in the current database
select json_build_object(
        'database',
        json_build_object(
            'foreign_tables', 
            json_object_agg(
                'oid', 
                row_to_json(t) 
            )
        )
       )
from pg_foreign_table t
;
*/

-- name: a_10_languages
-- returns list of languages in the current database
select json_build_object(
        'database',
        json_build_object(
            'languages', 
            json_object_agg(
                lanname, 
                row_to_json(t) 
            )
        )
       )
from pg_language t
;

-- name: a_11_publications
-- returns list of publications in the current database
select json_build_object(
        'database',
        json_build_object(
            'publications', 
            json_object_agg(
                pubname,
                row_to_json(t)
            )
        )
       )
from pg_publication t
;


-- name: a_12_schemas
-- returns list of non-system-schemas in the current database
select json_build_object(
        'database',
        json_build_object(
            'schemas', 
            json_object_agg(
                schema_name, 
                row_to_json(t) 
            )
        )
       )
  from information_schema.schemata t
 where schema_name not like '%time%'
   and schema_name not in ('information_schema', 'pg_catalog', 'pg_toast') 
;

-- name: a_13_roles
-- returns list of roles and users in the current database
select json_build_object(
        'database',
        json_build_object(
            'roles', 
            json_object_agg(
                rolname, 
                row_to_json(t) 
            )
        )
       )
  from pg_roles t
 where rolname not like 'pg_%'  -- exclude system roles
;



-- name: a_14_subscriptions
-- returns list of roles and users in the current database
with subscriptions as (
    select subname as subscription_name
         , subowner as owner_oid
         , r.rolname as owner_name
         , subenabled as is_enabled
         , subconninfo as connection_info
         , subslotname as slot_name
         , subsynccommit as sync_commit
         , subpublications as publications
      from pg_subscription s
      join pg_roles r on s.subowner = r.oid
     order by subname
)
select json_build_object(
        'database',
        json_build_object(
            'subscriptions', 
            json_object_agg(
                subscription_name, 
                row_to_json(t) 
            )
        )
       )
  from subscriptions t
 group by subscription_name
;

---------------------------------------------------
-- 2) schema level queries
---------------------------------------------------


-- name: b_09_functions
-- returns list of functions in the current database
with all_functions as (
    select n.nspname as schema_name
         , p.proname as function_name
         , r.rolname as function_owner
         , pg_get_function_arguments(p.oid) as input_arguments_types
         , case p.provolatile
            when 'i' then 'immutable'
            when 's' then 'stable'
            when 'v' then 'volatile'
           end as mutability_flag
      from pg_proc p
      join pg_roles r on p.proowner = r.oid
      join pg_namespace n on p.pronamespace = n.oid
     where n.nspname not in ('information_schema', 'pg_catalog', 'pg_toast')
       and n.nspname not like '%timescale%'
       and p.proname not like 'time%'
     order by n.nspname, p.proname
)
,   functions_by_schema as (
    select  schema_name
         ,  json_build_object(
                'functions',
                json_object_agg(
                    function_name,
                    row_to_json(t)
                )
            ) as functions_json
      from all_functions t
     group by t.schema_name
)
select json_build_object(
        'database',
        json_build_object(
            'schemas',
            json_object_agg(
                t.schema_name,
                t.functions_json
            )
        )
       )
 from functions_by_schema t
;

-- name: b_10_materialized_views
-- returns list of materialized views in the current database
with all_mat_views as (
    select *
      from pg_matviews
     where schemaname not in ('information_schema', 'pg_catalog', 'pg_toast')
     order by schemaname, matviewname
)
,   mat_views_by_schema as (
    select  schemaname
         ,  json_build_object(
                'materialized_views',
                json_object_agg(
                    matviewname,
                    row_to_json(t)
                )
            ) as mat_views_json
      from all_mat_views t
     group by t.schemaname
)
select json_build_object(
        'database',
        json_build_object(
            'schemas',
            json_object_agg(
                t.schemaname,
                t.mat_views_json
            )
        )
       )
 from mat_views_by_schema t
;

-- name: b_11_operators
-- returns list of operators in the current database
with all_operators as (
    select n.nspname as schema_name
         , o.oprname as operator_name
         , r.rolname as operator_owner
         , tl.typname as left_operand_type
         , tr.typname as right_operand_type
         , tres.typname as result_type
         , p.proname as function_name
      from pg_operator o
      join pg_namespace n on o.oprnamespace = n.oid
      join pg_roles r on o.oprowner = r.oid
      left join pg_type tl on o.oprleft = tl.oid
      left join pg_type tr on o.oprright = tr.oid
      left join pg_type tres on o.oprresult = tres.oid
      left join pg_proc p on o.oprcode = p.oid
     where n.nspname not in ('information_schema', 'pg_catalog', 'pg_toast')
     order by n.nspname, o.oprname
)
,   operators_by_schema as (
    select  schema_name
         ,  json_build_object(
                'operators',
                json_object_agg(
                    operator_name,
                    row_to_json(t)
                )
            ) as operators_json
      from all_operators t
     group by t.schema_name
)
select json_build_object(
        'database',
        json_build_object(
            'schemas',
            json_object_agg(
                t.schema_name,
                t.operators_json
            )
        )
       )
 from operators_by_schema t
;

-- name: b_12_procedures
-- returns list of procedures in the current database
with all_procedures as (
    select 
        n.nspname as schema_name,
        p.proname as procedure_name,
        r.rolname as procedure_owner,
        pg_get_function_arguments(p.oid) as arguments,
        l.lanname as language,
        p.prosrc as source_code,
        case p.provolatile
            when 'i' then 'immutable'
            when 's' then 'stable'
            when 'v' then 'volatile'
        end as volatility,
        case p.prosecdef
            when true then 'definer'
            else 'invoker'
        end as security
    from pg_proc p
    join pg_namespace n on p.pronamespace = n.oid
    join pg_roles r on p.proowner = r.oid
    join pg_language l on p.prolang = l.oid
    where p.prokind = 'p'  -- 'p' for procedures (postgresql 11+)
    and n.nspname not in ('information_schema', 'pg_catalog', 'pg_toast')
    order by n.nspname, p.proname
)
,   procedures_by_schema as (
    select  schema_name
         ,  json_build_object(
                'procedures',
                json_object_agg(
                    procedure_name,
                    row_to_json(t)
                )
            ) as procedures_json
      from all_procedures t
     group by t.schema_name
)
select json_build_object(
        'database',
        json_build_object(
            'schemas',
            json_object_agg(
                t.schema_name,
                t.procedures_json
            )
        )
       )
 from procedures_by_schema t
;

-- name: b_13_sequences
-- returns list of sequences in the current database
-- First, aggregate sequences within each schema
with sequences_by_schema as (
    select sequence_schema
         , json_object_agg(
            sequence_name,
            json_build_object(
                'sequence_name', sequence_name,
                'start_value', start_value,
                'minimum_value', minimum_value,
                'maximum_value', maximum_value,
                'increment', increment
            )
        ) as sequences_json
     from information_schema.sequences
    where sequence_schema not like '%timescale%'
    group by sequence_schema
)
-- then aggregate schemas
select json_build_object(
    'database',
    json_build_object(
        'schemas',
        json_object_agg(
            sequence_schema,
            json_build_object('sequences', sequences_json)
        )
    )
) as final_result
from sequences_by_schema;

-- name: b_14_trigger_functions
-- returns list of trigger functions in the current database
-- First, aggregate trigger functions within each schema
with all_trigger_functions as (
    select n.nspname as schema_name
         , p.proname as trigger_function_name
         , r.rolname as function_owner
         , pg_get_function_arguments(p.oid) as arguments
         , l.lanname as languages
         , p.prosrc as source_code
         , case p.prosecdef
            when true then 'definer'
            else 'invoker'
           end as security
      from pg_proc p
      join pg_namespace n on p.pronamespace = n.oid
      join pg_roles r on p.proowner = r.oid
      join pg_language l on p.prolang = l.oid
     where p.prorettype = (select oid from pg_type where typname = 'trigger')
       and n.nspname not in ('information_schema', 'pg_catalog', 'pg_toast')
     order by n.nspname, p.proname
)
,   trigger_functions_by_schema as (
    select  schema_name
         ,  json_build_object(
                'trigger_functions',
                json_object_agg(
                    trigger_function_name,
                    row_to_json(t)
                )
            ) as trigger_functions_json
      from all_trigger_functions t
     group by t.schema_name
)
select json_build_object(
        'database',
        json_build_object(
            'schemas',
            json_object_agg(
                t.schema_name,
                t.trigger_functions_json
            )
        )
       )
 from trigger_functions_by_schema t
;

-- name: b_15_types
-- returns list of types in the current database
-- First, aggregate types within each schema
with all_types as (
    select n.nspname as schema_name
         , t.typname as type_name
         , r.rolname as type_owner
         , case t.typtype
            when 'b' then 'base'
            when 'c' then 'composite'
            when 'd' then 'domain'
            when 'e' then 'enum'
            when 'p' then 'pseudo'
            when 'r' then 'range'
            when 'm' then 'multirange'
           end as type_category
         , case 
            when t.typtype = 'e' then (
                select array_to_string(array_agg(enumlabel order by enumsortorder), ', ')
                from pg_enum
                where enumtypid = t.oid
            )
            else null
           end as enum_values
         , pg_catalog.format_type(t.oid, null) as formatted_type
      from pg_type t
      join pg_namespace n on t.typnamespace = n.oid
      join pg_roles r on t.typowner = r.oid
     where t.typtype in ('b', 'd', 'e', 'r', 'm')
       and n.nspname not in ('information_schema', 'pg_catalog', 'pg_toast')
     order by n.nspname, t.typname
)
,   types_by_schema as (
    select  schema_name
         ,  json_build_object(
                'types',
                json_object_agg(
                    type_name,
                    row_to_json(t)
                )
            ) as types_json
      from all_types t
     group by t.schema_name
)
select json_build_object(
        'database',
        json_build_object(
            'schemas',
            json_object_agg(
                t.schema_name,
                t.types_json
            )
        )
       )
 from types_by_schema t
;

-- name: b_16_views
-- returns list of view in the current database
-- First, aggregate views within each schema
with all_views as (
    select n.nspname as schema_name
         , c.relname as view_name
         , r.rolname as view_owner
         , pg_get_viewdef(c.oid) as definition
      from pg_class c
      join pg_namespace n on c.relnamespace = n.oid
      join pg_roles r on c.relowner = r.oid
     where c.relkind = 'v'  -- 'v' for views
       and n.nspname not in ('information_schema', 'pg_catalog', 'pg_toast')
     order by n.nspname, c.relname
)
,   views_by_schema as (
    select  schema_name
         ,  json_build_object(
                'views',
                json_object_agg(
                    view_name,
                    row_to_json(t)
                )
            ) as views_json
      from all_views t
     group by t.schema_name
)
select json_build_object(
        'database',
        json_build_object(
            'schemas',
            json_object_agg(
                t.schema_name,
                t.views_json
            )
        )
       )
 from views_by_schema t
;


