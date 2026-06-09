"""以 NetworkX 建構敘事知識圖。"""
from __future__ import annotations

from typing import Any

import networkx as nx

from src.schemas import Event, ExtractionResult


def build_knowledge_graph(extraction: ExtractionResult) -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    g.graph["project_id"] = (
        extraction.characters[0].project_id
        if extraction.characters
        else extraction.events[0].project_id
        if extraction.events
        else ""
    )

    def _add_node(nid: str, ntype: str, label: str, **attrs: Any) -> None:
        g.add_node(nid, node_type=ntype, label=label, **attrs)

    for c in extraction.characters:
        _add_node(f"char:{c.name}", "character", c.name, traits=c.traits, abilities=c.abilities)
    for loc in extraction.locations:
        _add_node(f"loc:{loc.name}", "location", loc.name, description=loc.description)
    for obj in extraction.objects:
        _add_node(f"obj:{obj.name}", "object", obj.name)
        if obj.location:
            g.add_edge(f"obj:{obj.name}", f"loc:{obj.location}", relation="at_location")
        if obj.owner:
            g.add_edge(f"char:{obj.owner}", f"obj:{obj.name}", relation="owns")
    for i, ev in enumerate(extraction.events):
        eid = f"event:{ev.id[:8]}"
        label = _event_label(ev)
        _add_node(eid, "event", label[:40], order=i, action=ev.action, subject=ev.subject, object=ev.object)
        if ev.location:
            g.add_edge(eid, f"loc:{ev.location}", relation="happens_at")
        if ev.subject:
            g.add_edge(f"char:{ev.subject}", eid, relation="acts")
    for rule in extraction.world_rules:
        _add_node(
            f"rule:{rule.id[:8]}",
            "world_rule",
            (rule.rule_text or "")[:50],
            subject=rule.subject,
            constraint=rule.constraint,
            condition=rule.condition,
        )

    return g


def _event_label(ev: Event) -> str:
    parts = []
    if ev.subject:
        parts.append(ev.subject)
    if ev.action:
        parts.append(ev.action)
    if ev.object:
        parts.append(ev.object)
    if not parts:
        return (ev.evidence or "事件").strip()
    return "".join(parts)


def graph_to_pyvis_html(g: nx.MultiDiGraph, height: str = "500px") -> str:
    try:
        from pyvis.network import Network
    except ImportError:
        return "<p>請安裝 pyvis</p>"

    net = Network(height=height, directed=True, notebook=False)
    net.barnes_hut()

    color_map = {
        "character": "#4e9af1",
        "location": "#6bcb77",
        "object": "#ffd93d",
        "event": "#ff6b6b",
        "world_rule": "#c77dff",
    }

    for nid, data in g.nodes(data=True):
        ntype = data.get("node_type", "unknown")
        net.add_node(
            nid,
            label=data.get("label", nid),
            color=color_map.get(ntype, "#aaaaaa"),
            title=str(data),
        )

    for u, v, data in g.edges(data=True):
        net.add_edge(u, v, title=data.get("relation", ""))

    return net.generate_html()


def graph_stats(g: nx.MultiDiGraph) -> dict[str, int]:
    types: dict[str, int] = {}
    for _, data in g.nodes(data=True):
        t = data.get("node_type", "other")
        types[t] = types.get(t, 0) + 1
    return {"nodes": g.number_of_nodes(), "edges": g.number_of_edges(), **types}
