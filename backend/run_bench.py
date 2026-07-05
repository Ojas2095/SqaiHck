import asyncio
from web_app import kb, llm_engine
from benchmark_engine import BenchmarkEngine

def run_bench():
    print("Running benchmark on English questions...")
    bench = BenchmarkEngine(kb, llm_engine)
    res = bench.run(language="English", max_questions=5)
    print("Benchmark Result:", res)

if __name__ == "__main__":
    run_bench()

