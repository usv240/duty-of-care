"""Vertex AI Agent Engine entry point: the same agent, managed by Google Cloud."""

from __future__ import annotations

from vertexai.agent_engines import AdkApp

from duty_of_care_agent.agent import root_agent

app = AdkApp(agent=root_agent, enable_tracing=False)
