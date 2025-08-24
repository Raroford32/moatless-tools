#!/usr/bin/env python3
"""
Demonstration script for the enhanced real-world Moatless Tools system.

This script showcases the new features:
1. Real-time conversation management with intent analysis
2. Complete project lifecycle management
3. Code quality and security monitoring
4. Task management with progress tracking
"""

import asyncio
import uuid
from datetime import datetime

from moatless.conversation_memory import conversation_memory, ConversationContext
from moatless.project_manager import project_manager, TaskPriority, TaskStatus
from moatless.events import ProgressEvent, ConversationEvent, ProjectEvent


async def demonstrate_conversation_system():
    """Demonstrate the enhanced conversation system"""
    print("🗨️  === Conversation Management Demo ===")
    
    # Start a new conversation
    conversation_id = str(uuid.uuid4())
    project_id = "demo_project_001"
    
    print(f"Starting conversation {conversation_id} for project {project_id}")
    context = conversation_memory.start_conversation(
        conversation_id=conversation_id,
        project_id=project_id,
        repository_path="/demo/repo"
    )
    
    # Simulate user interactions with intent analysis
    user_messages = [
        "Can you help me create a new Python web application?",
        "I need to fix a bug in the authentication module",
        "Please explain how the database connection works",
        "Run the unit tests for the user service",
        "Refactor the payment processing code for better performance",
        "Review the security of the API endpoints"
    ]
    
    for i, message in enumerate(user_messages):
        print(f"\n👤 User: {message}")
        
        # Add user message and analyze intent
        msg = conversation_memory.add_message(
            conversation_id=conversation_id,
            message_id=f"msg_{i+1}",
            role="user",
            content=message
        )
        
        # Analyze intent
        intent_analysis = conversation_memory.analyze_intent(conversation_id, message)
        print(f"🧠 Intent: {intent_analysis['primary_intent']}")
        print(f"📊 Confidence: {intent_analysis['confidence']}")
        print(f"🎯 Suggested actions: {', '.join(intent_analysis['suggested_actions'])}")
        
        if intent_analysis['entities']:
            entities = [f"{e['type']}:{e['value']}" for e in intent_analysis['entities']]
            print(f"🔍 Entities found: {', '.join(entities)}")
        
        # Add assistant response
        assistant_response = f"I understand you want to {intent_analysis['primary_intent']}. Let me help you with that."
        conversation_memory.add_message(
            conversation_id=conversation_id,
            message_id=f"assistant_msg_{i+1}",
            role="assistant",
            content=assistant_response
        )
    
    # Show conversation history
    history = conversation_memory.get_conversation_history(conversation_id, limit=5)
    print(f"\n📝 Recent conversation history ({len(history)} messages):")
    for msg in history[-3:]:  # Show last 3 messages
        print(f"  {msg.role}: {msg.content[:50]}...")


