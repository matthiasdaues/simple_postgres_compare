# This module provides a utility function to execute an aiosql query that returns JSON data,
# parse the result, and merge it into a target dictionary. It is intended for use with
# psycopg2 database connections and aiosql query functions, enabling seamless ingestion
# and aggregation of JSON-formatted query results for further processing or analysis.

import json

def execute_and_merge_json(connection, query_func, target_dict):
    """
    Execute aiosql query that returns JSON and merge result into target dictionary.
    
    Args:
        connection: psycopg2 connection object
        query_func: aiosql query function
        target_dict: dictionary to update with the JSON result
    
    Returns:
        dict: the updated target_dict
    """
    cursor = connection.cursor()
    cursor.execute(query_func.sql)
    result = cursor.fetchone()[0]
    cursor.close()
    
    # Parse JSON if it's a string, otherwise use as-is
    if isinstance(result, str):
        json_data = json.loads(result)
    else:
        json_data = result
    
    # Deep merge into target dictionary
    return deep_merge_json(target_dict, json_data)

def deep_merge_json(target_dict, source_dict):
    """
    Deep merge source dictionary into target dictionary.
    """
    for key, value in source_dict.items():
        if key in target_dict:
            if isinstance(target_dict[key], dict) and isinstance(value, dict):
                deep_merge_json(target_dict[key], value)
            else:
                target_dict[key] = value
        else:
            target_dict[key] = value
    
    return target_dict

def execute_comparison_queries(connection, queries_object, target_dict):
    """
    Execute all available queries from queries.transactional_sql.compare_db_instances.
    
    Args:
        connection: psycopg2 connection
        queries_object: root aiosql queries object
        target_dict: dictionary to merge results into
        
    Returns:
        dict: updated target_dict with all query results merged
    """
    # Navigate to the comparison queries
    comparison_queries = queries_object.transactional_sql.compare_db_instances
    
    # Get all available query names
    all_queries = [q for q in dir(comparison_queries) if not q.startswith('_') and not q.startswith('load_from_') and not q.endswith('cursor') and not q.startswith('add') and callable(getattr(comparison_queries, q))]
    
    print(f"Executing {len(all_queries)} comparison queries: {all_queries}")
    
    for query_name in all_queries:
        try:
            query_func = getattr(comparison_queries, query_name)
            print(f"Executing query: {query_name}")
            execute_and_merge_json(connection, query_func, target_dict)
        except Exception as e:
            print(f"Error executing query {query_name}: {e}")
            continue
    
    return target_dict

# # Usage:
# database_structure = {}
# execute_all_comparison_queries(conn, queries, database_structure)