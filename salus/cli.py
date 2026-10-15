"""SALUS CLI — ask the universal org agent."""

from __future__ import annotations

import json
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from salus.agents import run_salus
from salus.config import settings

app = typer.Typer(add_completion=False, help="SALUS — universal org nerve agent")
console = Console()


@app.command()
def ask(
    question: str = typer.Argument(..., help="Natural language question or incident description"),
    tenant: Optional[str] = typer.Option(None, "--tenant", "-t"),
    user: str = typer.Option("person:sam", "--user", "-u", help="Per-user memory id"),
    session: Optional[str] = typer.Option(None, "--session", "-s"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Run full multi-agent loop against FalkorDB."""
    result = run_salus(question, tenant_id=tenant, user_id=user, session_id=session)
    if json_out:
        console.print_json(
            json.dumps(
                {
                    "answer": result.answer,
                    "domain": result.domain,
                    "system": result.system,
                    "owners": result.owners,
                    "confidence": result.confidence,
                    "actions": result.actions,
                    "sources": result.sources,
                    "evidence": result.evidence_summary,
                    "handoffs": result.handoffs,
                    "investigation_id": result.investigation_id,
                    "session_id": result.session_id,
                    "user_id": result.user_id,
                    "tool_selection": result.tool_selection,
                    "checklist": result.checklist,
                    "path": result.path,
                    "graph": settings.graph_name,
                },
                default=str,
            )
        )
        return

    console.print(
        Panel(
            result.answer,
            title=f"SALUS · {settings.graph_prefix}:{tenant or settings.tenant_id}",
            subtitle=f"confidence {result.confidence:.0%}",
        )
    )
    console.print("[bold]Handoffs[/bold]")
    for h in result.handoffs:
        console.print(f"  • {h}")
    if result.tool_selection:
        console.print(
            f"[bold]Tool selection[/bold] ({result.tool_selection.get('mode')}): "
            f"{', '.join(result.tool_selection.get('tools', []))}"
        )
    table = Table(title="Judge checklist")
    table.add_column("Bullet")
    table.add_column("Pass")
    for k, v in (result.checklist or {}).items():
        table.add_row(k, "[green]YES[/green]" if v else "[red]NO[/red]")
    console.print(table)
    console.print(f"session={result.session_id} investigation={result.investigation_id}")


@app.command("seed")
def seed_cmd(
    tenant: Optional[str] = typer.Option(None, "--tenant", "-t"),
    reset: bool = typer.Option(True, "--reset/--no-reset"),
) -> None:
    from salus.seed import load_seed

    name = load_seed(tenant, reset=reset)
    console.print(f"[green]Loaded[/green] {name}")


@app.command("verify")
def verify_cmd(tenant: Optional[str] = typer.Option(None, "--tenant", "-t")) -> None:
    """Smoke-test every Track 01/02/03 scoring bullet."""
    from salus.verify import run_verify

    ok = run_verify(tenant_id=tenant)
    raise typer.Exit(0 if ok else 1)


def main() -> None:
    import sys

    if len(sys.argv) > 1 and not sys.argv[1].startswith("-") and sys.argv[1] not in {
        "ask",
        "seed",
        "verify",
    }:
        q = " ".join(sys.argv[1:])
        sys.argv = [sys.argv[0], "ask", q]
    app()


if __name__ == "__main__":
    main()
