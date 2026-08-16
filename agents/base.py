"""
Base agent class with Google Gemini integration.
All agents inherit from this class, getting standardized logging,
cost tracking, and inter-agent message formatting.
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from google import genai
from google.genai import types

from utils.cost_tracker import CostTracker


@dataclass
class AgentMessage:
    """Standardized message format for inter-agent communication."""
    sender: str
    receiver: str
    message_type: str  # "request", "response", "error", "retry"
    content: Any
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "type": self.message_type,
            "content": self.content if isinstance(self.content, (str, dict, list)) else str(self.content),
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class BaseAgent:
    """Base class for all PaperMiner agents."""

    def __init__(
        self,
        name: str,
        role: str,
        model_name: str = "gemini-flash-latest",
        cost_tracker: Optional[CostTracker] = None,
    ):
        self.name = name
        self.role = role
        self.model_name = model_name
        self.cost_tracker = cost_tracker or CostTracker()
        self.interaction_log: list[AgentMessage] = []
        self._client: Optional[genai.Client] = None

    @property
    def client(self) -> genai.Client:
        """Lazy-init Gemini client."""
        if self._client is None:
            import os
            key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if key:
                self._client = genai.Client(api_key=key)
            else:
                self._client = genai.Client()
        return self._client

    def call_llm(
        self,
        prompt: str,
        system_instruction: str = "",
        task_description: str = "",
        temperature: float = 0.2,
        response_mime_type: Optional[str] = None,
        response_schema: Optional[Any] = None,
    ) -> str:
        """Make a call to Gemini with full cost tracking."""
        start_time = time.time()

        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction or f"You are {self.name}, a specialized AI agent. Role: {self.role}",
        )
        if response_mime_type:
            config.response_mime_type = response_mime_type
        if response_schema:
            config.response_schema = response_schema

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )

        duration = time.time() - start_time

        # Track costs
        input_tokens = response.usage_metadata.prompt_token_count or 0
        output_tokens = response.usage_metadata.candidates_token_count or 0

        self.cost_tracker.record_call(
            agent_name=self.name,
            task_description=task_description or "LLM call",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_seconds=duration,
        )

        return response.text or ""

    def call_llm_json(
        self,
        prompt: str,
        system_instruction: str = "",
        task_description: str = "",
        temperature: float = 0.1,
        response_schema: Optional[Any] = None,
    ) -> Any:
        """Make a Gemini call that returns parsed JSON."""
        raw = self.call_llm(
            prompt=prompt,
            system_instruction=system_instruction,
            task_description=task_description,
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=response_schema,
        )
        return json.loads(raw)

    def send_message(
        self,
        receiver: str,
        message_type: str,
        content: Any,
        metadata: Optional[dict] = None,
    ) -> AgentMessage:
        """Create and log a message to another agent."""
        msg = AgentMessage(
            sender=self.name,
            receiver=receiver,
            message_type=message_type,
            content=content,
            metadata=metadata or {},
        )
        self.interaction_log.append(msg)
        return msg

    def receive_message(self, message: AgentMessage) -> None:
        """Log a received message."""
        self.interaction_log.append(message)

    def get_interaction_log(self) -> list[dict]:
        """Return the full interaction log as serializable dicts."""
        return [msg.to_dict() for msg in self.interaction_log]
