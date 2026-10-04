import asyncio
import sys
from pathlib import Path

# Enable UTF-8 encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.trustdesk.eval.runner import EvalRunner
from src.trustdesk.eval.metrics import generate_markdown_report

async def main():
    print("=" * 70)
    print("[*] Running TrustDesk Capstone Benchmark Suite (eval_cases.jsonl)...")
    print("=" * 70)

    runner = EvalRunner()
    summary = await runner.run_benchmark()

    report = generate_markdown_report(summary)
    print("\n" + report)

    # Save to eval_report.md
    with open("eval_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    print("\n[+] Evaluation report saved to 'eval_report.md'")

    if summary.all_passed:
        print("\n[SUCCESS] ALL CAPSTONE BENCHMARKS PASSED THE RUBRIC CRITERIA!")
        sys.exit(0)
    else:
        print("\n[WARNING] SOME BENCHMARK CRITERIA DID NOT MEET THRESHOLDS.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
