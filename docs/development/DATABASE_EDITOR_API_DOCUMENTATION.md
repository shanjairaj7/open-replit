# Database Editor API Documentation

## Overview

The Streaming API provides comprehensive database management capabilities for deployed backends. This allows you to view, create, update, and delete data in your deployed backend databases through a centralized API interface.

## Database Structure

Each deployed backend uses a JSON-based database system where:
- **Tables** = JSON files containing arrays of records
- **Rows** = Individual record objects with key-value pairs
- **Columns** = Object keys (dynamic schema)
- **Auto-generated fields**: `id`, `created_at`, `updated_at`

## API Endpoints

### 1. Database Overview & Inspection

#### Get Complete Database Information
```http
GET /projects/{project_id}/backend/database/inspect
```

**Description**: Get an overview of all tables and their contents in the deployed backend database.

**Response Example**:
```json
{
  "status": "success",
  "project_id": "my-project-123",
  "backend_url": "https://user--app-name.modal.run",
  "database_inspection": {
    "database_path": "/root/json_data",
    "tables": {
      "users": [
        {"id": 1, "name": "John", "email": "john@example.com", "created_at": "2025-09-01T10:30:00"},
        {"id": 2, "name": "Jane", "email": "jane@example.com", "created_at": "2025-09-01T11:15:00"}
      ],
      "orders": [
        {"id": 1, "user_id": 1, "product": "Widget", "amount": 29.99, "created_at": "2025-09-01T12:00:00"}
      ]
    },
    "metadata": {
      "table_count": 2,
      "total_records": 3,
      "file_sizes": {
        "users": "256 bytes",
        "orders": "128 bytes"
      }
    }
  },
  "call_info": {
    "response_time_ms": 150,
    "called_at": "2025-09-01T06:30:00"
  }
}
```

### 2. Table Data Viewing

#### Get Specific Table Data
```http
GET /projects/{project_id}/backend/database/tables/{table_name}
```

**Description**: View data from a specific table in a structured format suitable for table display.

**Parameters**:
- `project_id`: Your project identifier
- `table_name`: Name of the table to view (e.g., "users", "orders")

**Response Example**:
```json
{
  "status": "success",
  "project_id": "my-project-123",
  "table_name": "users",
  "columns": ["id", "name", "email", "created_at"],
  "rows": [
    {"id": 1, "name": "John", "email": "john@example.com", "created_at": "2025-09-01T10:30:00"},
    {"id": 2, "name": "Jane", "email": "jane@example.com", "created_at": "2025-09-01T11:15:00"}
  ],
  "metadata": {
    "row_count": 2,
    "column_count": 4,
    "primary_key": "id"
  },
  "call_info": {
    "response_time_ms": 85,
    "backend_url": "https://user--app-name.modal.run"
  }
}
```

### 3. Table Data Management

#### Unified Table Operations
```http
POST /projects/{project_id}/backend/database/tables/{table_name}/manage
```

**Description**: Perform insert, update, or delete operations on table data.

**Request Body Format**:
```json
{
  "operation": "insert|update|delete",
  "data": { /* Record data for insert/update */ },
  "row_id": 123 /* Required for update/delete */
}
```

## Operation Examples

### Insert New Row

**Request**:
```http
POST /projects/my-project-123/backend/database/tables/users/manage
Content-Type: application/json

{
  "operation": "insert",
  "data": {
    "name": "Alice Smith",
    "email": "alice@example.com",
    "role": "admin"
  }
}
```

**Response**:
```json
{
  "status": "success",
  "operation": "insert",
  "table_name": "users",
  "affected_rows": 1,
  "data": {
    "id": 3,
    "name": "Alice Smith",
    "email": "alice@example.com",
    "role": "admin",
    "created_at": "2025-09-01T14:30:00"
  },
  "message": "Record inserted successfully into users",
  "project_id": "my-project-123",
  "call_info": {
    "response_time_ms": 120,
    "backend_url": "https://user--app-name.modal.run"
  }
}
```

### Update Existing Row

**Request**:
```http
POST /projects/my-project-123/backend/database/tables/users/manage
Content-Type: application/json

{
  "operation": "update",
  "row_id": 1,
  "data": {
    "email": "john.updated@example.com",
    "role": "moderator"
  }
}
```

