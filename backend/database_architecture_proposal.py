"""
Database Architecture Proposal for AI Coder Projects
Hybrid approach: Start with SQLite, upgrade path to PostgreSQL
"""

import os
import sqlite3
from pathlib import Path
import json

class ProjectDatabaseManager:
    """
    Smart database management that starts simple and scales up
    """
    
    def __init__(self, project_id: str, projects_root: str = "projects"):
        self.project_id = project_id
        self.projects_root = Path(projects_root)
        self.project_path = self.projects_root / project_id
        self.db_config_path = self.project_path / "db_config.json"
        
    def initialize_database(self, db_type: str = "sqlite"):
        """
        Initialize database for a project
        
        Args:
            db_type: "sqlite" (default) or "postgresql"
        """
        self.project_path.mkdir(parents=True, exist_ok=True)
        
        if db_type == "sqlite":
            return self._setup_sqlite()
        elif db_type == "postgresql":
            return self._setup_postgresql()
        
    def _setup_sqlite(self):
        """Setup SQLite database for project"""
        db_path = self.project_path / "database.sqlite"
        
        # Create database connection
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign keys
        conn.close()
        
        # Save config
        config = {
            "type": "sqlite",
            "path": str(db_path),
            "connection_string": f"sqlite:///{db_path}",
            "created_at": "2025-01-11"
        }
        
        with open(self.db_config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        return config
    
    def _setup_postgresql(self):
        """Setup PostgreSQL schema for project"""
        # This would connect to shared PostgreSQL and create schema
        schema_name = f"project_{self.project_id.replace('-', '_')}"
        
        config = {
            "type": "postgresql", 
            "schema": schema_name,
            "connection_string": f"postgresql://user:pass@localhost:5432/main?options=-csearch_path%3D{schema_name}",
            "created_at": "2025-01-11"
        }
        
        with open(self.db_config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        return config
    
    def get_connection_info(self):
        """Get database connection info for project"""
        if self.db_config_path.exists():
            with open(self.db_config_path, 'r') as f:
                return json.load(f)
        return None
    
    def upgrade_to_postgresql(self):
        """Migrate from SQLite to PostgreSQL"""
        # Implementation for upgrading database
        pass

# Environment variable template for projects
DATABASE_ENV_TEMPLATE = """
# Database Configuration
DATABASE_TYPE={db_type}
DATABASE_URL={connection_string}
DATABASE_PATH={db_path}

# For SQLAlchemy
SQLALCHEMY_DATABASE_URL={connection_string}
"""

def generate_database_code_for_model():
    """
    Generate the exact code structure the AI model should create
    """
    return {
        "fastapi_database": '''
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./database.sqlite")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Example Model
class Item(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)

# Create tables
Base.metadata.create_all(bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
''',
        
        "crud_operations": '''
from sqlalchemy.orm import Session
from . import models, schemas

def create_item(db: Session, item: schemas.ItemCreate):
    db_item = models.Item(**item.dict())
    db.add(db_item)
    db.commit() 
    db.refresh(db_item)
    return db_item

def get_items(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Item).offset(skip).limit(limit).all()
''',
        
        "api_routes": '''
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from . import crud, schemas
from .database import get_db

@app.post("/items/", response_model=schemas.Item)
def create_item(item: schemas.ItemCreate, db: Session = Depends(get_db)):
    return crud.create_item(db=db, item=item)

@app.get("/items/", response_model=List[schemas.Item])
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_items(db, skip=skip, limit=limit)
'''
    }

if __name__ == "__main__":
    # Example usage
    manager = ProjectDatabaseManager("test-project-001")
    config = manager.initialize_database("sqlite")
    print("Database initialized:")
    print(json.dumps(config, indent=2))