async def demonstrate_project_management():
    """Demonstrate the project management system"""
    print("\n\n🏗️  === Project Management Demo ===")
    
    # Create a new project
    project = await project_manager.create_project(
        name="E-commerce Platform",
        description="A modern e-commerce platform with microservices architecture",
        repository_path="/demo/ecommerce",
        owner="lead_developer@company.com",
        tags=["web", "microservices", "python", "react"]
    )
    
    print(f"Created project: {project.name} (ID: {project.project_id})")
    print(f"Status: {project.status.value}")
    print(f"Repository: {project.repository_path}")
    
    # Create some tasks
    tasks_to_create = [
        {
            "title": "Set up authentication service",
            "description": "Implement JWT-based authentication with refresh tokens",
            "priority": TaskPriority.HIGH,
            "files_involved": ["auth_service.py", "jwt_utils.py", "user_model.py"]
        },
        {
            "title": "Design payment processing API",
            "description": "Create secure payment processing with Stripe integration",
            "priority": TaskPriority.HIGH,
            "files_involved": ["payment_api.py", "stripe_client.py"]
        },
        {
            "title": "Implement product catalog",
            "description": "Build product listing and search functionality",
            "priority": TaskPriority.MEDIUM,
            "files_involved": ["product_service.py", "search_engine.py"]
        },
        {
            "title": "Add logging and monitoring",
            "description": "Set up comprehensive logging and health monitoring",
            "priority": TaskPriority.LOW,
            "files_involved": ["logger.py", "health_check.py", "metrics.py"]
        }
    ]
    
    created_tasks = []
    for task_data in tasks_to_create:
        task = await project_manager.create_task(
            project_id=project.project_id,
            **task_data
        )
        created_tasks.append(task)
        print(f"✅ Created task: {task.title} (Priority: {task.priority.value})")
    
    # Update some task statuses
    await project_manager.update_task(
        project_id=project.project_id,
        task_id=created_tasks[0].task_id,
        status=TaskStatus.IN_PROGRESS,
        assigned_to="backend_dev@company.com"
    )
    
    await project_manager.update_task(
        project_id=project.project_id,
        task_id=created_tasks[1].task_id,
        status=TaskStatus.COMPLETED,
        assigned_to="senior_dev@company.com"
    )
    
    print("\n📊 Updated task statuses:")
    print(f"  - {created_tasks[0].title}: IN_PROGRESS (assigned to backend_dev@company.com)")
    print(f"  - {created_tasks[1].title}: COMPLETED (assigned to senior_dev@company.com)")
    
    # Start code analysis
    print("\n🔍 Starting code analysis...")
    await project_manager.start_code_analysis(project.project_id)
    
    # Start security scan
    print("🔒 Starting security scan...")
    await project_manager.start_security_scan(project.project_id)
    
    # Wait a moment for analysis to complete
    await asyncio.sleep(3)
    
    # Get project dashboard
    dashboard = await project_manager.get_project_dashboard(project.project_id)
    
    print("\n📈 Project Dashboard:")
    print(f"  Project: {dashboard['project']['name']}")
    print(f"  Status: {dashboard['project']['status']}")
    print(f"  Total tasks: {dashboard['task_statistics']['total']}")
    print(f"  Task distribution: {dashboard['task_statistics']['by_status']}")
    print(f"  Priority distribution: {dashboard['task_statistics']['by_priority']}")
    
    # Show quality metrics
    quality = dashboard['project']['quality_metrics']
    print(f"\n📏 Code Quality Metrics:")
    print(f"  - Lines of code: {quality['lines_of_code']:,}")
    print(f"  - Code coverage: {quality['code_coverage']:.1f}%")
    print(f"  - Maintainability index: {quality['maintainability_index']:.1f}")
    
    # Show security metrics
    security = dashboard['project']['security_metrics']
    print(f"\n🔐 Security Metrics:")
    vulnerabilities = security['vulnerability_count']
    total_vulns = sum(vulnerabilities.values())
    print(f"  - Total vulnerabilities: {total_vulns}")
    if total_vulns > 0:
        print(f"    • Critical: {vulnerabilities['critical']}")
        print(f"    • High: {vulnerabilities['high']}")
        print(f"    • Medium: {vulnerabilities['medium']}")
        print(f"    • Low: {vulnerabilities['low']}")
    print(f"  - Dependency vulnerabilities: {security['dependency_vulnerabilities']}")
    print(f"  - Secrets detected: {security['secrets_detected']}")


def demonstrate_event_system():
    """Demonstrate the enhanced event system"""
    print("\n\n🎯 === Event System Demo ===")
    
    # Create different types of events
    events = [
        ProgressEvent(
            operation_id="analysis_001",
            progress_percentage=75.0,
            current_step="Analyzing security vulnerabilities",
            total_steps=100,
            estimated_remaining_time=45.0
        ),
        ConversationEvent(
            conversation_id="conv_123",
            message_type="user",
            content="Can you optimize the database queries?",
            metadata={"intent": "optimize", "confidence": 0.9}
        ),
        ProjectEvent(
            project_id="proj_456",
            status="active",
            details={"milestone": "MVP completed", "tasks_completed": 15}
        )
    ]
    
    for event in events:
        print(f"📡 Event: {event.scope}/{event.event_type}")
        if hasattr(event, 'progress_percentage'):
            print(f"   Progress: {event.progress_percentage:.1f}% - {event.current_step}")
        elif hasattr(event, 'message_type'):
            print(f"   Message: {event.content[:50]}...")
        elif hasattr(event, 'status'):
            print(f"   Status: {event.status}")
        print(f"   Timestamp: {event.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")


async def main():
    """Main demonstration function"""
    print("🚀 Moatless Tools - Enhanced Real-World System Demo")
    print("=" * 60)
    
    try:
        await demonstrate_conversation_system()
        await demonstrate_project_management()
        demonstrate_event_system()
        
        print("\n\n✨ === Demo Summary ===")
        print("The enhanced Moatless Tools system now includes:")
        print("✅ Intelligent conversation management with intent analysis")
        print("✅ Complete project lifecycle management")
        print("✅ Real-time code quality and security monitoring")
        print("✅ Advanced task management with progress tracking")
        print("✅ Enhanced event system for real-time updates")
        print("✅ WebSocket support for live UI updates")
        print("✅ Comprehensive API endpoints for all features")
        
        print("\n🎯 Ready for real-world deployment!")
        
    except Exception as e:
        print(f"❌ Demo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())