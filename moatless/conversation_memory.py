"""Conversation memory and context management for enhanced natural language processing."""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ConversationMessage:
    """Individual message in a conversation"""
    message_id: str
    timestamp: datetime
    role: str  # "user", "assistant", "system"
    content: str
    metadata: Dict[str, Any] = None
    context: Dict[str, Any] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "message_id": self.message_id,
            "timestamp": self.timestamp.isoformat(),
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata or {},
            "context": self.context or {}
        }


@dataclass 
class ConversationContext:
    """Context information for a conversation"""
    project_id: str
    repository_path: Optional[str] = None
    current_files: List[str] = None
    current_task: Optional[str] = None
    intent_history: List[str] = None
    code_context: Dict[str, Any] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return asdict(self)


class ConversationMemory:
    """Manages conversation history and context for natural language understanding"""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path) if storage_path else None
        self.conversations: Dict[str, List[ConversationMessage]] = {}
        self.conversation_contexts: Dict[str, ConversationContext] = {}
        self.max_messages_per_conversation = 1000
        
        if self.storage_path:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            self._load_conversations()
    
    def start_conversation(self, conversation_id: str, project_id: str, 
                          repository_path: Optional[str] = None) -> ConversationContext:
        """Start a new conversation with initial context"""
        context = ConversationContext(
            project_id=project_id,
            repository_path=repository_path,
            current_files=[],
            current_task=None,
            intent_history=[],
            code_context={}
        )
        
        self.conversations[conversation_id] = []
        self.conversation_contexts[conversation_id] = context
        
        # Add system message to start conversation
        self.add_message(
            conversation_id=conversation_id,
            message_id=f"{conversation_id}_start",
            role="system",
            content="Conversation started",
            metadata={"action": "conversation_start"}
        )
        
        self._save_conversation(conversation_id)
        return context
    
    def add_message(self, conversation_id: str, message_id: str, role: str, 
                   content: str, metadata: Optional[Dict] = None, 
                   context: Optional[Dict] = None) -> ConversationMessage:
        """Add a message to the conversation"""
        if conversation_id not in self.conversations:
            # Auto-start conversation if it doesn't exist
            self.start_conversation(conversation_id, "default")
        
        message = ConversationMessage(
            message_id=message_id,
            timestamp=datetime.now(timezone.utc),
            role=role,
            content=content,
            metadata=metadata or {},
            context=context or {}
        )
        
        self.conversations[conversation_id].append(message)
        
        # Trim conversation if too long
        if len(self.conversations[conversation_id]) > self.max_messages_per_conversation:
            # Keep first message (system) and last N messages
            system_msg = self.conversations[conversation_id][0]
            recent_msgs = self.conversations[conversation_id][-(self.max_messages_per_conversation-1):]
            self.conversations[conversation_id] = [system_msg] + recent_msgs
        
        self._save_conversation(conversation_id)
        return message
    
    def get_conversation_history(self, conversation_id: str, 
                               limit: Optional[int] = None) -> List[ConversationMessage]:
        """Get conversation history"""
        if conversation_id not in self.conversations:
            return []
        
        messages = self.conversations[conversation_id]
        if limit:
            return messages[-limit:]
        return messages
    
    def update_context(self, conversation_id: str, **kwargs) -> Optional[ConversationContext]:
        """Update conversation context"""
        if conversation_id not in self.conversation_contexts:
            return None
        
        context = self.conversation_contexts[conversation_id]
        for key, value in kwargs.items():
            if hasattr(context, key):
                setattr(context, key, value)
        
        self._save_conversation(conversation_id)
        return context
    
    def get_context(self, conversation_id: str) -> Optional[ConversationContext]:
        """Get conversation context"""
        return self.conversation_contexts.get(conversation_id)
    
    def analyze_intent(self, conversation_id: str, user_message: str) -> Dict[str, Any]:
        """Analyze user intent based on conversation history and context"""
        context = self.get_context(conversation_id)
        history = self.get_conversation_history(conversation_id, limit=10)
        
        # Simple intent classification - could be enhanced with ML models
        intent_analysis = {
            "primary_intent": self._classify_intent(user_message),
            "entities": self._extract_entities(user_message),
            "context_relevance": self._assess_context_relevance(user_message, context),
            "confidence": 0.8,  # Placeholder confidence score
            "suggested_actions": self._suggest_actions(user_message, context)
        }
        
        # Update intent history
        if context:
            if not context.intent_history:
                context.intent_history = []
            context.intent_history.append(intent_analysis["primary_intent"])
            if len(context.intent_history) > 10:
                context.intent_history = context.intent_history[-10:]
        
        return intent_analysis
    
    def _classify_intent(self, message: str) -> str:
        """Simple intent classification"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["create", "make", "generate", "build"]):
            return "create"
        elif any(word in message_lower for word in ["fix", "debug", "solve", "repair"]):
            return "fix"
        elif any(word in message_lower for word in ["explain", "understand", "what", "how"]):
            return "explain"
        elif any(word in message_lower for word in ["test", "run", "check", "validate"]):
            return "test"
        elif any(word in message_lower for word in ["refactor", "improve", "optimize"]):
            return "refactor"
        elif any(word in message_lower for word in ["review", "analyze", "examine"]):
            return "review"
        else:
            return "general"
    
    def _extract_entities(self, message: str) -> List[Dict[str, str]]:
        """Extract entities from message"""
        entities = []
        
        # Simple entity extraction - file paths
        import re
        file_patterns = [
            r'([a-zA-Z_][a-zA-Z0-9_]*\.py)',  # Python files
            r'([a-zA-Z_][a-zA-Z0-9_]*\.js)',   # JavaScript files
            r'([a-zA-Z_][a-zA-Z0-9_]*\.java)', # Java files
            r'([a-zA-Z_][a-zA-Z0-9_]*\.cpp)',  # C++ files
        ]
        
        for pattern in file_patterns:
            matches = re.findall(pattern, message)
            for match in matches:
                entities.append({"type": "file", "value": match})
        
        # Function/class names
        function_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        function_matches = re.findall(function_pattern, message)
        for match in function_matches:
            entities.append({"type": "function", "value": match})
        
        return entities
    
    def _assess_context_relevance(self, message: str, context: Optional[ConversationContext]) -> float:
        """Assess how relevant the message is to current context"""
        if not context:
            return 0.5
        
        relevance_score = 0.5
        
        # Check if message mentions current files
        if context.current_files:
            message_lower = message.lower()
            for file_path in context.current_files:
                if Path(file_path).stem.lower() in message_lower:
                    relevance_score += 0.2
        
        # Check if message relates to current task
        if context.current_task and context.current_task.lower() in message.lower():
            relevance_score += 0.3
        
        return min(relevance_score, 1.0)
    
    def _suggest_actions(self, message: str, context: Optional[ConversationContext]) -> List[str]:
        """Suggest possible actions based on intent and context"""
        intent = self._classify_intent(message)
        actions = []
        
        if intent == "create":
            actions.extend(["create_file", "generate_code", "scaffold_project"])
        elif intent == "fix":
            actions.extend(["analyze_error", "run_tests", "debug_code"])
        elif intent == "explain":
            actions.extend(["view_code", "analyze_structure", "generate_documentation"])
        elif intent == "test":
            actions.extend(["run_tests", "create_test", "validate_functionality"])
        elif intent == "refactor":
            actions.extend(["analyze_code_quality", "suggest_improvements", "optimize_code"])
        elif intent == "review":
            actions.extend(["code_review", "security_scan", "quality_analysis"])
        
        return actions
    
    def _save_conversation(self, conversation_id: str):
        """Save conversation to storage"""
        if not self.storage_path:
            return
        
        conversation_file = self.storage_path / f"{conversation_id}.json"
        conversation_data = {
            "conversation_id": conversation_id,
            "messages": [msg.to_dict() for msg in self.conversations.get(conversation_id, [])],
            "context": self.conversation_contexts.get(conversation_id, ConversationContext("default")).to_dict()
        }
        
        try:
            with open(conversation_file, 'w') as f:
                json.dump(conversation_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save conversation {conversation_id}: {e}")
    
    def _load_conversations(self):
        """Load conversations from storage"""
        if not self.storage_path or not self.storage_path.exists():
            return
        
        for conversation_file in self.storage_path.glob("*.json"):
            try:
                with open(conversation_file, 'r') as f:
                    data = json.load(f)
                
                conversation_id = data["conversation_id"]
                
                # Load messages
                messages = []
                for msg_data in data.get("messages", []):
                    msg = ConversationMessage(
                        message_id=msg_data["message_id"],
                        timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                        role=msg_data["role"],
                        content=msg_data["content"],
                        metadata=msg_data.get("metadata", {}),
                        context=msg_data.get("context", {})
                    )
                    messages.append(msg)
                
                self.conversations[conversation_id] = messages
                
                # Load context
                context_data = data.get("context", {})
                context = ConversationContext(**context_data)
                self.conversation_contexts[conversation_id] = context
                
            except Exception as e:
                logger.error(f"Failed to load conversation {conversation_file}: {e}")


# Global conversation memory instance
conversation_memory = ConversationMemory()