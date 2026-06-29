from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppSettings:
    graph_provider: str = "prepared_json"
    neo4j_uri: str | None = None
    neo4j_user: str | None = None
    neo4j_password: str | None = None


def load_settings() -> AppSettings:
    return AppSettings(
        graph_provider=os.getenv("GRAPH_PROVIDER", "prepared_json"),
        neo4j_uri=os.getenv("NEO4J_URI"),
        neo4j_user=os.getenv("NEO4J_USER"),
        neo4j_password=os.getenv("NEO4J_PASSWORD"),
    )
