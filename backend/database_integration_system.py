"""
Database Integration System for AI Coder
Extends the existing coder system to handle database operations
"""

import os
import json
import sqlite3
from pathlib import Path

class DatabaseIntegration:
    """
    Integration layer between AI coder and database management
    """
    
    def __init__(self, project_id: str, project_path: str):
        self.project_id = project_id
        self.project_path = Path(project_path)
        self.backend_path = self.project_path / "backend"
        self.db_path = self.backend_path / "database.sqlite"
        self.env_path = self.backend_path / ".env"
    
    def initialize_project_database(self):
        """Initialize database for a new project"""
        # Ensure backend directory exists
        self.backend_path.mkdir(parents=True, exist_ok=True)
        
        # Create SQLite database
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")  # Better concurrent access
        conn.close()
        
        # Update .env file with database URL
        self._update_env_file()
        
        return {
            "database_path": str(self.db_path),
            "database_url": f"sqlite:///{self.db_path}",
            "status": "initialized"
        }
    
    def _update_env_file(self):
        """Update .env file with database configuration"""
        env_content = []
        
        # Read existing .env if it exists
        if self.env_path.exists():
            with open(self.env_path, 'r') as f:
                env_content = f.readlines()
        
        # Remove existing database entries
        env_content = [line for line in env_content 
                      if not any(line.startswith(key) for key in 
                               ['DATABASE_URL=', 'DATABASE_TYPE=', 'SQLALCHEMY_DATABASE_URL='])]
        
        # Add database configuration
        env_content.extend([
            f"DATABASE_URL=sqlite:///{self.db_path}\n",
            f"DATABASE_TYPE=sqlite\n",
            f"SQLALCHEMY_DATABASE_URL=sqlite:///{self.db_path}\n"
        ])
        
        # Write back to .env
        with open(self.env_path, 'w') as f:
            f.writelines(env_content)

# Template code that the AI model should generate
DATABASE_CODE_TEMPLATES = {
    "database.py": '''"""
Database configuration and connection management
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./database.sqlite")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db():
    """Database dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)
''',
    
    "models.py": '''"""
Database models using SQLAlchemy
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    items = relationship("Item", back_populates="owner")

class Item(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="items")
''',
    
    "crud.py": '''"""
CRUD operations for database models
"""
from sqlalchemy.orm import Session
from . import models, schemas

def create_user(db: Session, user: schemas.UserCreate):
    """Create a new user"""
    db_user = models.User(email=user.email, username=user.username)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user(db: Session, user_id: int):
    """Get user by ID"""
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    """Get list of users"""
    return db.query(models.User).offset(skip).limit(limit).all()

def create_item(db: Session, item: schemas.ItemCreate, user_id: int):
    """Create a new item"""
    db_item = models.Item(**item.dict(), owner_id=user_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def get_items(db: Session, skip: int = 0, limit: int = 100):
    """Get list of items"""
    return db.query(models.Item).offset(skip).limit(limit).all()
''',
    
    "schemas.py": '''"""
Pydantic schemas for request/response models
"""
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class ItemBase(BaseModel):
    title: str
    description: Optional[str] = None

class ItemCreate(ItemBase):
    pass

class Item(ItemBase):
    id: int
    owner_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserBase(BaseModel):
    email: str
    username: str

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    items: List[Item] = []
    
    class Config:
        from_attributes = True
'''
}

def generate_database_prompts():
    """Generate prompts to add to the AI coder system"""
    return {
        "database_system_prompt": """
When creating backend applications, you should always implement database functionality using SQLAlchemy ORM with SQLite as the default database.

Database Setup Rules:
1. Always check for DATABASE_URL in environment variables
2. Use SQLite by default: "sqlite:///./database.sqlite"
3. Create models using SQLAlchemy declarative_base
4. Implement CRUD operations in separate crud.py file
5. Use Pydantic schemas for request/response models
6. Add database dependency injection to FastAPI routes

Standard Project Structure:
- database.py (connection and base)
- models.py (SQLAlchemy models)
- crud.py (database operations)
- schemas.py (Pydantic models)
- main.py (FastAPI app with database routes)

Always initialize database tables with: Base.metadata.create_all(bind=engine)
""",
        
        "database_action_prompt": """
Available database actions:
- <action type="init_database"/> - Initialize project database
- <action type="create_model" name="ModelName">model_definition</action>
- <action type="create_crud" model="ModelName"/> - Generate CRUD operations
- <action type="add_database_route" endpoint="/items">route_code</action>
"""
    }

# New interrupt handlers for database actions
def handle_database_interrupts():
    """Database-specific interrupt handlers to add to index_fixed.py"""
    return """
# Add these interrupt handlers to the existing coder system:

elif interrupt_action.get('type') == 'init_database':
    # Initialize database for project
    db_integration = DatabaseIntegration(self.project_id, self.project_path)
    result = db_integration.initialize_project_database()
    
    assistant_msg = {"role": "assistant", "content": accumulated_content}
    full_user_msg += f'''
<action_result type="init_database">
Database initialized successfully:
- Database path: {result['database_path']}
- Database URL: {result['database_url']}
- Environment variables updated

Next steps:
1. Create database models in models.py
2. Implement CRUD operations in crud.py  
3. Add database routes to your FastAPI app
4. Test with sample data
</action_result>
'''
    
    messages.append(assistant_msg)
    self.conversation_history.append(assistant_msg)
    continue

elif interrupt_action.get('type') == 'create_model':
    # Auto-generate SQLAlchemy model
    model_name = interrupt_action.get('name', 'DefaultModel')
    
    assistant_msg = {"role": "assistant", "content": accumulated_content}
    full_user_msg += f'''
<action_result type="create_model">
Please create the {model_name} model in models.py using SQLAlchemy.
Include appropriate fields, relationships, and constraints.
Don't forget to import it in __init__.py and update your CRUD operations.
</action_result>
'''
    
    messages.append(assistant_msg) 
    self.conversation_history.append(assistant_msg)
    continue
"""

if __name__ == "__main__":
    # Example usage
    db_integration = DatabaseIntegration("test-project", "/path/to/projects/test-project")
    result = db_integration.initialize_project_database()
    print("Database initialized:", result)