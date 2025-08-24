"""Tests for enhanced real-world system features."""

import pytest
import asyncio
import uuid
from datetime import datetime, timezone

from moatless.conversation_memory import ConversationMemory, ConversationMessage
from moatless.project_manager import ProjectManager, ProjectStatus, TaskStatus, TaskPriority
from moatless.events import ProgressEvent, ConversationEvent, ProjectEvent


class TestConversationMemory:
    """Test conversation memory functionality"""
    
    def test_start_conversation(self):
        """Test starting a new conversation"""
        memory = ConversationMemory()
        conversation_id = "test_conv_1"
        project_id = "test_project_1"
        
        context = memory.start_conversation(conversation_id, project_id)
        
        assert context.project_id == project_id
        assert conversation_id in memory.conversations
        assert len(memory.conversations[conversation_id]) == 1  # System message
        assert memory.conversations[conversation_id][0].role == "system"
    
    def test_add_message(self):
        """Test adding messages to conversation"""
        memory = ConversationMemory()
        conversation_id = "test_conv_2"
        
        # Start conversation
        memory.start_conversation(conversation_id, "test_project")
        
        # Add user message
        message = memory.add_message(
            conversation_id=conversation_id,
            message_id="msg_1",
            role="user",
            content="Create a new Python file"
        )
        
        assert message.role == "user"
        assert message.content == "Create a new Python file"
        assert len(memory.conversations[conversation_id]) == 2
    
    def test_intent_analysis(self):
        """Test intent analysis functionality"""
        memory = ConversationMemory()
        conversation_id = "test_conv_3"
        
        memory.start_conversation(conversation_id, "test_project")
        
        # Test different intents
        test_cases = [
            ("Create a new file", "create"),
            ("Fix the bug in main.py", "fix"),
            ("Explain how this function works", "explain"),
            ("Run the tests", "test"),
            ("Refactor this code", "refactor"),
            ("Review the changes", "review")
        ]
        
        for message, expected_intent in test_cases:
            analysis = memory.analyze_intent(conversation_id, message)
            assert analysis["primary_intent"] == expected_intent
            assert "entities" in analysis
            assert "confidence" in analysis
    
    def test_entity_extraction(self):
        """Test entity extraction from messages"""
        memory = ConversationMemory()
        
        # Test file entity extraction
        entities = memory._extract_entities("Please check the main.py file")
        file_entities = [e for e in entities if e["type"] == "file"]
        assert len(file_entities) > 0
        assert file_entities[0]["value"] == "main.py"
        
        # Test function entity extraction
        entities = memory._extract_entities("Call the process_data() function")
        func_entities = [e for e in entities if e["type"] == "function"]
        assert len(func_entities) > 0
        assert func_entities[0]["value"] == "process_data"


