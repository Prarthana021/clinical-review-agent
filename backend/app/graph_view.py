from __future__ import annotations

from typing import Any, Dict, List


DISPLAY_RELATIONSHIP_TYPES = {
    "SUBMITS",
    "INCLUDES_CONDITION",
    "REQUIRES_RELATIONSHIP",
    "DOCUMENTS",
    "SUPPORTS",
    "SUPPORTS_RELATIONSHIP",
    "CONTRADICTS",
    "CONTRADICTS_RELATIONSHIP",
    "SUPERSEDES",
    "WEAKENS",
    "SATISFIES",
    "FAILS_TO_SATISFY",
}


def build_graph_view(case: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    graph = case["graph"]
    relationships = [
        relationship
        for relationship in graph["relationships"]
        if relationship["type"] in DISPLAY_RELATIONSHIP_TYPES
    ]
    visible_node_ids = {
        node_id
        for relationship in relationships
        for node_id in (relationship["source"], relationship["target"])
    }

    return {
        "nodes": [node for node in graph["nodes"] if node["id"] in visible_node_ids],
        "relationships": relationships,
    }
