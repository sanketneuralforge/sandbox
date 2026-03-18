from typing import Dict, Optional
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.text import Text

import database

console = Console()


def _make_console(record: bool) -> Console:
    return Console(record=record) if record else console


def print_monthly_report(run_id: int, summaries: Dict[str, str] = None, output_path: Optional[str] = None):
    c = _make_console(record=output_path is not None)
    aggregates = database.get_monthly_aggregates(run_id)
    income = database.get_income(run_id)
    anomalies = database.get_anomalies(run_id)

    if not aggregates:
        c.print("[yellow]No expense data found for this run.[/yellow]")
        return

    c.print()
    c.rule("[bold cyan]Bank Statement Analysis Report[/bold cyan]")

    for month in sorted(aggregates.keys()):
        cats = aggregates[month]
        total_spent = sum(cats.values())
        month_income = income.get(month, 0)

        # Summary narrative
        if summaries and month in summaries:
            c.print()
            c.print(Panel(
                summaries[month],
                title=f"[bold]{month}[/bold]",
                border_style="cyan",
            ))

        # Spending table
        table = Table(box=box.SIMPLE_HEAVY, show_footer=True)
        table.add_column("Category", style="bold")
        table.add_column("Amount", justify="right", footer=f"[bold red]${total_spent:.2f}[/bold red]")
        table.add_column("Share", justify="right", footer="")

        for cat, amount in sorted(cats.items(), key=lambda x: -x[1]):
            pct = (amount / total_spent * 100) if total_spent else 0
            table.add_row(cat, f"${amount:.2f}", f"{pct:.1f}%")

        if month_income:
            table.add_row(
                "[green]income[/green]",
                f"[green]+${month_income:.2f}[/green]",
                "",
            )

        c.print(table)

    # Anomalies section
    if anomalies:
        c.print()
        c.rule("[bold yellow]Flagged Transactions[/bold yellow]")
        a_table = Table(box=box.SIMPLE, show_header=True)
        a_table.add_column("Date")
        a_table.add_column("Merchant")
        a_table.add_column("Amount", justify="right")
        a_table.add_column("Reason", style="yellow")

        for tx in anomalies:
            amount_str = f"${abs(tx['amount']):.2f}"
            if tx["amount"] > 0:
                amount_str = f"+{amount_str}"
            a_table.add_row(tx["date"], tx["merchant"], amount_str, tx["anomaly_reason"] or "")

        c.print(a_table)
    else:
        c.print("\n[green]No anomalies detected.[/green]")

    c.print()

    if output_path:
        c.save_html(output_path)
        console.print(f"[green]Report saved to:[/green] {output_path}")


def print_transaction_list(run_id: int, month: str = None, output_path: Optional[str] = None):
    c = _make_console(record=output_path is not None)
    transactions = database.get_transactions(run_id)
    if month:
        transactions = [t for t in transactions if t["date"].startswith(month)]

    if not transactions:
        c.print("[yellow]No transactions found.[/yellow]")
        return

    table = Table(box=box.SIMPLE, title=f"Transactions — Run {run_id}")
    table.add_column("Date")
    table.add_column("Merchant")
    table.add_column("Amount", justify="right")
    table.add_column("Category")
    table.add_column("Flag")

    for tx in transactions:
        amount = tx["amount"]
        amount_str = f"[green]+${amount:.2f}[/green]" if amount > 0 else f"[red]-${abs(amount):.2f}[/red]"
        flag = "[yellow]⚠[/yellow]" if tx["is_anomaly"] else ""
        table.add_row(
            tx["date"], tx["merchant"], amount_str,
            tx["category"] or "-", flag
        )

    c.print(table)

    if output_path:
        c.save_html(output_path)
        console.print(f"[green]Report saved to:[/green] {output_path}")


def print_runs():
    runs = database.list_runs()
    if not runs:
        console.print("[yellow]No analysis runs found.[/yellow]")
        return

    table = Table(box=box.SIMPLE, title="Analysis Runs")
    table.add_column("ID", justify="right")
    table.add_column("Filename")
    table.add_column("Imported At")
    table.add_column("Transactions", justify="right")

    for run in runs:
        table.add_row(
            str(run["id"]),
            run["filename"],
            run["imported_at"][:19],
            str(run["tx_count"]),
        )

    console.print(table)
