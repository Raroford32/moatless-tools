"""Enhanced API endpoints for conversation and project management."""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends, WebSocket
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from moatless.conversation_memory import conversation_memory, ConversationContext
from moatless.project_manager import project_manager, ProjectStatus, TaskStatus, TaskPriority
from moatless.api.websocket import manager as websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enhanced", tags=["enhanced"])


# Pydantic models for API requests/responses
class StartConversationRequest(BaseModel):
    project_id: str
    repository_path: Optional[str] = None


class AddMessageRequest(BaseModel):
    conversation_id: str
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    metadata: Optional[Dict] = None


class CreateProjectRequest(BaseModel):
    name: str
    description: str
    repository_path: str
    owner: Optional[str] = None
    tags: List[str] = []


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None


class CreateTaskRequest(BaseModel):
    title: str
    description: str
    priority: str = "medium"
    assigned_to: Optional[str] = None
    tags: List[str] = []
    files_involved: List[str] = []


class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    tags: Optional[List[str]] = None


# Conversation Management Endpoints
@router.post("/conversations/start")
async def start_conversation(request: StartConversationRequest):
    """Start a new conversation with project context"""
    try:
        conversation_id = str(uuid.uuid4())
        context = conversation_memory.start_conversation(
            conversation_id=conversation_id,
            project_id=request.project_id,
            repository_path=request.repository_path
        )
        
        return {
            "conversation_id": conversation_id,
            "context": context.to_dict(),
            "status": "started"
        }
    except Exception as e:
        logger.error(f"Failed to start conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations/message")
async def add_message(request: AddMessageRequest):
    """Add a message to a conversation"""
    try:
        message_id = str(uuid.uuid4())
        
        # Analyze intent for user messages
        intent_analysis = None
        if request.role == "user":
            intent_analysis = conversation_memory.analyze_intent(
                request.conversation_id,
                request.content
            )
        
        message = conversation_memory.add_message(
            conversation_id=request.conversation_id,
            message_id=message_id,
            role=request.role,
            content=request.content,
            metadata=request.metadata
        )
        
        # Broadcast message via WebSocket
        await websocket_manager.broadcast_message({
            "type": "conversation_message",
            "conversation_id": request.conversation_id,
            "message": message.to_dict(),
            "intent_analysis": intent_analysis
        })
        
        return {
            "message": message.to_dict(),
            "intent_analysis": intent_analysis
        }
    except Exception as e:
        logger.error(f"Failed to add message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}/history")
async def get_conversation_history(conversation_id: str, limit: Optional[int] = None):
    """Get conversation history"""
    try:
        messages = conversation_memory.get_conversation_history(conversation_id, limit)
        context = conversation_memory.get_context(conversation_id)
        
        return {
            "conversation_id": conversation_id,
            "messages": [msg.to_dict() for msg in messages],
            "context": context.to_dict() if context else None
        }
    except Exception as e:
        logger.error(f"Failed to get conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/conversations/{conversation_id}/context")
