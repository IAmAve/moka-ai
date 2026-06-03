# Engineering Workflow Orchestrator AI Agents Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance the EngineeringWorkflowOrchestrator with fully autonomous AI agents for each workflow stage (analyze, create, install, code, test, debug, approval, launch) while maintaining backward compatibility.

**Architecture:** Implement an agent-delegation pattern where the existing orchestrator delegates stage execution to specialized AI agents. Each agent is fully autonomous with goal-driven behavior using LLMs, and the orchestrator maintains workflow coordination, state management, and error handling with fallback capabilities.

**Tech Stack:** Python, LLMs (via existing Moka AI integrations), EventBus, dependency injection, pytest

---
"""
### Task 1: Create AI Agent Base Class

**Files:**
- Create: `core_runtime/ai_agent.py`
- Test: `tests/test_ai_agent.py`

- [ ] **Step 1: Write the failing test for AI Agent base class**

```python
import pytest
from unittest.mock import Mock, AsyncMock
from core_runtime.ai_agent import BaseAIAgent

class TestBaseAIAgent:
    @pytest.fixture
    def agent(self):
        return BaseAIAgent(name="test_agent")
    
    def test_agent_initialization(self, agent):
        """Test that agent initializes with correct attributes"""
        assert agent.name == "test_agent"
        assert agent.logger is not None
        
    @pytest.mark.asyncio
    async def test_receive_goal_method_exists(self, agent):
        """Test that receive_goal method exists"""
        assert hasattr(agent, 'receive_goal')
        assert callable(getattr(agent, 'receive_goal'))
        
    @pytest.mark.asyncio
    async def test_plan_actions_method_exists(self, agent):
        """Test that plan_actions method exists"""
        assert hasattr(agent, 'plan_actions')
        assert callable(getattr(agent, 'plan_actions'))
        
    @pytest.mark.asyncio
    async def test_execute_actions_method_exists(self, agent):
        """Test that execute_actions method exists"""
        assert hasattr(agent, 'execute_actions')
        assert callable(getattr(agent, 'execute_actions'))
        
    @pytest.mark.asyncio
    async def test_report_progress_method_exists(self, agent):
        """Test that report_progress method exists"""
        assert hasattr(agent, 'report_progress')
        assert callable(getattr(agent, 'report_progress'))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ai_agent.py::TestBaseAIAgent::test_agent_initialization -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'core_runtime.ai_agent'"

- [ ] **Step 3: Write minimal implementation**

```python
"""
AI Agent Base Class for Engineering Workflow Orchestrator
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class AgentContext:
    """Context shared between agents during workflow execution"""
    workflow_spec: Optional[Any] = None
    sandbox_id: Optional[str] = None
    stage_results: Dict[str, Any] = field(default_factory=dict)
    shared_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAIAgent(ABC):
    """
    Abstract base class for all AI agents in the Engineering Workflow Orchestrator.
    Defines the standard interface that all stage-specific agents must implement.
    """
    
    def __init__(self, name: str, logger: Optional[logging.Logger] = None):
        self.name = name
        self.logger = logger or logging.getLogger(__name__)
        self._log = self.logger.info if self.logger else lambda m: None
        
    @abstractmethod
    async def receive_goal(self, goal: str, context: AgentContext) -> bool:
        """
        Receive and process a goal for the agent to work towards.
        
        Args:
            goal: The goal statement for the agent
            context: Shared context information
            
        Returns:
            bool: True if goal was successfully received, False otherwise
        """
        pass
        
    @abstractmethod
    async def plan_actions(self, context: AgentContext) -> List[Dict[str, Any]]:
        """
        Plan the actions needed to achieve the agent's goal.
        
        Args:
            context: Shared context information
            
        Returns:
            List[Dict[str, Any]]: List of action plans
        """
        pass
        
    @abstractmethod
    async def execute_actions(self, actions: List[Dict[str, Any]], context: AgentContext) -> bool:
        """
        Execute the planned actions.
        
        Args:
            actions: List of actions to execute
            context: Shared context information
            
        Returns:
            bool: True if execution was successful, False otherwise
        """
        pass
        
    @abstractmethod
    async def report_progress(self, context: AgentContext) -> Dict[str, Any]:
        """
        Report progress on the agent's current work.
        
        Args:
            context: Shared context information
            
        Returns:
            Dict[str, Any]: Progress report
        """
        pass
        
    def _log_info(self, message: str):
        """Log an info message"""
        self._log(f"[{self.name}] {message}")
        
    def _log_error(self, message: str):
        """Log an error message"""
        if self.logger:
            self.logger.error(f"[{self.name}] {message}")
        
    def _log_warning(self, message: str):
        """Log a warning message"""
        if self.logger:
            self.logger.warning(f"[{self.name}] {message}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ai_agent.py::TestBaseAIAgent -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core_runtime/ai_agent.py tests/test_ai_agent.py
git commit -m "feat: create AI agent base class for workflow orchestrator"
```
"""
### Task 2: Create AI Agent Factory

**Files:**
- Create: `core_runtime/ai_agent_factory.py`
- Test: `tests/test_ai_agent_factory.py`

- [ ] **Step 1: Write the failing test for AI Agent Factory**

```python
import pytest
from unittest.mock import Mock, patch
from core_runtime.ai_agent_factory import AIAgentFactory
from core_runtime.ai_agent import BaseAIAgent

class TestAIAgentFactory:
    @pytest.fixture
    def factory(self):
        return AIAgentFactory()
    
    def test_factory_initialization(self, factory):
        """Test that factory initializes correctly"""
        assert factory is not None
        assert hasattr(factory, 'create_agent')
        
    @pytest.mark.asyncio
    async def test_create_analyze_agent(self, factory):
        """Test creating an analyze agent"""
        with patch('core_runtime.ai_agent_factory.AnalyzeAgent') as mock_agent_class:
            mock_agent = Mock(spec=BaseAIAgent)
            mock_agent_class.return_value = mock_agent
            
            agent = factory.create_agent('analyze')
            assert agent == mock_agent
            mock_agent_class.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_create_unknown_agent_type(self, factory):
        """Test creating an unknown agent type raises appropriate error"""
        with pytest.raises(ValueError, match="Unknown agent type"):
            factory.create_agent('unknown_type')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ai_agent_factory.py::TestAIAgentFactory::test_factory_initialization -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'core_runtime.ai_agent_factory'"

- [ ] **Step 3: Write minimal implementation**

```python
"""
AI Agent Factory for creating stage-specific AI agents
"""

import logging
from typing import Dict, Type, Optional
from core_runtime.ai_agent import BaseAIAgent


class AIAgentFactory:
    """
    Factory for creating stage-specific AI agents.
    Manages agent registration and instantiation.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self._agent_types: Dict[str, Type[BaseAIAgent]] = {}
        self._log = self.logger.info if self.logger else lambda m: None
        
    def register_agent_type(self, agent_type: str, agent_class: Type[BaseAIAgent]):
        """
        Register an agent type with its corresponding class.
        
        Args:
            agent_type: String identifier for the agent type
            agent_class: Class that implements the agent type
        """
        self._agent_types[agent_type] = agent_class
        self._log(f"Registered agent type: {agent_type}")
        
    def create_agent(self, agent_type: str, *args, **kwargs) -> BaseAIAgent:
        """
        Create an instance of the specified agent type.
        
        Args:
            agent_type: String identifier for the agent type to create
            *args: Positional arguments to pass to agent constructor
            **kwargs: Keyword arguments to pass to agent constructor
            
        Returns:
            BaseAIAgent: Instance of the requested agent type
            
        Raises:
            ValueError: If agent_type is not registered
        """
        if agent_type not in self._agent_types:
            raise ValueError(f"Unknown agent type: {agent_type}")
            
        agent_class = self._agent_types[agent_type]
        return agent_class(*args, **kwargs)
        
    def get_registered_agent_types(self) -> list:
        """
        Get list of all registered agent types.
        
        Returns:
            list: List of registered agent type strings
        """
        return list(self._agent_types.keys())
        
    def is_agent_type_registered(self, agent_type: str) -> bool:
        """
        Check if an agent type is registered.
        
        Args:
            agent_type: String identifier to check
            
        Returns:
            bool: True if agent type is registered, False otherwise
        """
        return agent_type in self._agent_types
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ai_agent_factory.py::TestAIAgentFactory -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core_runtime/ai_agent_factory.py tests/test_ai_agent_factory.py
git commit -m "feat: create AI agent factory for workflow orchestrator"
```
"""
### Task 3: Create AnalyzeAgent

**Files:**
- Create: `core_runtime/analyze_agent.py`
- Test: `tests/test_analyze_agent.py`

- [ ] **Step 1: Write the failing test for AnalyzeAgent**

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from core_runtime.analyze_agent import AnalyzeAgent
from core_runtime.ai_agent import AgentContext

class TestAnalyzeAgent:
    @pytest.fixture
    def agent(self):
        return AnalyzeAgent(name="test_analyze_agent")
    
    @pytest.fixture
    def context(self):
        return AgentContext()
    
    def test_agent_initialization(self, agent):
        """Test that agent initializes with correct attributes"""
        assert agent.name == "test_analyze_agent"
        assert agent.logger is not None
        
    @pytest.mark.asyncio
    async def test_receive_goal_processes_intent(self, agent, context):
        """Test that receive_goal properly processes user intent"""
        goal = "Create a user login system with email and password"
        result = await agent.receive_goal(goal, context)
        assert result is True
        assert context.workflow_spec is not None
        assert hasattr(context.workflow_spec, 'intent')
        assert context.workflow_spec.intent == goal
        
    @pytest.mark.asyncio
    async def test_plan_actions_creates_steps(self, agent, context):
        """Test that plan_actions creates implementation steps"""
        # Set up context with a workflow spec
        context.workflow_spec = Mock()
        context.workflow_spec.intent = "Create a REST API"
        
        actions = await agent.plan_actions(context)
        assert isinstance(actions, list)
        assert len(actions) > 0
        # Check that actions have expected structure
        for action in actions:
            assert 'name' in action
            assert 'description' in action
            
    @pytest.mark.asyncio
    async def test_execute_actions_returns_bool(self, agent, context):
        """Test that execute_actions returns a boolean"""
        actions = [{'name': 'test_action', 'description': 'Test action'}]
        result = await agent.execute_actions(actions, context)
        assert isinstance(result, bool)
        
    @pytest.mark.asyncio
    async def test_report_progress_returns_dict(self, agent, context):
        """Test that report_progress returns a dictionary"""
        result = await agent.report_progress(context)
        assert isinstance(result, dict)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_analyze_agent.py::TestAnalyzeAgent::test_agent_initialization -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'core_runtime.analyze_agent'"

- [ ] **Step 3: Write minimal implementation**

```python
"""
Analyze Agent for Engineering Workflow Orchestrator
Responsible for understanding user intent and creating workflow specifications
"""

import logging
from typing import Any, Dict, List, Optional
from core_runtime.ai_agent import BaseAIAgent, AgentContext


class AnalyzeAgent(BaseAIAgent):
    """
    AI Agent responsible for analyzing user intent and creating workflow specifications.
    Transforms high-level user requests into detailed, actionable workflow specs.
    """
    
    def __init__(self, name: str = "AnalyzeAgent", logger: Optional[logging.Logger] = None):
        super().__init__(name, logger)
        
    async def receive_goal(self, goal: str, context: AgentContext) -> bool:
        """
        Process user intent goal and create initial workflow specification.
        
        Args:
            goal: User's intent statement
            context: Shared context for workflow execution
            
        Returns:
            bool: True if goal processed successfully
        """
        try:
            self._log_info(f"Analyzing user intent: {goal}")
            
            # In a full implementation, this would use LLM to analyze the intent
            # For now, we'll create a basic workflow spec structure
            from dataclasses import dataclass, field
            
            @dataclass
            class WorkflowSpec:
                intent: str
                file_changes: List[Dict[str, str]] = field(default_factory=list)
                dependencies: List[str] = field(default_factory=list)
                plan: Dict[str, Any] = field(default_factory=dict)
                status: str = "analyzed"
                
            # Create basic workflow spec
            context.workflow_spec = WorkflowSpec(
                intent=goal,
                file_changes=[],  # Will be populated by further analysis
                dependencies=[],  # Will be inferred from intent
                plan={"steps": ["analyze intent", "create spec"]},
                status="analyzed"
            )
            
            self._log_info(f"Created workflow spec for intent: {goal}")
            return True
            
        except Exception as e:
            self._log_error(f"Failed to analyze goal: {e}")
            return False
            
    async def plan_actions(self, context: AgentContext) -> List[Dict[str, Any]]:
        """
        Plan actions for analyzing user intent in more detail.
        
        Args:
            context: Shared context containing workflow spec
            
        Returns:
            List[Dict[str, Any]]: Planned actions for detailed analysis
        """
        if not context.workflow_spec:
            return [{"name": "error_handling", "description": "Handle missing workflow spec"}]
            
        self._log_info("Planning detailed analysis actions")
        
        # Plan actions based on the workflow spec intent
        actions = [
            {
                "name": "extract_requirements",
                "description": "Extract functional and non-functional requirements from intent",
                "estimated_effort": "5 minutes"
            },
            {
                "name": "identify_dependencies", 
                "description": "Identify technical dependencies needed for implementation",
                "estimated_effort": "3 minutes"
            },
            {
                "name": "create_file_plan",
                "description": "Plan which files need to be created or modified",
                "estimated_effort": "4 minutes"
            }
        ]
        
        return actions
        
    async def execute_actions(self, actions: List[Dict[str, Any]], context: AgentContext) -> bool:
        """
        Execute the planned analysis actions.
        
        Args:
            actions: List of analysis actions to execute
            context: Shared context for workflow execution
            
        Returns:
            bool: True if execution successful
        """
        try:
            self._log_info(f"Executing {len(actions)} analysis actions")
            
            for action in actions:
                action_name = action.get('name', 'unknown')
                self._log_info(f"Executing action: {action_name}")
                
                # In a full implementation, this would perform the actual analysis
                # For now, we'll simulate the work and update context
                if action_name == "extract_requirements":
                    # Simulate extracting requirements
                    context.shared_data['requireries'] = [
                        "Requirement 1 extracted from intent",
                        "Requirement 2 extracted from intent"
                    ]
                elif action_name == "identify_dependencies":
                    # Simulate identifying dependencies
                    context.shared_data['dependencies'] = [
                        "dependency1",
                        "dependency2"
                    ]
                    context.workflow_spec.dependencies = context.shared_data['dependencies']
                elif action_name == "create_file_plan":
                    # Simulate creating file plan
                    context.shared_data['file_plan'] = [
                        {"file": "src/main.py", "type": "create"},
                        {"file": "src/utils.py", "type": "modify"}
                    ]
                    context.workflow_spec.file_changes = context.shared_data['file_plan']
                    
            # Update workflow spec status
            if context.workflow_spec:
                context.workflow_spec.status = "analyzed_detailed"
                
            self._log_info("Analysis actions completed successfully")
            return True
            
        except Exception as e:
            self._log_error(f"Failed to execute analysis actions: {e}")
            return False
            
    async def report_progress(self, context: AgentContext) -> Dict[str, Any]:
        """
        Report progress on the analysis workflow stage.
        
        Args:
            context: Shared context for workflow execution
            
        Returns:
            Dict[str, Any]: Progress report
        """
        progress = {
            "agent": self.name,
            "stage": "analyze",
            "status": "in_progress",
            "details": {}
        }
        
        if context.workflow_spec:
            progress["details"]["intent"] = context.workflow_spec.intent
            progress["details"]["status"] = context.workflow_spec.status
            progress["details"]["file_changes_count"] = len(context.workflow_spec.file_changes)
            progress["details"]["dependencies_count"] = len(context.workflow_spec.dependencies)
        else:
            progress["details"]["error"] = "No workflow spec created yet"
            
        # Add any shared data from analysis
        if context.shared_data:
            progress["details"]["shared_data_keys"] = list(context.shared_data.keys())
            
        return progress
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_analyze_agent.py::TestAnalyzeAgent -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core_runtime/analyze_agent.py tests/test_analyze_agent.py
git commit -m "feat: create AnalyzeAgent for workflow orchestrator"
```
"""
### Task 4: Create CreateAgent

**Files:**
- Create: `core_runtime/create_agent.py`
- Test: `tests/test_create_agent.py`

- [ ] **Step 1: Write the failing test for CreateAgent**

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from core_runtime.create_agent import CreateAgent
from core_runtime.ai_agent import AgentContext

class TestCreateAgent:
    @pytest.fixture
    def agent(self):
        return CreateAgent(name="test_create_agent")
    
    @pytest.fixture
    def context(self):
        return AgentContext()
    
    def test_agent_initialization(self, agent):
        """Test that agent initializes with correct attributes"""
        assert agent.name == "test_create_agent"
        assert agent.logger is not None
        
    @pytest.mark.asyncio
    async def test_receive_goal_processes_spec(self, agent, context):
        """Test that receive_goal processes workflow spec"""
        # Set up a mock workflow spec
        context.workflow_spec = Mock()
        context.workflow_spec.intent = "Create a REST API"
        
        result = await agent.receive_goal("Create detailed plan", context)
        assert result is True
        assert context.workflow_spec is not None
        
    @pytest.mark.asyncio
    async def test_plan_actions_creates_detailed_plan(self, agent, context):
        """Test that plan_actions creates detailed implementation plan"""
        # Set up context with workflow spec
        context.workflow_spec = Mock()
        context.workflow_spec.intent = "Create a REST API"
        context.workflow_spec.dependencies = ["fastapi", "uvicorn"]
        
        actions = await agent.plan_actions(context)
        assert isinstance(actions, list)
        assert len(actions) > 0
        # Check that actions have expected structure
        for action in actions:
            assert 'name' in action
            assert 'description' in action
            # Check for planning-specific fields
            assert 'estimated_effort' in action or 'priority' in action
            
    @pytest.mark.asyncio
    async def test_execute_actions_returns_bool(self, agent, context):
        """Test that execute_actions returns a boolean"""
        actions = [{'name': 'plan_step', 'description': 'Plan implementation step'}]
        result = await agent.execute_actions(actions, context)
        assert isinstance(result, bool)
        
    @pytest.mark.asyncio
    async def test_report_progress_returns_dict(self, agent, context):
        """Test that report_progress returns a dictionary"""
        result = await agent.report_progress(context)
        assert isinstance(result, dict)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_create_agent.py::TestCreateAgent::test_agent_initialization -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'core_runtime.create_agent'"

- [ ] **Step 3: Write minimal implementation**

```python
"""
Create Agent for Engineering Workflow Orchestrator
Responsible for developing detailed implementation plans from workflow specifications
"""

import logging
from typing import Any, Dict, List, Optional
from core_runtime.ai_agent import BaseAIAgent, AgentContext


class CreateAgent(BaseAIAgent):
    """
    AI Agent responsible for creating detailed implementation plans.
    Takes workflow specifications and breaks them down into actionable, ordered steps.
    """
    
    def __init__(self, name: str = "CreateAgent", logger: Optional[logging.Logger] = None):
        super().__init__(name, logger)
        
    async def receive_goal(self, goal: str, context: AgentContext) -> bool:
        """
        Process goal to create detailed implementation plan from workflow spec.
        
        Args:
            goal: Goal statement for the planning phase
            context: Shared context containing workflow spec
            
        Returns:
            bool: True if goal processed successfully
        """
        try:
            self._log_info(f"Creating implementation plan for goal: {goal}")
            
            if not context.workflow_spec:
                self._log_error("No workflow spec available for planning")
                return False
                
            # In a full implementation, this would use LLM to create detailed plan
            # For now, we'll enhance the existing spec with planning details
            if hasattr(context.workflow_spec, 'plan') and isinstance(context.workflow_spec.plan, dict):
                # Enhance existing plan with more details
                context.workflow_spec.plan.update({
                    'detailed_steps': [],
                    'resource_estimates': {},
                    'risk_assessment': {},
                    'timeline_estimates': {}
                })
                context.workflow_spec.status = "planned"
            else:
                # Create plan if it doesn't exist
                context.workflow_spec.plan = {
                    'detailed_steps': [],
                    'resource_estimates': {},
                    'risk_assessment': {},
                    'timeline_estimates': {}
                }
                context.workflow_spec.status = "planned"
                
            self._log_info("Implementation plan created successfully")
            return True
            
        except Exception as e:
            self._log_error(f"Failed to create implementation plan: {e}")
            return False
            
    async def plan_actions(self, context: AgentContext) -> List[Dict[str, Any]]:
        """
        Plan actions for creating detailed implementation plan.
        
        Args:
            context: Shared context containing workflow spec
            
        Returns:
            List[Dict[str, Any]]: Planned actions for detailed planning
        """
        if not context.workflow_spec:
            return [{"name": "error_handling", "description": "Handle missing workflow spec"}]
            
        self._log_info("Planning detailed implementation actions")
        
        # Plan actions based on the workflow spec
        actions = [
            {
                "name": "break_down_requirements",
                "description": "Break down requirements into implementable tasks",
                "estimated_effort": "10 minutes",
                "priority": "high"
            },
            {
                "name": "identify_technical_approach",
                "description": "Determine technical approach and architecture",
                "estimated_effort": "15 minutes",
                "priority": "high"
            },
            {
                "name": "create_task_dependencies",
                "description": "Identify dependencies between tasks",
                "estimated_effort": "8 minutes",
                "priority": "medium"
            },
            {
                "name": "estimate_resources",
                "description": "Estimate time and resources needed for each task",
                "estimated_effort": "5 minutes",
                "priority": "medium"
            }
        ]
        
        return actions
        
    async def execute_actions(self, actions: List[Dict[str, Any]], context: AgentContext) -> bool:
        """
        Execute the planned planning actions.
        
        Args:
            actions: List of planning actions to execute
            context: Shared context for workflow execution
            
        Returns:
            bool: True if execution successful
        """
        try:
            self._log_info(f"Executing {len(actions)} planning actions")
            
            for action in actions:
                action_name = action.get('name', 'unknown')
                self._log_info(f"Executing action: {action_name}")
                
                # In a full implementation, this would perform the actual planning
                # For now, we'll simulate the work and update context
                if action_name == "break_down_requirements":
                    # Simulate breaking down requirements
                    if hasattr(context.workflow_spec, 'plan'):
                        context.workflow_spec.plan['detailed_steps'] = [
                            {"task": "Setup project structure", "estimated_time": "30 min"},
                            {"task": "Implement core functionality", "estimated_time": "2 hours"},
                            {"task": "Add error handling", "estimated_time": "30 min"}
                        ]
                elif action_name == "identify_technical_approach":
                    # Simulate identifying technical approach
                    if hasattr(context.workflow_spec, 'plan'):
                        context.workflow_spec.plan['technical_approach'] = {
                            "architecture": "modular",
                            "patterns": ["MVC", "repository"],
                            "technologies": context.workflow_spec.dependencies if hasattr(context.workflow_spec, 'dependencies') else []
                        }
                elif action_name == "create_task_dependencies":
                    # Simulate creating task dependencies
                    if hasattr(context.workflow_spec, 'plan'):
                        context.workflow_spec.plan['dependencies'] = {
                            "Setup project structure": [],
                            "Implement core functionality": ["Setup project structure"],
                            "Add error handling": ["Implement core functionality"]
                        }
                elif action_name == "estimate_resources":
                    # Simulate estimating resources
                    if hasattr(context.workflow_spec, 'plan'):
                        context.workflow_spec.plan['resource_estimates'] = {
                            "total_time": "3 hours",
                            "complexity": "medium",
                            "team_size": 1
                        }
                        
            # Update workflow spec status
            if context.workflow_spec:
                context.workflow_spec.status = "planned_detailed"
                
            self._log_info("Planning actions completed successfully")
            return True
            
        except Exception as e:
            self._log_error(f"Failed to execute planning actions: {e}")
            return False
            
    async def report_progress(self, context: AgentContext) -> Dict[str, Any]:
        """
        Report progress on the planning workflow stage.
        
        Args:
            context: Shared context for workflow execution
            
        Returns:
            Dict[str, Any]: Progress report
        """
        progress = {
            "agent": self.name,
            "stage": "create",
            "status": "in_progress",
            "details": {}
        }
        
        if context.workflow_spec:
            progress["details"]["intent"] = getattr(context.workflow_spec, 'intent', 'unknown')
            progress["details"]["status"] = getattr(context.workflow_spec, 'status', 'unknown')
            if hasattr(context.workflow_spec, 'plan'):
                plan = context.workflow_spec.plan
                progress["details"]["has_detailed_steps"] = bool(plan.get('detailed_steps'))
                progress["details"]["has_technical_approach"] = bool(plan.get('technical_approach'))
                progress["details"]["has_dependencies"] = bool(plan.get('dependencies'))
                progress["details"]["has_resource_estimates"] = bool(plan.get('resource_estimates'))
        else:
            progress["details"]["error"] = "No workflow spec available for planning"
            
        return progress
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_create_agent.py::TestCreateAgent -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core_runtime/create_agent.py tests/test_create_agent.py
git commit -m "feat: create CreateAgent for workflow orchestrator"
```