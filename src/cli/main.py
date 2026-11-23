"""TradingAgents command-line interface.

The analysis, backtest, interactive-prompt and model-SDK imports are deferred to
their commands' bodies so a read-only command such as ``manifest query`` starts
without loading the graph, data vendors or model clients. The names the tests
patch (``run_analysis``, ``run_backtest``, ``summarize``) stay as module
attributes resolved at call time.
"""

import json
import sys
from enum import StrEnum
from typing import Annotated

import typer
from rich.markup import escape

from cli.console import console
from tradingagents.default_config import DEFAULT_CONFIG

# prompt_toolkit's win32 output module is importable only on Windows (it asserts
# the platform at import time), so gate on the platform rather than catching the
# failure — that way a genuinely broken prompt_toolkit on Windows still surfaces
# instead of silently disabling the handler below. Off Windows this stays an
# empty tuple, which `except` accepts and never matches (#1138).
if sys.platform == "win32":  # pragma: no cover - platform dependent
    from prompt_toolkit.output.win32 import NoConsoleScreenBufferError

    _NO_CONSOLE_ERRORS: tuple[type[BaseException], ...] = (NoConsoleScreenBufferError,)
else:
    _NO_CONSOLE_ERRORS = ()

# Providers the user signs in to instead of setting an API key. Kept as a light
# literal so the CLI starts without importing the model client that derives it;
# the login/logout commands still authenticate via the real chatgpt_auth path.
_SIGNED_IN_PROVIDERS = ("chatgpt",)

app = typer.Typer(
    name="TradingAgents",
    help="TradingAgents CLI: Multi-Agents LLM Financial Trading Framework",
    add_completion=True,  # Enable shell completion
)


def run_analysis(*args, **kwargs):
    """Analyze one ticker (FR: deferred import). Kept patchable as ``cli.main.run_analysis``."""
    from cli.run import run_analysis as _run_analysis

    return _run_analysis(*args, **kwargs)


def run_backtest(*args, **kwargs):
    """Run a backtest sweep (deferred import). Patchable as ``cli.main.run_backtest``."""
    from tradingagents.backtest import run_backtest as _run_backtest

    return _run_backtest(*args, **kwargs)


def summarize(*args, **kwargs):
    """Summarize a backtest result (deferred import). Patchable as ``cli.main.summarize``."""
    from tradingagents.backtest import summarize as _summarize

    return _summarize(*args, **kwargs)


class DecisionMode(StrEnum):
    """Supported FR-D qualification modes exposed by the analysis CLI."""

    STANDARD = "standard"
    TEAM = "team"


