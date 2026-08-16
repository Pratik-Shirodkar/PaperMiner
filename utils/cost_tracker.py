"""
Cost tracker utility for monitoring Gemini API usage across agents.
Tracks tokens and estimated costs per agent per call.
"""

import time
from dataclasses import dataclass, field
from typing import Optional


# Gemini 2.5 Flash pricing
# Input: $0.10 per 1M tokens, Output: $0.40 per 1M tokens
GEMINI_FLASH_INPUT_COST_PER_TOKEN = 0.10 / 1_000_000
GEMINI_FLASH_OUTPUT_COST_PER_TOKEN = 0.40 / 1_000_000


@dataclass
class AgentCall:
    """Record of a single agent LLM call."""
    agent_name: str
    task_description: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    duration_seconds: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class CostTracker:
    """Tracks token usage and costs across all agents."""
    calls: list[AgentCall] = field(default_factory=list)

    def record_call(
        self,
        agent_name: str,
        task_description: str,
        input_tokens: int,
        output_tokens: int,
        duration_seconds: float,
    ) -> AgentCall:
        """Record an API call and compute its cost."""
        cost = (
            input_tokens * GEMINI_FLASH_INPUT_COST_PER_TOKEN
            + output_tokens * GEMINI_FLASH_OUTPUT_COST_PER_TOKEN
        )
        call = AgentCall(
            agent_name=agent_name,
            task_description=task_description,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            duration_seconds=duration_seconds,
        )
        self.calls.append(call)
        return call

    @property
    def total_cost_usd(self) -> float:
        return sum(c.cost_usd for c in self.calls)

    @property
    def total_input_tokens(self) -> int:
        return sum(c.input_tokens for c in self.calls)

    @property
    def total_output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.calls)

    def get_agent_summary(self) -> dict[str, dict]:
        """Get cost breakdown per agent."""
        summary: dict[str, dict] = {}
        for call in self.calls:
            if call.agent_name not in summary:
                summary[call.agent_name] = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                    "total_duration": 0.0,
                }
            s = summary[call.agent_name]
            s["calls"] += 1
            s["input_tokens"] += call.input_tokens
            s["output_tokens"] += call.output_tokens
            s["cost_usd"] += call.cost_usd
            s["total_duration"] += call.duration_seconds
        return summary

    def format_report(self) -> str:
        """Generate a human-readable cost report."""
        lines = [
            "═" * 60,
            "  COST & TOKEN USAGE REPORT",
            "═" * 60,
            "",
        ]
        summary = self.get_agent_summary()
        for agent, stats in summary.items():
            lines.append(f"  Agent: {agent}")
            lines.append(f"    Calls:         {stats['calls']}")
            lines.append(f"    Input tokens:  {stats['input_tokens']:,}")
            lines.append(f"    Output tokens: {stats['output_tokens']:,}")
            lines.append(f"    Cost:          ${stats['cost_usd']:.6f}")
            lines.append(f"    Duration:      {stats['total_duration']:.1f}s")
            lines.append("")

        lines.append("─" * 60)
        lines.append(f"  TOTAL INPUT TOKENS:  {self.total_input_tokens:,}")
        lines.append(f"  TOTAL OUTPUT TOKENS: {self.total_output_tokens:,}")
        lines.append(f"  TOTAL COST:          ${self.total_cost_usd:.6f}")
        lines.append("═" * 60)
        return "\n".join(lines)
