#!/bin/bash

# Performance Comparison Script: Pandas vs Polars
# This script runs benchmarks with both backends and compares results

echo "================================================================================"
echo "🔬 PERFORMANCE COMPARISON: PANDAS vs POLARS"
echo "================================================================================"
echo ""

# Create results directory
mkdir -p benchmarks/results

# Step 1: Test with Pandas (baseline)
echo "📊 PHASE 1: TESTING PANDAS + PICKLE (Baseline)"
echo "--------------------------------------------------------------------------------"

# Disable Polars
sed -i '' 's/USE_POLARS=true/USE_POLARS=false/' .env

echo "✅ Polars disabled (USE_POLARS=false)"
echo "🏃 Running Pandas benchmark (10 runs)..."
echo ""

source venv/bin/activate
python src/benchmarks/benchmark_runner.py --full --runs 10

echo ""
echo "✅ Pandas benchmark complete"
echo ""

# Step 2: Test with Polars
echo "================================================================================"
echo "📊 PHASE 2: TESTING POLARS + PICKLE (Optimized)"
echo "--------------------------------------------------------------------------------"

# Enable Polars
sed -i '' 's/USE_POLARS=false/USE_POLARS=true/' .env

echo "✅ Polars enabled (USE_POLARS=true)"
echo "🏃 Running Polars benchmark (10 runs)..."
echo ""

python src/benchmarks/benchmark_runner.py --full --runs 10

echo ""
echo "✅ Polars benchmark complete"
echo ""

# Step 3: Show results
echo "================================================================================"
echo "📈 RESULTS SAVED"
echo "================================================================================"
echo ""
echo "Benchmark results are saved in: benchmarks/results/"
echo ""
ls -lht benchmarks/results/*.csv | head -2
echo ""
echo "📊 To analyze results:"
echo "   1. Open CSV files in Excel/Google Sheets"
echo "   2. Compare 'mean_time_seconds' columns"
echo "   3. Calculate speedup: pandas_time / polars_time"
echo ""
echo "✅ Comparison complete!"
