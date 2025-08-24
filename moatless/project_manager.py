"""Project management system for complete codebase lifecycle management."""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict

from moatless.events import ProjectEvent, SecurityScanEvent, CodeAnalysisEvent

logger = logging.getLogger(__name__)


class ProjectStatus(Enum):
    """Project status enumeration"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    ERROR = "error"


class TaskStatus(Enum):
    """Task status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CodeQualityMetrics:
    """Code quality metrics for a project"""
    lines_of_code: int = 0
    cyclomatic_complexity: float = 0.0
    code_coverage: float = 0.0
    technical_debt_ratio: float = 0.0
    maintainability_index: float = 0.0
    duplicated_lines_density: float = 0.0
    last_updated: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        result = asdict(self)
        if self.last_updated:
            result["last_updated"] = self.last_updated.isoformat()
        return result


@dataclass
class SecurityMetrics:
    """Security metrics for a project"""
    vulnerability_count: Dict[str, int] = None  # {"low": 2, "medium": 1, "high": 0, "critical": 0}
    dependency_vulnerabilities: int = 0
    secrets_detected: int = 0
    last_scan: Optional[datetime] = None
    
    def __post_init__(self):
        if self.vulnerability_count is None:
            self.vulnerability_count = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    
    def to_dict(self) -> dict:
        result = asdict(self)
        if self.last_scan:
            result["last_scan"] = self.last_scan.isoformat()
        return result


