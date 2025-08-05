# EU API Testing Script

This directory contains a standalone script to test and debug the EU Funding & Tenders Portal API specifically for finding open calls related to clean energy.

## Files

- `test_eu_api_calls.py` - Main testing script
- `README_API_TESTING.md` - This file

## Usage

### Basic Testing

```bash
python3 test_eu_api_calls.py
```

This will:
1. Make a basic search request for "clean energy"
2. Analyze the API response structure
3. Show status of found calls (Open/Closed)
4. Save the raw response to a JSON file for detailed analysis

### Advanced Testing

To run additional tests, edit the `test_eu_api_calls.py` file and uncomment these lines at the bottom:

```python
# Uncomment these lines to run additional tests:
print("\n2️⃣  Testing different search terms...")
tester.test_different_search_terms()

print("\n3️⃣  Testing advanced parameters...")
tester.test_advanced_parameters()
```

## What the Script Does

### 1. Basic Search Test
- Tests the EU API with basic parameters
- Shows request/response details
- Analyzes individual results
- Counts open vs closed calls

### 2. Response Analysis
- Extracts titles, identifiers, status codes
- Decodes status codes (31094502=Open, 31094503=Closed)
- Formats deadlines and checks if expired
- Shows programme periods

### 3. Different Search Terms Test
- Tests multiple energy-related keywords
- Compares result counts across terms
- Helps identify which terms work best

### 4. Advanced Parameters Test
- Tests different API parameter combinations
- Checks status filters, language filters, etc.
- Helps understand API capabilities

## Customization

You can modify the script to:

### Change Search Terms
```python
# In test_basic_search method
data = tester.test_basic_search("your search term", max_results=20)
```

### Add New Parameters
```python
# In the search_params dictionary
search_params = {
    "apiKey": self.api_key,
    "index": "opportunities",
    "text": search_term,
    "language": "en",
    "status": "31094502",  # Add status filter
    "programmePeriod": "2021 - 2027",  # Add period filter
    # Add more parameters here
}
```

### Change Request Method
```python
# Try GET instead of POST
response = requests.get(
    self.api_url,
    params=search_params,  # Use params instead of data
    timeout=15
)
```

### Add Custom Filtering
```python
# Add your own filtering logic in analyze_response method
def analyze_response(self, data: Dict[str, Any], search_term: str):
    results = data.get('results', [])
    
    # Your custom filtering logic here
    filtered_results = []
    for result in results:
        # Add your conditions
        if your_condition:
            filtered_results.append(result)
    
    # Process filtered results
```

## Common Issues & Solutions

### Issue: No Open Calls Found
**Cause**: API may return only historical data
**Solution**: 
- Try different search terms
- Check the official EU portal directly
- Modify status filtering logic

### Issue: API Returns 400/405 Errors
**Cause**: Incorrect request format or parameters
**Solution**:
- Check the `test_advanced_parameters()` method
- Try different parameter combinations
- Use GET instead of POST

### Issue: Timeout Errors
**Cause**: Slow API response
**Solution**:
- Increase timeout value
- Add retry logic
- Test during off-peak hours

## Output Files

The script creates JSON files with timestamps:
- `eu_api_response_[timestamp].json` - Raw API response for detailed analysis

## Next Steps

1. **Run the basic test** to see current API behavior
2. **Examine the JSON output** to understand response structure
3. **Modify search parameters** based on your needs
4. **Add custom filtering** for your specific use case
5. **Integrate successful approaches** back into the main application

## API Documentation

- EU Funding & Tenders Portal: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home
- Search API appears to use Elasticsearch-style queries
- Public API key: "SEDIA" (for open data access)

## Tips for Debugging

1. **Start simple** - Use basic text search first
2. **Check status codes** - Look for patterns in open vs closed calls
3. **Examine metadata** - Most useful data is in the metadata arrays
4. **Test different terms** - Some keywords may work better than others
5. **Save responses** - Keep JSON files for offline analysis 