@app.callback(invoke_without_command=True)
def analyze(
    ctx: typer.Context,
    checkpoint: bool | None = typer.Option(
        None,
        "--checkpoint/--no-checkpoint",
        help="Enable/disable checkpoint-resume (save state after each node so a "
        "crashed run can resume). Omit to honor TRADINGAGENTS_CHECKPOINT_ENABLED.",
    ),
    clear_checkpoints: bool = typer.Option(
        False,
        "--clear-checkpoints",
        help="Delete all saved checkpoints before running (force fresh start).",
    ),
    portfolio: str = typer.Option(
        None,
        "--portfolio",
        help="JSON file with current holdings and cash, so the trader, risk and "
        "portfolio agents size against your actual position.",
    ),
    ticker: str = typer.Option(None, "--ticker", help="Ticker to analyze, e.g. NVDA or 0700.HK; skips the prompt"),
    date: str = typer.Option(None, "--date", help="Analysis date, YYYY-MM-DD; skips the prompt"),
    analysts: str = typer.Option(
        None, "--analysts", help="Comma-separated analysts, e.g. market,news; skips the prompt"
    ),
    decision_mode: Annotated[
        DecisionMode,
        typer.Option(
            "--decision-mode",
            help="Decision qualification mode: standard preserves upstream behavior; team applies the deterministic gate.",
        ),
    ] = DecisionMode.STANDARD,
    save: bool | None = typer.Option(
        None, "--save/--no-save", help="Save the report under results_dir without asking"
    ),
    show: bool | None = typer.Option(
        None, "--show/--no-show", help="Show the full report at the end without asking"
    ),
    html: bool | None = typer.Option(
        None, "--html/--no-html",
        help="Save the report as one HTML page too, complete_report.html, without asking (default: yes)",
    ),
):
    """Run an analysis. This is what a bare `tradingagents` does.

    Flags answer their questions; with provider, models, depth and language also
    set through TRADINGAGENTS_* variables, the run asks nothing.
    """
    if ctx.invoked_subcommand is not None:
        return
    if clear_checkpoints:
        from tradingagents.graph.checkpointer import clear_all_checkpoints
        n = clear_all_checkpoints(DEFAULT_CONFIG["data_cache_dir"])
        console.print(f"[yellow]Cleared {n} checkpoint(s).[/yellow]")
    portfolio_context = None
    if portfolio:
        from tradingagents.portfolio import load_portfolio

        try:
            portfolio_context = load_portfolio(portfolio)
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1) from None

    try:
        flags = {
            "ticker": ticker,
            "date": date,
            "analysts": analysts,
            "decision_mode": decision_mode.value,
            "save": save,
            "show": show,
            "html": html,
        }
        run_analysis(checkpoint=checkpoint, portfolio=portfolio_context, flags=flags)
    except _NO_CONSOLE_ERRORS:
        # A terminal with no console buffer cannot host the interactive prompts.
        # Emit one actionable line on stderr instead of a prompt_toolkit
        # traceback; plain text, since rich may not render here either (#1138).
        typer.echo(
            "Error: no Windows console available. The interactive CLI needs a real "
            "console buffer — run it from Windows Terminal, PowerShell, or cmd.exe "
            "rather than a piped or embedded terminal.",
            err=True,
        )
        raise typer.Exit(code=1) from None


@app.command()
def backtest(
    tickers: str = typer.Argument(..., help="Comma-separated tickers, e.g. NVDA,AAPL"),
    start: str = typer.Option(..., "--start", help="First analysis date, YYYY-MM-DD"),
    end: str = typer.Option(..., "--end", help="Last analysis date, YYYY-MM-DD"),
    every: int = typer.Option(7, "--every", help="Days between analysis dates"),
    analysts: str = typer.Option(
        None, "--analysts", help="Comma-separated analysts to run: market, sentiment, news, fundamentals; omit for all the asset type allows"
    ),
    asset_type: str = typer.Option("stock", "--asset-type", help="stock or crypto"),
    portfolio: str = typer.Option(
        None, "--portfolio", help="JSON file with holdings and cash, held constant across the grid"
    ),
    run_id: str = typer.Option(
        None, "--run-id", help="Continue an earlier sweep: its cells are skipped and its log reused"
    ),
):
    """Score past decisions over a grid of tickers and dates."""

    from cli.models import AnalystType, AssetType
    from cli.prompts import filter_analysts_for_asset_type, parse_analysts
    from tradingagents.backtest import iter_grid
    from tradingagents.portfolio import load_portfolio

    try:
        dates = iter_grid(start, end, every)
        book = load_portfolio(portfolio) if portfolio else None
        kind = AssetType(asset_type.strip().lower())
        # The analysts are named and checked as for an analysis; without a
        # choice, every analyst the asset type allows runs.
        chosen = (parse_analysts(analysts, kind) if analysts
                  else filter_analysts_for_asset_type(list(AnalystType), kind))
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from None

    names = [t.strip() for t in tickers.split(",") if t.strip()]
    if not names:
        console.print("[red]No ticker to analyze; pass them comma-separated, e.g. NVDA,AAPL[/red]")
        raise typer.Exit(code=1)

    def show_progress(done, total, ticker, date):
        console.print(f"[dim][{done}/{total}] {ticker} {date}[/dim]")

    kwargs = {"asset_type": kind.value, "portfolio": book, "run_id": run_id, "progress": show_progress,
              "selected_analysts": [a.value for a in chosen]}

    try:
        result = run_backtest(names, dates, DEFAULT_CONFIG, **kwargs)
    except Exception as exc:  # a missing key or an unknown analyst is a setup error
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from None
    console.print(summarize(result).render())
    console.print(f"\nRan {result.cells_run} cells, skipped {result.skipped}. Log: {result.log_path}")
    console.print(f"Continue or settle this sweep: --run-id {result.run_id}")
    for ticker, date, reason in result.failures:
        console.print(f"[yellow]failed:[/yellow] {ticker} {date}: {reason}")
    for ticker, reason in result.settlement_failures:
        console.print(f"[yellow]unsettled:[/yellow] {ticker}: {reason}")


