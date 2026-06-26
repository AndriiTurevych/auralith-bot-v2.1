from dataclasses import dataclass


@dataclass(frozen=True)
class Agent:
    key: str
    title: str
    domain: str
    system_prompt: str
    web_search: bool = False
