#!/usr/bin/env python3
import argparse
import os
import sys

import database
import parser as stmt_parser
import agent
import reports
from rich.console import Console

console = Console()


def cmd_import(args):
    filepath = os.path.abspath(args.file)
    filename = os.path.basename(filepath)

    # Warn on duplicate import
    existing = database.find_run_by_filename(filename)
    if existing and not args.force:
        console.print(
            f"[yellow]Warning:[/yellow] '{filename}' was already imported "
            f"(run_id={existing['id']}, at {existing['imported_at'][:19]}).\n"
            "Use --force to import again."
        )
        return

    console.print(f"\n[bold]Importing:[/bold] {filename}")

    try:
        transactions = stmt_parser.parse_file(filepath)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    run_id = database.create_run(filename)
    db_ids = database.insert_transactions(run_id, transactions)

    # Attach DB ids to transactions for the agent
    db_transactions = database.get_transactions(run_id)

    summaries = agent.run_analysis(run_id, db_transactions)

    output_path = f"report_run_{run_id}.html"
    console.print(f"\n[green]Done![/green] Run ID: {run_id}")
    reports.print_monthly_report(run_id, summaries, output_path=output_path)


def cmd_report(args):
    runs = database.list_runs()
    if not runs:
        console.print("[yellow]No runs found. Import a file first.[/yellow]")
        return

    run_id = args.run_id if args.run_id else runs[0]["id"]
    console.print(f"\nShowing report for run_id={run_id}")

    if args.transactions:
        reports.print_transaction_list(run_id, args.month, output_path=args.output)
    else:
        reports.print_monthly_report(run_id, output_path=args.output)


def cmd_list_runs(_args):
    reports.print_runs()


def main():
    database.init_db()

    parser = argparse.ArgumentParser(
        description="Bank Statement Analyzer — powered by Claude",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py import --file statement.csv
  python main.py report
  python main.py report --run-id 2 --month 2024-01
  python main.py report --run-id 1 --transactions
  python main.py list-runs
        """,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # import
    p_import = subparsers.add_parser("import", help="Import and analyze a bank statement")
    p_import.add_argument("--file", required=True, help="Path to CSV or PDF bank statement")
    p_import.add_argument("--force", action="store_true", help="Re-import even if file was already imported")
    p_import.set_defaults(func=cmd_import)

    # report
    p_report = subparsers.add_parser("report", help="Show analysis report")
    p_report.add_argument("--run-id", type=int, dest="run_id", help="Run ID (default: latest)")
    p_report.add_argument("--month", help="Filter to a specific month (YYYY-MM)")
    p_report.add_argument("--transactions", action="store_true", help="Show full transaction list")
    p_report.add_argument("--output", metavar="FILE.html", help="Save report as HTML file")
    p_report.set_defaults(func=cmd_report)

    # list-runs
    p_list = subparsers.add_parser("list-runs", help="List all imported runs")
    p_list.set_defaults(func=cmd_list_runs)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
