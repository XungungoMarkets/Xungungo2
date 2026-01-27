"""
Test script to explore yfinance screen API functionality
"""

import yfinance as yf
import json

def test_predefined_query(query_name):
    """Test a predefined screener query"""
    print(f"\n{'='*60}")
    print(f"Testing predefined query: {query_name}")
    print(f"{'='*60}")
    
    try:
        result = yf.screen(query_name)
        print(f"\nType of result: {type(result)}")
        
        # Check if it's a pandas DataFrame
        if hasattr(result, 'to_dict'):
            print(f"Result is a DataFrame with shape: {result.shape}")
            print(f"\nColumns: {list(result.columns)}")
            print(f"\nFirst few rows:")
            print(result.head())
            
            # Convert to dictionary for JSON serialization
            result_dict = result.to_dict('records')
            print(f"\nSample first record (as dict):")
            print(json.dumps(result_dict[0] if result_dict else {}, indent=2, default=str))
        else:
            print(f"Result: {result}")
            
        return result
        
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return None

def test_custom_query():
    """Test a custom EquityQuery"""
    print(f"\n{'='*60}")
    print(f"Testing custom query")
    print(f"{'='*60}")
    
    try:
        from yfinance import EquityQuery
        
        # Create a simple custom query
        q = EquityQuery('and', [
            EquityQuery('gt', ['percentchange', 3]),
            EquityQuery('eq', ['region', 'us'])
        ])
        
        print(f"Query object: {q}")
        
        result = yf.screen(q, sortField='percentchange', sortAsc=True)
        print(f"\nType of result: {type(result)}")
        
        if hasattr(result, 'to_dict'):
            print(f"Result is a DataFrame with shape: {result.shape}")
            print(f"\nColumns: {list(result.columns)}")
            print(f"\nFirst few rows:")
            print(result.head())
        else:
            print(f"Result: {result}")
            
        return result
        
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None

def explore_predefined_queries():
    """List all available predefined queries"""
    print(f"\n{'='*60}")
    print(f"Available predefined screener queries:")
    print(f"{'='*60}")
    
    queries = yf.PREDEFINED_SCREENER_QUERIES
    for name, query_info in queries.items():
        print(f"\n{name}:")
        if isinstance(query_info, dict):
            print(f"  - Query: {query_info.get('query', 'N/A')}")
            print(f"  - Sort field: {query_info.get('sortField', 'N/A')}")
            print(f"  - Sort type: {query_info.get('sortType', 'N/A')}")
            print(f"  - Count: {query_info.get('count', 'N/A')}")
            print(f"  - Offset: {query_info.get('offset', 'N/A')}")

if __name__ == "__main__":
    # First, list all available predefined queries
    explore_predefined_queries()
    
    # Test a few predefined queries
    print("\n\n" + "="*60)
    print("TESTING PREDEFINED QUERIES")
    print("="*60)
    
    # Test 1: Day gainers
    test_predefined_query("day_gainers")
    
    # Test 2: Most actives
    test_predefined_query("most_actives")
    
    # Test 3: Small cap gainers
    test_predefined_query("small_cap_gainers")
    
    # Test custom query
    print("\n\n" + "="*60)
    print("TESTING CUSTOM QUERY")
    print("="*60)
    
    test_custom_query()
    
    print("\n\n" + "="*60)
    print("TESTING COMPLETE")
    print("="*60)