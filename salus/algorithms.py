"""Track 01 — FalkorDB graph algorithms as agent tools."""

from __future__ import annotations

from typing import Any

from salus.graph import query


def pagerank_systems(tenant_id: str | None = None, limit: int = 10) -> dict[str, Any]:
    """Influence ranking over System DEPENDS_ON edges."""
    lim = max(1, min(int(limit), 50))
    cypher = f"""
    CALL algo.pageRank('System', 'DEPENDS_ON')
    YIELD node, score
    RETURN node.name AS name, node.domain AS domain, score
    ORDER BY score DESC
    LIMIT {lim}
    """
    rows = query(cypher, readonly=True, tenant_id=tenant_id)
    return {
        "algorithm": "algo.pageRank",
        "ranking": [{"name": r[0], "domain": r[1], "score": r[2]} for r in rows],
        "cypher": cypher.strip(),
    }


def betweenness_systems(tenant_id: str | None = None, limit: int = 10) -> dict[str, Any]:
    """Bridge nodes in the dependency graph."""
    lim = max(1, min(int(limit), 50))
    cypher = f"""
    CALL algo.betweenness({{nodeLabels: ['System'], relationshipTypes: ['DEPENDS_ON']}})
    YIELD node, score
    RETURN node.name AS name, node.domain AS domain, score
    ORDER BY score DESC
    LIMIT {lim}
    """
    rows = query(cypher, readonly=True, tenant_id=tenant_id)
    return {
        "algorithm": "algo.betweenness",
        "ranking": [{"name": r[0], "domain": r[1], "score": r[2]} for r in rows],
        "cypher": cypher.strip(),
    }


def connected_components(tenant_id: str | None = None) -> dict[str, Any]:
    """Weakly connected components over System DEPENDS_ON."""
    cypher = """
    CALL algo.WCC({nodeLabels: ['System'], relationshipTypes: ['DEPENDS_ON']})
    YIELD node, componentId
    RETURN componentId, collect(node.name) AS systems
    ORDER BY componentId
    """
    rows = query(cypher, readonly=True, tenant_id=tenant_id)
    return {
        "algorithm": "algo.WCC",
        "components": [{"component_id": r[0], "systems": r[1]} for r in rows],
        "cypher": cypher.strip(),
    }


def shortest_dependency_path(
    source: str, target: str, tenant_id: str | None = None, max_hops: int = 6
) -> dict[str, Any]:
    hops = max(1, min(int(max_hops), 8))
    cypher = f"""
    MATCH (a:System {{name: $source}}), (b:System {{name: $target}})
    RETURN [n IN nodes(shortestPath((a)-[:DEPENDS_ON*..{hops}]->(b))) | n.name] AS path,
           length(shortestPath((a)-[:DEPENDS_ON*..{hops}]->(b))) AS hops
    """
    rows = query(cypher, {"source": source, "target": target}, readonly=True, tenant_id=tenant_id)
    if not rows or rows[0][0] is None:
        # Try SPpaths as fallback
        cypher2 = """
        MATCH (a:System {name: $source}), (b:System {name: $target})
        CALL algo.SPpaths({sourceNode: a, targetNode: b, relTypes: ['DEPENDS_ON'], maxLen: 6})
        YIELD path
        RETURN [n IN nodes(path) | n.name] AS names, length(path) AS hops
        LIMIT 1
        """
        rows2 = query(cypher2, {"source": source, "target": target}, readonly=True, tenant_id=tenant_id)
        if not rows2:
            return {"found": False, "source": source, "target": target}
        return {
            "found": True,
            "algorithm": "algo.SPpaths",
            "path": rows2[0][0],
            "hops": rows2[0][1],
            "cypher": cypher2.strip(),
        }
    return {
        "found": True,
        "algorithm": "shortestPath",
        "path": rows[0][0],
        "hops": rows[0][1],
        "cypher": cypher.strip(),
    }


def bfs_from_system(system_name: str, max_depth: int = 3, tenant_id: str | None = None) -> dict[str, Any]:
    depth = max(1, min(int(max_depth), 6))
    cypher = f"""
    MATCH (a:System {{name: $name}})
    CALL algo.BFS(a, {depth}, 'DEPENDS_ON')
    YIELD nodes
    RETURN [n IN nodes | n.name] AS reached
    """
    rows = query(cypher, {"name": system_name}, readonly=True, tenant_id=tenant_id)
    reached = rows[0][0] if rows else []
    return {
        "algorithm": "algo.BFS",
        "source": system_name,
        "max_depth": depth,
        "reached": reached or [],
        "cypher": cypher.strip(),
    }
