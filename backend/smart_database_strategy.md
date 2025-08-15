# Smart Database Strategy for AI Coder Projects

## Core Philosophy: Start Simple, Scale Smart

### **Tier 1: SQLite (Default for all new projects)**
- **Cost**: $0
- **Setup**: Instant
- **Model Knowledge**: Excellent (simple SQL)
- **Use Case**: 95% of projects

### **Tier 2: PostgreSQL Schema Isolation**  
- **Cost**: One shared PostgreSQL instance
- **Setup**: Schema per project
- **Use Case**: Projects that need concurrent access

### **Tier 3: Dedicated Database**
- **Cost**: Per-project database
- **Use Case**: Production/enterprise projects

## Implementation Strategy

### 1. **Default Project Structure**
```
projects/
├── project-abc-123/
│   ├── frontend/
│   ├── backend/
│   │   ├── database.sqlite        # Auto-created
│   │   ├── models.py              # SQLAlchemy models
│   │   ├── database.py            # Connection logic
│   │   └── .env                   # DATABASE_URL=sqlite:///database.sqlite
│   └── db_config.json            # Database metadata
```

### 2. **Smart Environment Variables**
The AI model will always use these environment variables:
```bash
DATABASE_URL=sqlite:///./database.sqlite  # Start here
DATABASE_TYPE=sqlite                       # For model context
SQLALCHEMY_DATABASE_URL=sqlite:///./database.sqlite
```

### 3. **Upgrade Path**
When a project needs more power:
- Change `DATABASE_URL` to PostgreSQL
- Model uses same SQLAlchemy code
- Zero code changes needed

## Why This Works Best for Qwen3 Coder

### **SQLite Advantages for AI Models:**
1. **Simple Setup**: No server configuration
2. **File-based**: Easy to understand and debug
3. **Standard SQL**: Model knows it well
4. **Self-contained**: Perfect for isolated projects
5. **Zero Infrastructure**: No external dependencies

### **SQLAlchemy ORM Benefits:**
1. **Database Agnostic**: Same code works for SQLite → PostgreSQL
2. **Well-documented**: Lots of training data
3. **Pythonic**: Natural for Python backends
4. **Migration Support**: Alembic for schema changes

## Cost Analysis

| Solution | Small Project | Medium Project | Large Project |
|----------|---------------|----------------|---------------|
| SQLite Only | $0 | $0 | Limited |
| Hybrid (SQLite→PG) | $0 | ~$10/month | ~$50/month |
| MongoDB Atlas | $0 (free tier) | ~$57/month | ~$200/month |
| AWS RDS | ~$15/month | ~$100/month | ~$500/month |

**Winner: Hybrid SQLite → PostgreSQL**

## Infrastructure Management

### **Project Creation Flow:**
1. Create project directory
2. Initialize SQLite database
3. Generate database.py with SQLAlchemy
4. Create .env with DATABASE_URL
5. Model creates models, CRUD, API routes

### **Database Actions for AI Model:**
- `<action type="create_database_model" name="User">` - Create SQLAlchemy model
- `<action type="create_crud_operations" model="User">` - Generate CRUD
- `<action type="migrate_database">` - Run migrations
- `<action type="seed_database">` - Add sample data

## Model Integration Strategy

### **Prompting Strategy:**
```
SYSTEM: When creating backends, always use SQLAlchemy ORM with these patterns:
1. DATABASE_URL from environment (supports SQLite → PostgreSQL)  
2. Create models in models.py
3. Use dependency injection for database sessions
4. Generate CRUD operations
5. Add database routes to FastAPI

Your database connection is always: DATABASE_URL environment variable
Start with SQLite, but code should work with PostgreSQL too.
```

### **Code Templates for Model:**
The AI will always generate this structure:
```python
# database.py - Always the same pattern
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

This approach gives us:
✅ **Zero infrastructure cost** for 95% of projects  
✅ **Instant setup** - no waiting for database provisioning  
✅ **Perfect isolation** - each project is completely separate  
✅ **Easy scaling** - upgrade path when needed  
✅ **Model-friendly** - simple patterns that AI understands well  
✅ **Backup/restore** - just copy the .sqlite file  
✅ **Development-friendly** - easy to debug and inspect  