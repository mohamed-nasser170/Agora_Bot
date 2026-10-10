"""
main.py
════════════════════════════════════════════════════════════════
Agora — terminal chat (handy for quick tests).

Run:      python main.py
Web app:  uvicorn server:app --reload     →  http://localhost:8000
════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bootstrap import ConfigError, build_flow  # noqa: E402
from utils.helpers import format_duration, sanitise_input  # noqa: E402

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel

    console = Console()
    RICH = True
except ImportError:  # rich is optional
    console, RICH = None, False

BANNER = r"""
     █████╗  ██████╗  ██████╗ ██████╗  █████╗
    ██╔══██╗██╔════╝ ██╔═══██╗██╔══██╗██╔══██╗
    ███████║██║  ███╗██║   ██║██████╔╝███████║
    ██╔══██║██║   ██║██║   ██║██╔══██╗██╔══██║
    ██║  ██║╚██████╔╝╚██████╔╝██║  ██║██║  ██║
    ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝
              Αγορά · where ideas gather
"""

HELP = "/clear  reset memory    /memory  show memory    /quit  exit"


def out(text: str = "", style: str | None = None) -> None:
    console.print(text, style=style) if RICH else print(text)


def main() -> None:
    try:
        flow = build_flow()
    except ConfigError as exc:
        print(f"\n[ERROR] {exc}\n  → copy .env.example to .env and set GROQ_API_KEY\n")
        sys.exit(1)

    out(BANNER, "bold dark_orange")
    out(f"model: {flow.chain.model_name}   ·   {HELP}\n", "dim")

    while True:
        try:
            text = sanitise_input(console.input("[bold]you ›[/bold] ") if RICH else input("you › "))
        except (EOFError, KeyboardInterrupt):
            out("\nbye 👋")
            return
        if not text:
            continue

        cmd = text.lower()
        if cmd in ("/quit", "/exit", "/q"):
            out("bye 👋")
            return
        if cmd == "/clear":
            flow.memory.clear()
            out("memory cleared", "green")
            continue
        if cmd == "/memory":
            s = flow.memory.stats()
            body = f"name: {s['user_name'] or '—'}\nturns: {s['turns']}\nfacts: {s['facts']}"
            out(Panel(body, title="memory", border_style="dark_orange") if RICH else body)
            continue

        t0 = time.time()
        if RICH:
            with console.status("[dim]thinking…[/dim]"):
                reply = flow.run(text)
            out(f"\n[bold dark_orange]agora[/bold dark_orange] [dim]· {format_duration(time.time() - t0)}[/dim]")
            console.print(Markdown(reply))
            out()
        else:
            reply = flow.run(text)
            print(f"\nagora · {format_duration(time.time() - t0)}\n{reply}\n")


if __name__ == "__main__":
    main()