@dataclass
class ProjectTask:
    """Individual task within a project"""
    task_id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    assigned_to: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    tags: List[str] = None
    dependencies: List[str] = None  # List of task IDs this task depends on
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    files_involved: List[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = self.created_at
        if self.tags is None:
            self.tags = []
        if self.dependencies is None:
            self.dependencies = []
        if self.files_involved is None:
            self.files_involved = []
    
    def to_dict(self) -> dict:
        result = asdict(self)
        for date_field in ["created_at", "updated_at", "due_date"]:
            if result[date_field]:
                result[date_field] = result[date_field].isoformat()
        result["status"] = self.status.value
        result["priority"] = self.priority.value
        return result


@dataclass
class Project:
    """Project representation with complete lifecycle management"""
    project_id: str
    name: str
    description: str
    repository_path: str
    status: ProjectStatus
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    owner: Optional[str] = None
    collaborators: List[str] = None
    tags: List[str] = None
    settings: Dict[str, Any] = None
    quality_metrics: Optional[CodeQualityMetrics] = None
    security_metrics: Optional[SecurityMetrics] = None
    tasks: Dict[str, ProjectTask] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = self.created_at
        if self.collaborators is None:
            self.collaborators = []
        if self.tags is None:
            self.tags = []
        if self.settings is None:
            self.settings = {}
        if self.quality_metrics is None:
            self.quality_metrics = CodeQualityMetrics()
        if self.security_metrics is None:
            self.security_metrics = SecurityMetrics()
        if self.tasks is None:
            self.tasks = {}
    
    def to_dict(self) -> dict:
        result = asdict(self)
        for date_field in ["created_at", "updated_at"]:
            if result[date_field]:
                result[date_field] = result[date_field].isoformat()
        result["status"] = self.status.value
        result["quality_metrics"] = self.quality_metrics.to_dict()
        result["security_metrics"] = self.security_metrics.to_dict()
        result["tasks"] = {task_id: task.to_dict() for task_id, task in self.tasks.items()}
        return result


class ProjectManager:
    """Manages multiple projects with complete lifecycle support"""
    
    def __init__(self, storage_path: Optional[str] = None, event_bus=None):
        self.storage_path = Path(storage_path) if storage_path else None
        self.event_bus = event_bus
        self.projects: Dict[str, Project] = {}
        self.active_scans: Dict[str, Set[str]] = {}  # project_id -> set of scan types
        
        if self.storage_path:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            self._load_projects()
    
    async def create_project(self, name: str, description: str, repository_path: str,
                           owner: Optional[str] = None, tags: List[str] = None) -> Project:
        """Create a new project"""
        project_id = str(uuid.uuid4())
        
        project = Project(
            project_id=project_id,
            name=name,
            description=description,
            repository_path=repository_path,
            status=ProjectStatus.INITIALIZING,
            owner=owner,
            tags=tags or []
        )
        
        self.projects[project_id] = project
        await self._save_project(project)
        
        # Emit project creation event
        if self.event_bus:
            event = ProjectEvent(
                project_id=project_id,
                event_type="created",
                status=project.status.value,
                details={"name": name, "repository_path": repository_path}
            )
            await self.event_bus.emit(event)
        
        # Start initialization process
        await self._initialize_project(project)
        
        return project
    
    async def _initialize_project(self, project: Project):
        """Initialize a project with basic analysis"""
        try:
            project.status = ProjectStatus.ACTIVE
            project.updated_at = datetime.now(timezone.utc)
            
            # Start basic code analysis
            await self.start_code_analysis(project.project_id)
            
            # Start security scan
            await self.start_security_scan(project.project_id)
            
            await self._save_project(project)
            
            if self.event_bus:
                event = ProjectEvent(
                    project_id=project.project_id,
                    event_type="initialized",
                    status=project.status.value
                )
                await self.event_bus.emit(event)
                
        except Exception as e:
            logger.error(f"Failed to initialize project {project.project_id}: {e}")
            project.status = ProjectStatus.ERROR
            await self._save_project(project)
    
    async def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID"""
        return self.projects.get(project_id)
    
    async def list_projects(self, owner: Optional[str] = None, 
                          status: Optional[ProjectStatus] = None) -> List[Project]:
        """List projects with optional filtering"""
        projects = list(self.projects.values())
        
        if owner:
            projects = [p for p in projects if p.owner == owner]
        
        if status:
            projects = [p for p in projects if p.status == status]
        
        return projects
    
    async def update_project(self, project_id: str, **kwargs) -> Optional[Project]:
        """Update project properties"""
        if project_id not in self.projects:
            return None
        
        project = self.projects[project_id]
        old_status = project.status
        
        for key, value in kwargs.items():
            if hasattr(project, key):
                if key == "status" and isinstance(value, str):
                    setattr(project, key, ProjectStatus(value))
                else:
                    setattr(project, key, value)
        
        project.updated_at = datetime.now(timezone.utc)
        await self._save_project(project)
        
        # Emit status change event if status changed
        if old_status != project.status and self.event_bus:
            event = ProjectEvent(
                project_id=project_id,
                event_type="status_changed",
                status=project.status.value,
                details={"old_status": old_status.value, "new_status": project.status.value}
            )
            await self.event_bus.emit(event)
        
        return project
    
    async def create_task(self, project_id: str, title: str, description: str,
                        priority: TaskPriority = TaskPriority.MEDIUM,
                        assigned_to: Optional[str] = None,
                        tags: List[str] = None,
                        files_involved: List[str] = None) -> Optional[ProjectTask]:
        """Create a new task in a project"""
        if project_id not in self.projects:
            return None
        
        task_id = str(uuid.uuid4())
        task = ProjectTask(
            task_id=task_id,
            title=title,
            description=description,
            status=TaskStatus.PENDING,
            priority=priority,
            assigned_to=assigned_to,
            tags=tags or [],
            files_involved=files_involved or []
        )
        
        self.projects[project_id].tasks[task_id] = task
        await self._save_project(self.projects[project_id])
        
        return task
    
    async def update_task(self, project_id: str, task_id: str, **kwargs) -> Optional[ProjectTask]:
        """Update a task"""
        project = self.projects.get(project_id)
        if not project or task_id not in project.tasks:
            return None
        
        task = project.tasks[task_id]
        
        for key, value in kwargs.items():
            if hasattr(task, key):
                if key == "status" and isinstance(value, str):
                    setattr(task, key, TaskStatus(value))
                elif key == "priority" and isinstance(value, str):
                    setattr(task, key, TaskPriority(value))
                else:
                    setattr(task, key, value)
        
        task.updated_at = datetime.now(timezone.utc)
        await self._save_project(project)
        
        return task
    
    async def start_code_analysis(self, project_id: str) -> bool:
        """Start comprehensive code analysis"""
        project = self.projects.get(project_id)
        if not project:
            return False
        
        # Prevent multiple concurrent analyses
        if project_id not in self.active_scans:
            self.active_scans[project_id] = set()
        
        if "code_analysis" in self.active_scans[project_id]:
            return False
        
        self.active_scans[project_id].add("code_analysis")
        
        try:
            # Start analysis in background
            asyncio.create_task(self._perform_code_analysis(project))
            return True
        except Exception as e:
            logger.error(f"Failed to start code analysis for {project_id}: {e}")
            self.active_scans[project_id].discard("code_analysis")
            return False
    
    async def _perform_code_analysis(self, project: Project):
        """Perform code analysis (placeholder implementation)"""
        try:
            if self.event_bus:
                event = CodeAnalysisEvent(
                    project_id=project.project_id,
                    file_path="*",
                    analysis_type="quality",
                    status="started"
                )
                await self.event_bus.emit(event)
            
            # Simulate analysis work
            await asyncio.sleep(2)
            
            # Update metrics (placeholder values)
            project.quality_metrics.lines_of_code = 5000  # Would be calculated
            project.quality_metrics.code_coverage = 75.5
            project.quality_metrics.maintainability_index = 68.2
            project.quality_metrics.last_updated = datetime.now(timezone.utc)
            
            await self._save_project(project)
            
            if self.event_bus:
                event = CodeAnalysisEvent(
                    project_id=project.project_id,
                    file_path="*",
                    analysis_type="quality",
                    status="completed",
                    results=project.quality_metrics.to_dict()
                )
                await self.event_bus.emit(event)
                
        except Exception as e:
            logger.error(f"Code analysis failed for {project.project_id}: {e}")
        finally:
            self.active_scans[project.project_id].discard("code_analysis")
    
    async def start_security_scan(self, project_id: str) -> bool:
        """Start security vulnerability scan"""
        project = self.projects.get(project_id)
        if not project:
            return False
        
        if project_id not in self.active_scans:
            self.active_scans[project_id] = set()
        
        if "security_scan" in self.active_scans[project_id]:
            return False
        
        self.active_scans[project_id].add("security_scan")
        
        try:
            asyncio.create_task(self._perform_security_scan(project))
            return True
        except Exception as e:
            logger.error(f"Failed to start security scan for {project_id}: {e}")
            self.active_scans[project_id].discard("security_scan")
            return False
    
    async def _perform_security_scan(self, project: Project):
        """Perform security scan (placeholder implementation)"""
        try:
            if self.event_bus:
                event = SecurityScanEvent(
                    project_id=project.project_id,
                    scan_type="vulnerability",
                    severity="info",
                    finding={"status": "started"}
                )
                await self.event_bus.emit(event)
            
            # Simulate scan work
            await asyncio.sleep(3)
            
            # Update security metrics (placeholder)
            project.security_metrics.vulnerability_count = {"low": 2, "medium": 1, "high": 0, "critical": 0}
            project.security_metrics.dependency_vulnerabilities = 3
            project.security_metrics.secrets_detected = 0
            project.security_metrics.last_scan = datetime.now(timezone.utc)
            
            await self._save_project(project)
            
            if self.event_bus:
                event = SecurityScanEvent(
                    project_id=project.project_id,
                    scan_type="vulnerability",
                    severity="low",
                    finding={
                        "status": "completed",
                        "summary": project.security_metrics.to_dict()
                    }
                )
                await self.event_bus.emit(event)
                
        except Exception as e:
            logger.error(f"Security scan failed for {project.project_id}: {e}")
        finally:
            self.active_scans[project.project_id].discard("security_scan")
    
    async def get_project_dashboard(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive project dashboard data"""
        project = self.projects.get(project_id)
        if not project:
            return None
        
        # Calculate task statistics
        tasks = list(project.tasks.values())
        task_stats = {
            "total": len(tasks),
            "by_status": {},
            "by_priority": {},
            "overdue": 0
        }
        
        now = datetime.now(timezone.utc)
        for task in tasks:
            # Status distribution
            status_str = task.status.value
            task_stats["by_status"][status_str] = task_stats["by_status"].get(status_str, 0) + 1
            
            # Priority distribution
            priority_str = task.priority.value
            task_stats["by_priority"][priority_str] = task_stats["by_priority"].get(priority_str, 0) + 1
            
            # Overdue tasks
            if task.due_date and task.due_date < now and task.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                task_stats["overdue"] += 1
        
        return {
            "project": project.to_dict(),
            "task_statistics": task_stats,
            "active_scans": list(self.active_scans.get(project_id, set())),
            "last_activity": project.updated_at.isoformat() if project.updated_at else None
        }
    
    async def _save_project(self, project: Project):
        """Save project to storage"""
        if not self.storage_path:
            return
        
        project_file = self.storage_path / f"{project.project_id}.json"
        
        try:
            with open(project_file, 'w') as f:
                json.dump(project.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save project {project.project_id}: {e}")
    
    def _load_projects(self):
        """Load projects from storage"""
        if not self.storage_path or not self.storage_path.exists():
            return
        
        for project_file in self.storage_path.glob("*.json"):
            try:
                with open(project_file, 'r') as f:
                    data = json.load(f)
                
                # Convert datetime strings back to datetime objects
                for date_field in ["created_at", "updated_at"]:
                    if data.get(date_field):
                        data[date_field] = datetime.fromisoformat(data[date_field])
                
                # Convert quality metrics
                if "quality_metrics" in data:
                    qm_data = data["quality_metrics"]
                    if qm_data.get("last_updated"):
                        qm_data["last_updated"] = datetime.fromisoformat(qm_data["last_updated"])
                    data["quality_metrics"] = CodeQualityMetrics(**qm_data)
                
                # Convert security metrics
                if "security_metrics" in data:
                    sm_data = data["security_metrics"]
                    if sm_data.get("last_scan"):
                        sm_data["last_scan"] = datetime.fromisoformat(sm_data["last_scan"])
                    data["security_metrics"] = SecurityMetrics(**sm_data)
                
                # Convert tasks
                if "tasks" in data:
                    tasks = {}
                    for task_id, task_data in data["tasks"].items():
                        for date_field in ["created_at", "updated_at", "due_date"]:
                            if task_data.get(date_field):
                                task_data[date_field] = datetime.fromisoformat(task_data[date_field])
                        
                        if "status" in task_data:
                            task_data["status"] = TaskStatus(task_data["status"])
                        if "priority" in task_data:
                            task_data["priority"] = TaskPriority(task_data["priority"])
                        
                        tasks[task_id] = ProjectTask(**task_data)
                    data["tasks"] = tasks
                
                # Convert status
                if "status" in data:
                    data["status"] = ProjectStatus(data["status"])
                
                project = Project(**data)
                self.projects[project.project_id] = project
                
            except Exception as e:
                logger.error(f"Failed to load project {project_file}: {e}")


# Global project manager instance
project_manager = ProjectManager()