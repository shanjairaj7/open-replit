"""
Database-specific prompts and patterns for the AI coder system
"""

DATABASE_SYSTEM_ADDITION = """

## DATABASE INTEGRATION (SQLite + SQLAlchemy)

**CRITICAL: Every backend application MUST use the database when data persistence is needed.**

### Database-First Development Pattern:

1. **ALWAYS start with database.py** - This file is already provided in your boilerplate
2. **Create SQLAlchemy ORM models** with `Base` inheritance
3. **Create Pydantic schemas** for API validation in the same model file
4. **Use dependency injection** with `Depends(get_db)` in services
5. **Call `create_tables()`** in every service file that uses the database

### Required Database Pattern:

```python
# models/item_models.py - ALWAYS follow this pattern
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from database import Base

# SQLAlchemy ORM Model (Database) - ALWAYS suffix with ORM
class ItemORM(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

# Pydantic Models (API) - ALWAYS create these schemas
class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None

class ItemCreate(ItemBase):
    pass

class ItemUpdate(ItemBase):
    name: Optional[str] = None

class ItemResponse(ItemBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

```python
# services/item_service.py - ALWAYS follow this pattern
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List
from models.item_models import ItemORM, ItemCreate, ItemUpdate, ItemResponse
from database import get_db, create_tables

# MANDATORY: Initialize tables
create_tables()

router = APIRouter(prefix="/items", tags=["items"])

@router.get("/", response_model=List[ItemResponse])
def get_items(db: Session = Depends(get_db)):
    items = db.query(ItemORM).order_by(ItemORM.created_at.desc()).all()
    return items

@router.post("/", response_model=ItemResponse)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = ItemORM(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
```

### When to Use Database vs Memory:

**✅ USE DATABASE for:**
- Todo items, tasks, notes
- User data, profiles
- Any data that should persist
- Lists that users create/modify
- Settings, preferences
- Any CRUD operations

**❌ DON'T use database for:**
- Static configuration
- Temporary UI state
- Real-time data that doesn't need persistence
- Cache-like data

### Database Integration Checklist:
- [ ] `database.py` exists and is imported
- [ ] SQLAlchemy ORM models inherit from `Base`
- [ ] Pydantic schemas are created for API
- [ ] `create_tables()` called in service
- [ ] Routes use `db: Session = Depends(get_db)`
- [ ] CRUD operations use SQLAlchemy queries
- [ ] Error handling for 404s implemented

### Common Database Patterns:

**Filtering and Pagination:**
```python
@router.get("/", response_model=List[ItemResponse])
def get_items(
    skip: int = 0,
    limit: int = 100, 
    completed: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(ItemORM)
    if completed is not None:
        query = query.filter(ItemORM.completed == completed)
    return query.offset(skip).limit(limit).all()
```

**Bulk Operations:**
```python
@router.post("/bulk/", response_model=List[ItemResponse])
def create_bulk_items(items: List[ItemCreate], db: Session = Depends(get_db)):
    db_items = [ItemORM(**item.dict()) for item in items]
    db.add_all(db_items)
    db.commit()
    for item in db_items:
        db.refresh(item)
    return db_items
```

**Statistics/Aggregations:**
```python
@router.get("/stats/")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(ItemORM).count()
    completed = db.query(ItemORM).filter(ItemORM.completed == True).count()
    return {"total": total, "completed": completed, "pending": total - completed}
```

### Requirements.txt Dependencies:
The boilerplate already includes:
- `sqlalchemy>=2.0.0` - ORM and database toolkit
- `alembic>=1.13.0` - Database migrations (for advanced use)

### Database File:
SQLite database will be created as `app_database.db` in the backend directory. This file contains all data and can be easily backed up or moved.

**Remember: Database integration is MANDATORY for any application that manages user data, todos, or persistent information. Always use the database instead of in-memory lists or dictionaries for data that needs to persist.**
"""