**Response**:
```json
{
  "status": "success",
  "operation": "update",
  "table_name": "users",
  "affected_rows": 1,
  "data": {
    "id": 1,
    "name": "John",
    "email": "john.updated@example.com",
    "role": "moderator",
    "created_at": "2025-09-01T10:30:00",
    "updated_at": "2025-09-01T15:00:00"
  },
  "message": "Record 1 updated successfully in users",
  "project_id": "my-project-123",
  "call_info": {
    "response_time_ms": 95,
    "backend_url": "https://user--app-name.modal.run"
  }
}
```

### Delete Row

**Request**:
```http
POST /projects/my-project-123/backend/database/tables/users/manage
Content-Type: application/json

{
  "operation": "delete",
  "row_id": 2
}
```

**Response**:
```json
{
  "status": "success",
  "operation": "delete",
  "table_name": "users",
  "affected_rows": 1,
  "data": {
    "deleted_id": 2
  },
  "message": "Record 2 deleted successfully from users",
  "project_id": "my-project-123",
  "call_info": {
    "response_time_ms": 78,
    "backend_url": "https://user--app-name.modal.run"
  }
}
```

## Error Handling

### Common Error Scenarios

#### Backend Not Deployed
```json
{
  "status": "not_deployed",
  "message": "Backend not deployed yet - cannot perform insert",
  "project_id": "my-project-123",
  "table_name": "users",
  "operation": "insert",
  "suggestion": "Deploy the backend first using the deploy API endpoint"
}
```

#### Row Not Found (Update/Delete)
```json
{
  "status": "error",
  "operation": "update",
  "table_name": "users",
  "error": "Record with id 999 not found in users",
  "project_id": "my-project-123"
}
```

#### Missing Required Data
```json
{
  "status": "error",
  "error": "data is required for insert operation",
  "project_id": "my-project-123",
  "table_name": "users",
  "operation": "insert"
}
```

#### Backend Timeout
```json
{
  "status": "timeout",
  "error": "Table insert operation timed out",
  "project_id": "my-project-123",
  "table_name": "users",
  "operation": "insert",
  "suggestion": "Operation may be slow or backend unresponsive"
}
```

## Usage Workflow

### 1. View Database Overview
Start by calling the database inspection endpoint to see all available tables and their current data.

### 2. Select and View Table
Use the table-specific GET endpoint to view data in a structured format perfect for displaying in a table UI.

### 3. Perform Operations
Use the unified management endpoint to:
- **Insert**: Add new records with auto-generated IDs and timestamps
- **Update**: Modify existing records (partial updates supported)
- **Delete**: Remove records by ID

### 4. Automatic Features
- **Auto-generated IDs**: New records automatically get unique IDs
- **Timestamps**: `created_at` added on insert, `updated_at` added on update  
- **Cache Management**: View caches automatically cleared after modifications
- **Validation**: Required fields and data types are validated

## Performance & Caching

- **Read Operations**: Cached for 10 seconds to prevent backend overload
- **Write Operations**: Longer timeout (10s) for database modifications
- **Cache Invalidation**: Automatic after successful write operations
- **Error Recovery**: Detailed error messages with actionable suggestions

## Security Notes

- All internal database endpoints are **stealth APIs** (hidden from OpenAPI documentation)
- Operations go through the streaming API which handles authentication and project access
- Direct access to internal endpoints is not exposed publicly
- Each project's database is isolated and accessed through project-specific credentials

## Integration Examples

### Building a Table UI
1. Call `GET /projects/{id}/backend/database/tables/{table}` to get structured data
2. Display columns and rows in your UI
3. Use the management endpoint for user-initiated CRUD operations
4. Refresh the table view after successful operations

### Database Administration
1. Use the inspection endpoint to get a complete database overview
2. Iterate through tables to understand the data structure
3. Perform bulk operations by calling the management endpoint multiple times
4. Monitor operation success through detailed response messages

This API provides a complete SQL-like database editor experience while maintaining the simplicity of JSON-based storage and the security of stealth internal APIs.