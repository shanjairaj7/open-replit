from pydantic import BaseModel
from typing import Optional, Union, Dict, Any
from enum import Enum

class ActionType(str, Enum):
    FILE = "file"
    SHELL = "shell" 
    START = "start"
    SUPABASE = "supabase"

class FileAction(BaseModel):
    type: ActionType = ActionType.FILE
    filePath: str
    content: str = ""
    isStreaming: bool = False

class ShellAction(BaseModel):
    type: ActionType = ActionType.SHELL
    content: str
    isStreaming: bool = False

class StartAction(BaseModel):
    type: ActionType = ActionType.START
    content: str
    isStreaming: bool = False

class SupabaseAction(BaseModel):
    type: ActionType = ActionType.SUPABASE
    operation: str
    content: str = ""
    isStreaming: bool = False

# Union type for all actions
BoltAction = Union[FileAction, ShellAction, StartAction, SupabaseAction]

class BoltArtifact(BaseModel):
    id: str
    title: str
    actions: list[BoltAction] = []
    isComplete: bool = False