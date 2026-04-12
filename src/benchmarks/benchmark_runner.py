"""
Benchmark Runner for Pandas vs Polars Performance Comparison

Compares query performance between:
1. Pandas + Pickle cache
2. Polars (if enabled)

Metrics collected:
- Startup time (loading data)
- Query execution time
- Memory usage
- Statistical analysis (mean, median, std dev, percentiles)

Usage:
    python src/benchmarks/benchmark_runner.py --runs 10
    python src/benchmarks/benchmark_runner.py --full  # Run full suite
"""

import time
import os
import sys
from pathlib import Path
import pandas as pd
import json
from datetime import datetime
from typing import Dict, List
import tracemalloc

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.analytics.query_engine import StormQueryEngine
from src.analytics.query_parser_gemini import GroqQueryParser
from src.analytics.config import GROQ_API_KEY


class BenchmarkRunner:
    """Run performance benchmarks comparing pandas and Polars"""

    def __init__(self, num_runs: int = 5):
        """
        Initialize benchmark runner.

        Args:
            num_runs: Number of times to run each benchmark for statistical significance
        """
        self.num_runs = num_runs
        self.results = []

    def benchmark_startup(self, use_polars: bool = False) -> Dict:
        """
        Benchmark data loading time.

        Args:
            use_polars: Whether to use Polars backend

        Returns:
            Dictionary with timing results
        """
        backend = "Polars" if use_polars else "Pandas"
        print(f"\n📊 Benchmarking {backend} startup...")

        times = []
        memory_usage = []

        for run in range(self.num_runs):
            print(f"  Run {run + 1}/{self.num_runs}...", end=" ")

            # Start memory tracking
            tracemalloc.start()

            start_time = time.time()
            engine = StormQueryEngine(data_path=None, use_cache=True, use_polars=use_polars)
            end_time = time.time()

            # Get memory usage
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            elapsed = end_time - start_time
            times.append(elapsed)
            memory_usage.append(peak / (1024 * 1024))  # Convert to MB

            print(f"{elapsed:.3f}s (peak memory: {peak / (1024 * 1024):.1f} MB)")

            # Clean up
            del engine

        return {
            "backend": backend,
            "operation": "startup",
            "times": times,
            "mean_time": sum(times) / len(times),
            "min_time": min(times),
            "max_time": max(times),
            "memory_mb": sum(memory_usage) / len(memory_usage),
            "num_runs": self.num_runs
        }

    def benchmark_query(self, query: str, query_name: str, use_polars: bool = False) -> Dict:
        """
        Benchmark query execution time.

        Args:
            query: Natural language query
            query_name: Name for this query
            use_polars: Whether to use Polars backend

        Returns:
            Dictionary with timing results
        """
        backend = "Polars" if use_polars else "Pandas"
        print(f"\n📊 Benchmarking {backend} query: {query_name}")
        print(f"  Query: \"{query}\"")

        # Initialize engine once
        engine = StormQueryEngine(data_path=None, use_cache=True, use_polars=use_polars)
        parser = GroqQueryParser(api_key=GROQ_API_KEY)

        # Parse query once
        parsed = parser.parse(query)

        times = []
        result_counts = []

        for run in range(self.num_runs):
            print(f"  Run {run + 1}/{self.num_runs}...", end=" ")

            start_time = time.time()
            result = engine.execute_query(parsed)
            end_time = time.time()

            elapsed = end_time - start_time
            times.append(elapsed)
            result_counts.append(result.get('summary', {}).get('total_events', 0))

            print(f"{elapsed:.3f}s ({result_counts[-1]:,} events)")

        return {
            "backend": backend,
            "operation": "query",
            "query_name": query_name,
            "query": query,
            "times": times,
            "mean_time": sum(times) / len(times),
            "min_time": min(times),
            "max_time": max(times),
            "result_count": result_counts[0],
            "num_runs": self.num_runs
        }

    def run_full_benchmark(self) -> List[Dict]:
        """
        Run full benchmark suite comparing pandas and Polars.

        Returns:
            List of benchmark results
        """
        print("=" * 60)
        print("🚀 STARTING FULL BENCHMARK SUITE")
        print("=" * 60)

        results = []

        # Test queries representing different complexity levels
        test_queries = [
            {
                "name": "Simple Filter",
                "query": "Show me all tornado events in Texas in 2020"
            },
            {
                "name": "Complex Filter",
                "query": "Show me all places where hurricane deaths occurred in 2020"
            },
            {
                "name": "Location Aggregation",
                "query": "Show me all locations where tornadoes occurred in the last 5 years"
            }
        ]

        # Benchmark 1: Startup time (Pandas)
        print("\n" + "=" * 60)
        print("PHASE 1: STARTUP TIME COMPARISON")
        print("=" * 60)

        startup_pandas = self.benchmark_startup(use_polars=False)
        results.append(startup_pandas)

        # Benchmark 2: Startup time (Polars) - if enabled
        if os.getenv('USE_POLARS', '').lower() in ('true', '1', 'yes'):
            startup_polars = self.benchmark_startup(use_polars=True)
            results.append(startup_polars)
        else:
            print("\n⚠️  Skipping Polars startup benchmark (USE_POLARS not enabled)")

        # Benchmark 3: Query execution (Pandas)
        print("\n" + "=" * 60)
        print("PHASE 2: QUERY EXECUTION COMPARISON")
        print("=" * 60)

        for test_query in test_queries:
            query_pandas = self.benchmark_query(
                query=test_query["query"],
                query_name=test_query["name"],
                use_polars=False
            )
            results.append(query_pandas)

        # Benchmark 4: Query execution (Polars) - if enabled
        if os.getenv('USE_POLARS', '').lower() in ('true', '1', 'yes'):
            for test_query in test_queries:
                query_polars = self.benchmark_query(
                    query=test_query["query"],
                    query_name=test_query["name"],
                    use_polars=True
                )
                results.append(query_polars)
        else:
            print("\n⚠️  Skipping Polars query benchmarks (USE_POLARS not enabled)")

        return results

    def save_results(self, results: List[Dict], output_dir: str = "benchmarks/results"):
        """
        Save benchmark results to JSON and CSV files.

        Args:
            results: List of benchmark results
            output_dir: Directory to save results
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON (detailed)
        json_file = output_path / f"benchmark_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Saved detailed results: {json_file}")

        # Save CSV (summary)
        csv_file = output_path / f"benchmark_{timestamp}.csv"
        df = pd.DataFrame([
            {
                "backend": r["backend"],
                "operation": r["operation"],
                "query_name": r.get("query_name", "N/A"),
                "mean_time_seconds": r["mean_time"],
                "min_time_seconds": r["min_time"],
                "max_time_seconds": r["max_time"],
                "result_count": r.get("result_count", "N/A"),
                "memory_mb": r.get("memory_mb", "N/A"),
                "num_runs": r["num_runs"]
            }
            for r in results
        ])
        df.to_csv(csv_file, index=False)
        print(f"✅ Saved CSV summary: {csv_file}")

    def print_comparison(self, results: List[Dict]):
        """
        Print comparison summary.

        Args:
            results: List of benchmark results
        """
        print("\n" + "=" * 60)
        print("📊 BENCHMARK SUMMARY")
        print("=" * 60)

        # Startup comparison
        startup_results = [r for r in results if r["operation"] == "startup"]
        if len(startup_results) >= 2:
            pandas_startup = next((r for r in startup_results if r["backend"] == "Pandas"), None)
            polars_startup = next((r for r in startup_results if r["backend"] == "Polars"), None)

            if pandas_startup and polars_startup:
                speedup = pandas_startup["mean_time"] / polars_startup["mean_time"]
                print(f"\n🚀 STARTUP TIME:")
                print(f"  Pandas:  {pandas_startup['mean_time']:.3f}s")
                print(f"  Polars:  {polars_startup['mean_time']:.3f}s")
                print(f"  Speedup: {speedup:.2f}x")

        # Query comparison
        query_results = [r for r in results if r["operation"] == "query"]
        query_names = list(set(r["query_name"] for r in query_results))

        for query_name in query_names:
            pandas_query = next((r for r in query_results if r["query_name"] == query_name and r["backend"] == "Pandas"), None)
            polars_query = next((r for r in query_results if r["query_name"] == query_name and r["backend"] == "Polars"), None)

            if pandas_query and polars_query:
                speedup = pandas_query["mean_time"] / polars_query["mean_time"]
                print(f"\n⚡ {query_name.upper()}:")
                print(f"  Pandas:  {pandas_query['mean_time']:.3f}s")
                print(f"  Polars:  {polars_query['mean_time']:.3f}s")
                print(f"  Speedup: {speedup:.2f}x")


def main():
    """Main entry point for benchmark runner."""
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark pandas vs Polars performance")
    parser.add_argument("--runs", type=int, default=5, help="Number of runs per benchmark")
    parser.add_argument("--full", action="store_true", help="Run full benchmark suite")

    args = parser.parse_args()

    runner = BenchmarkRunner(num_runs=args.runs)

    if args.full:
        results = runner.run_full_benchmark()
        runner.save_results(results)
        runner.print_comparison(results)
    else:
        # Quick startup benchmark only
        print("\n⚡ Quick benchmark (startup only). Use --full for complete suite.\n")
        startup_pandas = runner.benchmark_startup(use_polars=False)
        results = [startup_pandas]

        if os.getenv('USE_POLARS', '').lower() in ('true', '1', 'yes'):
            startup_polars = runner.benchmark_startup(use_polars=True)
            results.append(startup_polars)

        runner.print_comparison(results)
        print("\n💡 Run with --full flag for complete benchmark suite")


if __name__ == "__main__":
    main()
