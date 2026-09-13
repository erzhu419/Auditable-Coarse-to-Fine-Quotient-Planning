"""Replay declared history-dependent actions from the V13 retained execution tree."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

Key = tuple[int, tuple[int, ...]]
SCHEMA = "controlled_predictive_recorded_history_policy_v13"


def _key(record: Sequence[Any]) -> Key:
    return record[0], tuple(record[1])


def _policy_node(trace: Mapping[str, Any]) -> dict[str, Any]:
    result = {"key": trace["key"]}
    if "action" not in trace:
        result["status"] = trace["status"]
    else:
        result["action"] = trace["action"]
        result["children"] = [_policy_node(edge["node"]) for edge in trace["children"]]
    return result


def freeze_history_payload(queries: Mapping[str, Mapping[str, float]],
                           traces: Mapping[str, Mapping[str, Any]],
                           metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Retain action histories, omitting environment probabilities and model rows."""
    return {
        "schema": SCHEMA,
        "scope": "Replay of retained histories under the fixed V13 observation stream",
        "metadata": dict(metadata), "query_order": list(traces),
        "queries": {name: dict(queries[name]) for name in traces},
        "policies": {name: _policy_node(trace) for name, trace in traces.items()},
    }


class RecordedHistoryPolicy:
    """An action depends on the complete recorded path, including repeated boards."""

    def __init__(self, payload: Mapping[str, Any]):
        if payload["schema"] != SCHEMA:
            raise ValueError("not a V13 recorded-history policy")
        self.payload = payload

    def action(self, query_name: str, history: Sequence[Key]) -> str | None:
        node = self.payload["policies"][query_name]
        if not history or history[0] != _key(node["key"]):
            raise ValueError("history must start at this declared query root")
        for key in history[1:]:
            matches = [child for child in node.get("children", ()) if _key(child["key"]) == key]
            if not matches:
                raise ValueError("this history is outside the retained execution tree")
            node = matches[0]
        return node.get("action")


def replay_all_histories(payload: Mapping[str, Any]) -> dict[str, Any]:
    policy = RecordedHistoryPolicy(payload)
    decisions = []
    terminal_count = 0
    for name in payload["query_order"]:
        def visit(node: Mapping[str, Any], ancestors: tuple[Key, ...]) -> None:
            nonlocal terminal_count
            history = (*ancestors, _key(node["key"]))
            action = policy.action(name, history)
            if action is None:
                terminal_count += 1
            else:
                decisions.append({"query_name": name,
                    "history": [[h, list(board)] for h, board in history], "action": action})
            for child in node.get("children", ()):
                visit(child, history)
        visit(payload["policies"][name], ())
    return {"query_root_actions": {name: policy.action(name, (_key(payload["policies"][name]["key"]),))
                                   for name in payload["query_order"]},
        "decisions": decisions, "decision_count": len(decisions),
        "terminal_history_count": terminal_count,
        "new_planning_observations": 0,
        "scope": "Recorded-history replay; no online acquisition or new-policy evaluation"}