class TestProjectManager:
    """Test project management functionality"""
    
    @pytest.mark.asyncio
    async def test_create_project(self):
        """Test creating a new project"""
        manager = ProjectManager()
        
        project = await manager.create_project(
            name="Test Project",
            description="A test project",
            repository_path="/tmp/test_repo",
            owner="test_user"
        )
        
        assert project.name == "Test Project"
        assert project.description == "A test project"
        assert project.repository_path == "/tmp/test_repo"
        assert project.owner == "test_user"
        assert project.status in [ProjectStatus.INITIALIZING, ProjectStatus.ACTIVE]  # Allow both states
        assert project.project_id in manager.projects
    
    @pytest.mark.asyncio
    async def test_create_task(self):
        """Test creating tasks in a project"""
        manager = ProjectManager()
        
        # Create project first
        project = await manager.create_project(
            name="Test Project",
            description="A test project",
            repository_path="/tmp/test_repo"
        )
        
        # Create task
        task = await manager.create_task(
            project_id=project.project_id,
            title="Test Task",
            description="A test task",
            priority=TaskPriority.HIGH,
            files_involved=["main.py", "utils.py"]
        )
        
        assert task.title == "Test Task"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING
        assert "main.py" in task.files_involved
        assert task.task_id in project.tasks
    
    @pytest.mark.asyncio
    async def test_update_task(self):
        """Test updating task status"""
        manager = ProjectManager()
        
        # Create project and task
        project = await manager.create_project(
            name="Test Project",
            description="A test project",
            repository_path="/tmp/test_repo"
        )
        
        task = await manager.create_task(
            project_id=project.project_id,
            title="Test Task",
            description="A test task"
        )
        
        # Update task status
        updated_task = await manager.update_task(
            project_id=project.project_id,
            task_id=task.task_id,
            status=TaskStatus.IN_PROGRESS,
            assigned_to="developer@example.com"
        )
        
        assert updated_task.status == TaskStatus.IN_PROGRESS
        assert updated_task.assigned_to == "developer@example.com"
    
    @pytest.mark.asyncio
    async def test_project_dashboard(self):
        """Test project dashboard data generation"""
        manager = ProjectManager()
        
        # Create project with tasks
        project = await manager.create_project(
            name="Test Project",
            description="A test project",
            repository_path="/tmp/test_repo"
        )
        
        # Create multiple tasks with different statuses
        await manager.create_task(
            project_id=project.project_id,
            title="Task 1",
            description="First task",
            priority=TaskPriority.HIGH
        )
        
        task2 = await manager.create_task(
            project_id=project.project_id,
            title="Task 2",
            description="Second task",
            priority=TaskPriority.MEDIUM
        )
        
        # Update one task to completed
        await manager.update_task(
            project_id=project.project_id,
            task_id=task2.task_id,
            status=TaskStatus.COMPLETED
        )
        
        # Get dashboard
        dashboard = await manager.get_project_dashboard(project.project_id)
        
        assert dashboard is not None
        assert dashboard["project"]["project_id"] == project.project_id
        assert dashboard["task_statistics"]["total"] == 2
        assert dashboard["task_statistics"]["by_status"]["pending"] == 1
        assert dashboard["task_statistics"]["by_status"]["completed"] == 1
        assert dashboard["task_statistics"]["by_priority"]["high"] == 1
        assert dashboard["task_statistics"]["by_priority"]["medium"] == 1


class TestEventSystem:
    """Test enhanced event system"""
    
    def test_progress_event_creation(self):
        """Test creating progress events"""
        event = ProgressEvent(
            operation_id="test_op_1",
            progress_percentage=50.0,
            current_step="Processing files",
            total_steps=10,
            estimated_remaining_time=30.0
        )
        
        assert event.operation_id == "test_op_1"
        assert event.progress_percentage == 50.0
        assert event.current_step == "Processing files"
        assert event.total_steps == 10
        assert event.estimated_remaining_time == 30.0
        assert event.scope == "progress"
        assert event.event_type == "progress"
    
    def test_conversation_event_creation(self):
        """Test creating conversation events"""
        event = ConversationEvent(
            conversation_id="conv_1",
            message_type="user",
            content="Hello, can you help me?",
            metadata={"intent": "general"}
        )
        
        assert event.conversation_id == "conv_1"
        assert event.message_type == "user"
        assert event.content == "Hello, can you help me?"
        assert event.metadata["intent"] == "general"
        assert event.scope == "conversation"
    
    def test_project_event_creation(self):
        """Test creating project events"""
        event = ProjectEvent(
            project_id="proj_1",
            status="active",
            details={"action": "created"}
        )
        
        assert event.project_id == "proj_1"
        assert event.status == "active"
        assert event.details["action"] == "created"
        assert event.scope == "project"


# Integration tests would go here for testing the API endpoints
# These would require setting up FastAPI test client and mocking dependencies


if __name__ == "__main__":
    # Run basic tests
    test_conv = TestConversationMemory()
    test_conv.test_start_conversation()
    test_conv.test_add_message()
    test_conv.test_intent_analysis()
    test_conv.test_entity_extraction()
    print("✓ Conversation memory tests passed")
    
    # Note: Async tests would need to be run with asyncio.run() or pytest
    print("✓ Basic functionality tests completed")