async def update_conversation_context(conversation_id: str, context_update: Dict):
    """Update conversation context"""
    try:
        context = conversation_memory.update_context(conversation_id, **context_update)
        if not context:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"context": context.to_dict()}
    except Exception as e:
        logger.error(f"Failed to update conversation context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Project Management Endpoints
@router.post("/projects")
async def create_project(request: CreateProjectRequest):
    """Create a new project"""
    try:
        project = await project_manager.create_project(
            name=request.name,
            description=request.description,
            repository_path=request.repository_path,
            owner=request.owner,
            tags=request.tags
        )
        
        return {"project": project.to_dict()}
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects")
async def list_projects(owner: Optional[str] = None, status: Optional[str] = None):
    """List projects with optional filtering"""
    try:
        status_enum = None
        if status:
            try:
                status_enum = ProjectStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        projects = await project_manager.list_projects(owner=owner, status=status_enum)
        return {"projects": [p.to_dict() for p in projects]}
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get a specific project"""
    try:
        project = await project_manager.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {"project": project.to_dict()}
    except Exception as e:
        logger.error(f"Failed to get project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/projects/{project_id}")
async def update_project(project_id: str, request: UpdateProjectRequest):
    """Update a project"""
    try:
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        project = await project_manager.update_project(project_id, **update_data)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {"project": project.to_dict()}
    except Exception as e:
        logger.error(f"Failed to update project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/dashboard")
async def get_project_dashboard(project_id: str):
    """Get comprehensive project dashboard data"""
    try:
        dashboard = await project_manager.get_project_dashboard(project_id)
        if not dashboard:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return dashboard
    except Exception as e:
        logger.error(f"Failed to get project dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/analyze")
async def start_code_analysis(project_id: str):
    """Start code analysis for a project"""
    try:
        operation_id = str(uuid.uuid4())
        
        # Track the operation
        await websocket_manager.track_operation(
            operation_id=operation_id,
            operation_type="code_analysis",
            metadata={"project_id": project_id}
        )
        
        success = await project_manager.start_code_analysis(project_id)
        if not success:
            raise HTTPException(status_code=400, detail="Analysis already in progress or project not found")
        
        return {
            "operation_id": operation_id,
            "status": "started",
            "project_id": project_id
        }
    except Exception as e:
        logger.error(f"Failed to start code analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/security-scan")
async def start_security_scan(project_id: str):
    """Start security scan for a project"""
    try:
        operation_id = str(uuid.uuid4())
        
        # Track the operation
        await websocket_manager.track_operation(
            operation_id=operation_id,
            operation_type="security_scan",
            metadata={"project_id": project_id}
        )
        
        success = await project_manager.start_security_scan(project_id)
        if not success:
            raise HTTPException(status_code=400, detail="Scan already in progress or project not found")
        
        return {
            "operation_id": operation_id,
            "status": "started",
            "project_id": project_id
        }
    except Exception as e:
        logger.error(f"Failed to start security scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Task Management Endpoints
@router.post("/projects/{project_id}/tasks")
async def create_task(project_id: str, request: CreateTaskRequest):
    """Create a new task in a project"""
    try:
        priority = TaskPriority(request.priority)
        task = await project_manager.create_task(
            project_id=project_id,
            title=request.title,
            description=request.description,
            priority=priority,
            assigned_to=request.assigned_to,
            tags=request.tags,
            files_involved=request.files_involved
        )
        
        if not task:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {"task": task.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/tasks")
async def get_project_tasks(project_id: str):
    """Get all tasks for a project"""
    try:
        project = await project_manager.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        tasks = [task.to_dict() for task in project.tasks.values()]
        return {"tasks": tasks}
    except Exception as e:
        logger.error(f"Failed to get project tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/projects/{project_id}/tasks/{task_id}")
async def update_task(project_id: str, task_id: str, request: UpdateTaskRequest):
    """Update a task"""
    try:
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        task = await project_manager.update_task(project_id, task_id, **update_data)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task or project not found")
        
        return {"task": task.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Real-time Operations Endpoints
@router.get("/operations/{operation_id}")
async def get_operation_status(operation_id: str):
    """Get status of a tracked operation"""
    try:
        operation = websocket_manager.active_operations.get(operation_id)
        if not operation:
            raise HTTPException(status_code=404, detail="Operation not found")
        
        return {"operation": operation}
    except Exception as e:
        logger.error(f"Failed to get operation status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/operations")
async def list_active_operations():
    """List all active operations"""
    try:
        operations = {
            op_id: op_data for op_id, op_data in websocket_manager.active_operations.items()
            if op_data.get("status") != "completed"
        }
        return {"operations": operations}
    except Exception as e:
        logger.error(f"Failed to list operations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket connection info
@router.get("/websocket/connections")
async def get_websocket_connections():
    """Get information about active WebSocket connections"""
    try:
        connection_count = len(websocket_manager.active_connections)
        subscriptions = {
            "projects": len(websocket_manager.project_subscriptions),
            "trajectories": len(websocket_manager.trajectory_subscriptions)
        }
        
        return {
            "active_connections": connection_count,
            "subscriptions": subscriptions
        }
    except Exception as e:
        logger.error(f"Failed to get WebSocket info: {e}")
        raise HTTPException(status_code=500, detail=str(e))