# The plans `login` and `logout` take: the providers signed in to, not keyed.
Plan = StrEnum("Plan", {name: name for name in _SIGNED_IN_PROVIDERS})


@app.command()
def login(plan: Annotated[Plan, typer.Argument(help="The plan to sign in with")]):
    """Sign in with your ChatGPT Plus or Pro plan, for the chatgpt provider."""
    from tradingagents.llm_clients import chatgpt_auth

    try:
        # One unwrapped line, so the sign-in address can be copied whole.
        email = chatgpt_auth.sign_in(
            say=lambda line: console.print(line, soft_wrap=True, markup=False, highlight=False))
    except chatgpt_auth.ChatGPTAuthError as exc:
        console.print(f"[red]{escape(str(exc))}[/red]")
        raise typer.Exit(code=1) from None
    console.print(f"[green]Signed in to ChatGPT as {escape(email)}.[/green]")


@app.command()
def logout(plan: Annotated[Plan, typer.Argument(help="The plan to sign out of")]):
    """Sign out of your ChatGPT plan: revoke this machine's access and forget it."""
    from tradingagents.llm_clients import chatgpt_auth

    outcome = chatgpt_auth.sign_out()
    if outcome == "revoked":
        console.print("Signed out of ChatGPT.")
    elif outcome == "forgotten":
        console.print("[yellow]Signed out here, but OpenAI could not be reached to revoke the sign-in; "
                      "it stays valid at OpenAI until it expires.[/yellow]")
    else:
        console.print("Not signed in to ChatGPT.")


@app.command()
def manifest(
    action: Annotated[str, typer.Argument(help="Subcommand: query")],
    results_dir: str = typer.Option(
        None, "--results-dir",
        help="Results root to scan; defaults to the configured results directory"),
    ticker: str = typer.Option(None, "--ticker", help="Only runs for this ticker"),
    date: str = typer.Option(None, "--date", help="Only runs on this YYYY-MM-DD analysis date"),
    json_output: bool = typer.Option(
        False, "--json", help="Print a JSON object {matches, warnings} to stdout"),
):
    """Read the run manifests under a results root (FR-C). Never starts an analysis."""
    if action != "query":
        console.print(
            f"[red]Unknown manifest subcommand: {action!r}. Try: manifest query[/red]")
        raise typer.Exit(code=2)

    # Imported here so the query path never pulls in the analysis graph, backtest
    # or data vendors.
    from tradingagents.enhancements.manifest import query_manifests

    root = results_dir or DEFAULT_CONFIG["results_dir"]
    outcome = query_manifests(root, ticker=ticker or None, date=date or None)

    if json_output:
        matches = [
            {
                "run_id": m.run_id,
                "ticker": m.ticker,
                "trade_date": m.trade_date,
                "status": m.status,
                "reports": m.reports,
                "manifest_path": str(m.manifest_path),
            }
            for m in outcome.matches
        ]
        typer.echo(json.dumps({"matches": matches, "warnings": list(outcome.warnings)}))
        return

    if not outcome.matches:
        console.print("[dim]No matching runs.[/dim]")
    for m in outcome.matches:
        console.print(f"{m.ticker} {m.trade_date} [{m.status}] {m.run_id}")
        for key, value in m.reports.items():
            if value is not None:
                console.print(f"  {key}: {value}")
    for warning in outcome.warnings:
        console.print(f"[yellow]warning:[/yellow] {warning}")


if __name__ == "__main__":
    app()
