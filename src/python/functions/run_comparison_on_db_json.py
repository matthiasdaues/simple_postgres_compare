# This module provides the compare_database_structures function, which recursively compares two
# hierarchical dictionaries representing database structures. It identifies keys and values that
# exist only in the source or target, as well as differences in values for matching keys. The function
# supports ignoring specified keys and produces a detailed summary of differences, making it useful
# for schema comparison, migration validation, and

def compare_database_structures(source_dict, target_dict, ignore_keys=None):
    """
    Compare two hierarchical database structure dictionaries.
    
    Args:
        source_dict: First database structure dictionary
        target_dict: Second database structure dictionary  
        ignore_keys: List of key strings to ignore during comparison
        
    Returns:
        dict: {
            'source_only': [...],  # List of paths only in source
            'target_only': [...],  # List of paths only in target
            'value_differences': [...],  # Different values for same keys
            'summary': {...}  # Count statistics
        }
    """
    return _compare_recursive(source_dict, target_dict, ignore_keys or [], "")

def _compare_recursive(source_dict, target_dict, ignore_keys, path):
    """
    Internal recursive function for comparing dictionaries.
    """
    result = {
        'source_only': [],
        'target_only': [],
        'value_differences': [],
        'summary': {
            'source_only_count': 0,
            'target_only_count': 0,
            'value_diff_count': 0
        }
    }
    
    # Find keys only in source
    source_only_keys = set(source_dict.keys()) - set(target_dict.keys())
    for key in source_only_keys:
        # Skip if key is integer or in ignore list
        if isinstance(key, int) or key in ignore_keys:
            continue
        current_path = f"{path}.{key}" if path else key
        result['source_only'].append(current_path)
        result['summary']['source_only_count'] += 1
    
    # Find keys only in target
    target_only_keys = set(target_dict.keys()) - set(source_dict.keys())
    for key in target_only_keys:
        # Skip if key is integer or in ignore list
        if isinstance(key, int) or key in ignore_keys:
            continue
        current_path = f"{path}.{key}" if path else key
        result['target_only'].append(current_path)
        result['summary']['target_only_count'] += 1
    
    # Compare common keys
    common_keys = set(source_dict.keys()) & set(target_dict.keys())
    for key in common_keys:
        # Skip if key is integer or in ignore list
        if isinstance(key, int) or key in ignore_keys:
            continue
        
        current_path = f"{path}.{key}" if path else key
        source_value = source_dict[key]
        target_value = target_dict[key]
        
        # Both are dictionaries - recurse
        if isinstance(source_value, dict) and isinstance(target_value, dict):
            nested_result = _compare_recursive(
                source_value, target_value, ignore_keys, current_path
            )
            
            # Merge nested results (lists now)
            result['source_only'].extend(nested_result['source_only'])
            result['target_only'].extend(nested_result['target_only'])
            result['value_differences'].extend(nested_result['value_differences'])
            
            result['summary']['source_only_count'] += nested_result['summary']['source_only_count']
            result['summary']['target_only_count'] += nested_result['summary']['target_only_count']
            result['summary']['value_diff_count'] += nested_result['summary']['value_diff_count']
        
        # Different values for same key
        elif source_value != target_value:
            result['value_differences'].append({
                'path': current_path,
                'source_value': source_value,
                'target_value': target_value
            })
            result['summary']['value_diff_count'] += 1
    
    return result

# # Usage example:
# comparison_result = compare_database_structures(
#     source_db_structure, 
#     target_db_structure, 
#     ignore_keys=['created_at', 'updated_at', 'oid']
# )

# Example output:
# {
#     'source_only': ['database.extensions.btree_gin', 'database.schemas.gigabeam_staging'],
#     'target_only': ['database.extensions.uuid-ossp'],
#     'value_differences': [
#         {'path': 'database.settings.max_connections', 'source_value': 100, 'target_value': 200}
#     ],
#     'summary': {'source_only_count': 2, 'target_only_count': 1, 'value_diff_count': 1}
# }