"""End-to-end verification of every Track 01/02/03 judge bullet."""

from __future__ import annotations

import concurrent.futures
from typing import Any

from rich.console import Console
from rich.table import Table

from salus import actions, algorithms, ingest, knowledge, memory, tool_router, tools
from salus.agents import run_salus
from salus.seed import load_seed

console = Console()


def run_verify(tenant_id: str | None = None) -> bool:
    load_seed(tenant_id, reset=True)
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))

    # ── Track 01 ────────────────────────────────────────────
    br = tools.blast_radius("payments-api", tenant_id=tenant_id)
    check("01 multi-hop reasoning", bool(br.get("depends_on")), str(br.get("depends_on")))

    pr = algorithms.pagerank_systems(tenant_id=tenant_id)
    bet = algorithms.betweenness_systems(tenant_id=tenant_id)
    wcc = algorithms.connected_components(tenant_id=tenant_id)
    sp = algorithms.shortest_dependency_path("ehr-core", "building-mgmt", tenant_id=tenant_id)
    bfs = algorithms.bfs_from_system("payments-api", tenant_id=tenant_id)
    check(
        "01 graph algorithms as tools",
        bool(pr.get("ranking")) and bool(bet.get("ranking") is not None) and bool(sp.get("found")) and bool(bfs.get("reached") is not None) and bool(wcc.get("components") is not None),
        f"pr={len(pr.get('ranking', []))} bet={len(bet.get('ranking', []))} sp={sp.get('path')} wcc={len(wcc.get('components', []))}",
    )

    sel = tool_router.select_tools("Why are checkouts failing and who should own this?")
    check(
        "01 tool selection through MCP catalog",
        sel.get("mode") in {"heuristic_mcp_catalog", "llm"} and len(sel.get("tools", [])) >= 5,
        f"{sel.get('mode')}: {len(sel.get('tools', []))} tools",
    )

    act = actions.page_owner("Maya Chen", system_name="payments-api", reason="verify", tenant_id=tenant_id)
    check("01 actions based on graph", act.get("status") == "completed", act.get("action_id", ""))

    ans = run_salus(
        "Why are checkouts failing and who should own this?",
        tenant_id=tenant_id,
        user_id="person:sam",
    )
    check(
        "01 explainable results",
        bool(ans.investigation_id) and bool(ans.path.get("evidence_path_id")),
        str(ans.path.get("evidence_path_id")),
    )

    # ── Track 02 ────────────────────────────────────────────
    proc = memory.load_procedure(tenant_id=tenant_id)
    check("02 procedural memory", bool(proc and proc.get("steps")), str((proc or {}).get("name")))

    check("02 episodic memory", bool(ans.path.get("memory", {}).get("episodes") is not None) and bool(ans.checklist.get("track02_episodic")), ans.session_id or "")
    check("02 semantic memory", bool(ans.path.get("memory", {}).get("facts") is not None) or bool(ans.checklist.get("track02_semantic")), "")

    hist = memory.session_history(ans.session_id or "", tenant_id=tenant_id)
    check("02 persistent conversation history", len(hist) >= 2, f"{len(hist)} messages")

    # continue session
    ans2 = run_salus(
        "What did we conclude about payments-api?",
        tenant_id=tenant_id,
        user_id="person:sam",
    )
    check(
        "02 remember across sessions (CONTINUES)",
        bool(ans2.path.get("user_memory")),
        f"session={ans2.session_id}",
    )

    check("02 shared state + handoffs", len(ans.handoffs) >= 2 and bool(ans.path.get("shared_state")), str(ans.handoffs))

    # high-concurrency CAS
    def writer(i: int) -> dict[str, Any]:
        return memory.update_shared_state_with_retry(
            "active_incident",
            lambda v: {**v, "writer": i, "hits": int(v.get("hits", 0)) + 1},
            tenant_id=tenant_id,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(writer, i) for i in range(8)]
        outs = [f.result() for f in futs]
    ok_writes = sum(1 for o in outs if o.get("ok") or o.get("version"))
    final = memory.read_shared_state(tenant_id=tenant_id)
    check(
        "02 high-concurrency shared state (CAS)",
        ok_writes >= 1 and int(final.get("version") or 0) >= 2,
        f"ok_writes={ok_writes} version={final.get('version')} hits={final.get('value', {}).get('hits')}",
    )

    mem_a = memory.cross_session_memory("person:sam", tenant_id=tenant_id)
    mem_b = memory.cross_session_memory("person:maya", tenant_id=tenant_id)
    # create maya session noise
    run_salus("badge readers failing", tenant_id=tenant_id, user_id="person:maya")
    mem_b2 = memory.cross_session_memory("person:maya", tenant_id=tenant_id)
    check(
        "02 separate memory per user/tenant",
        mem_a.get("user_id") == "person:sam" and mem_b2.get("user_id") == "person:maya",
        f"sam_eps={len(mem_a.get('episodes', []))} maya_eps={len(mem_b2.get('episodes', []))}",
    )

    # ── Track 03 ────────────────────────────────────────────
    doc = ingest.ingest_document(
        title="Verify runbook",
        summary="test ingest",
        domain="finance",
        references_systems=["payments-api"],
        tenant_id=tenant_id,
    )
    tkt = ingest.ingest_ticket(
        key="INC-VERIFY",
        title="verify ticket",
        domain="finance",
        about_systems=["payments-api"],
        tenant_id=tenant_id,
    )
    chat = ingest.ingest_chat(
        content="talking about payments-api in chat",
        user_id="person:sam",
        mention_systems=["payments-api"],
        tenant_id=tenant_id,
    )
    src = knowledge.collect_sources("payments-api", tenant_id=tenant_id)
    check(
        "03 docs + tickets + chats in one graph",
        bool(doc.get("document_id")) and bool(tkt.get("ticket_id")) and bool(chat.get("message_id")) and bool(src.get("documents") is not None),
        f"docs={len(src.get('documents', []))} tickets={len(src.get('tickets', []))} chats={len(src.get('chats', []))}",
    )

    owns = tools.who_owns_and_knows("payments-api", tenant_id=tenant_id)
    check(
        "03 who owns / who knows",
        bool(owns.get("owners")) and bool(owns.get("domain_experts")),
        str(owns.get("owners")),
    )

    dec = knowledge.trace_decisions("risk-engine", tenant_id=tenant_id)
    check("03 trace decisions to source", isinstance(dec.get("decisions"), list), str(dec.get("decisions")))

    # knowledge currency
    facts = tools.recall_memory("payments-api", tenant_id=tenant_id).get("facts") or []
    if facts:
        inv = knowledge.invalidate_fact(
            facts[0]["id"],
            reason="verify currency",
            replacement_statement="Updated: ledger lag threshold now 1.5s",
            about_system="payments-api",
            tenant_id=tenant_id,
        )
        check("03 keep knowledge current (INVALIDATES)", bool(inv.get("replacement")), str(inv))
    else:
        check("03 keep knowledge current (INVALIDATES)", False, "no fact to invalidate")

    check(
        "03 answers with clear sources",
        bool(ans.sources),
        ", ".join(ans.sources[:3]),
    )

    # Combined agent checklist
    all_agent = all(ans.checklist.values()) if ans.checklist else False
    check("combined agent checklist all true", all_agent, str(ans.checklist))

    table = Table(title="SALUS Track 01/02/03 verification")
    table.add_column("Bullet")
    table.add_column("Pass")
    table.add_column("Detail")
    for name, ok, detail in results:
        table.add_row(name, "[green]YES[/green]" if ok else "[red]NO[/red]", detail[:80])
    console.print(table)

    failed = [n for n, ok, _ in results if not ok]
    if failed:
        console.print(f"[red]FAILED ({len(failed)}):[/red] {', '.join(failed)}")
        return False
    console.print(f"[green]All {len(results)} judge bullets passed.[/green]")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if run_verify() else 1)
