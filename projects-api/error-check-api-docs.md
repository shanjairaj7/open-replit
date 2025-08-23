# Error Check API Documentation

## Endpoint: `GET /api/projects/{project_id}/error-check`

This endpoint runs comprehensive error checks for both backend (Python) and frontend (TypeScript) simultaneously for a given project.

### Parameters

- `project_id` (path parameter): The unique identifier of the project to check

### Response Format

```json
{
    "project_id": "string",
    "timestamp": "ISO datetime string",
    "backend": {
        "exists": boolean,
        "errors": "string (error output)",
        "status": {
            "executed": boolean,
            "success": boolean,
            "error": "string or null"
        },
        "error_count": number
    },
    "frontend": {
        "exists": boolean,
        "errors": "string (error output)",
        "status": {
            "executed": boolean,
            "success": boolean,
            "error": "string or null"
        },
        "error_count": number
    },
    "summary": {
        "total_errors": number,
        "backend_has_errors": boolean,
        "frontend_has_errors": boolean,
        "overall_status": "string"
    }
}
```

### Overall Status Values

- `"clean"` - No errors found in either backend or frontend
- `"backend_has_errors"` - Only backend has errors
- `"frontend_has_errors"` - Only frontend has errors  
- `"both_have_errors"` - Both backend and frontend have errors
- `"unknown"` - Status could not be determined
- `"check_failed"` - The error checking process failed

### Example Usage

#### cURL
```bash
curl -X GET "http://localhost:8000/api/projects/my-project-123/error-check"
```

#### Python
```python
import requests

response = requests.get("http://localhost:8000/api/projects/my-project-123/error-check")
data = response.json()

print(f"Total errors: {data['summary']['total_errors']}")
print(f"Status: {data['summary']['overall_status']}")
```

#### JavaScript
```javascript
fetch('http://localhost:8000/api/projects/my-project-123/error-check')
  .then(response => response.json())
  .then(data => {
    console.log(`Total errors: ${data.summary.total_errors}`);
    console.log(`Status: ${data.summary.overall_status}`);
  });
```

### Error Checking Details

#### Backend (Python)
- Uses the existing `_run_python_error_check` method
- Checks for Python syntax errors, import errors, etc.
- Supports virtual environment detection
- Runs with timeout to prevent hanging

#### Frontend (TypeScript)  
- Uses the existing `_run_typescript_error_check` method
- Runs `npx tsc --noEmit` for type checking
- Parses TypeScript compiler output
- Runs with timeout to prevent hanging

### HTTP Status Codes

- `200 OK` - Error check completed successfully (even if errors were found)
- `404 Not Found` - Project with given ID does not exist
- `500 Internal Server Error` - Server error during processing

### Performance Notes

- Both backend and frontend checks run **simultaneously** using asyncio
- Typical response time: 5-30 seconds depending on project size
- Timeout protection prevents hanging requests
- Results include detailed error counts and status information

### Test Script

A test script is provided at `test_error_check.py`:

```bash
python test_error_check.py my-project-123
```