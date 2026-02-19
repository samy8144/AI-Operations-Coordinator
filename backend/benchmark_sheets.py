import os
import time
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from sheets_sync import sheets

def benchmark():
    print("🚀 Starting Benchmark...")
    
    # First read (will populate cache)
    start = time.time()
    print("Reading pilots (1st time - cache miss)...")
    sheets.read_pilots()
    end = time.time()
    first_duration = end - start
    print(f"Time: {first_duration:.2f}s")
    
    # Second read (should be cache hit for worksheet, but still network call for get_all_records)
    # Wait, get_all_records() is still a network call.
    # But _get_worksheet() being cached saves open_by_key() call.
    
    iters = 3
    print(f"\nPerforming {iters} more reads (should benefit from cached worksheet object)...")
    
    durations = []
    for i in range(iters):
        start = time.time()
        sheets.read_pilots()
        end = time.time()
        d = end - start
        durations.append(d)
        print(f"Iteration {i+1}: {d:.2f}s")
    
    avg_cached = sum(durations) / iters
    print(f"\nAverage time with cached worksheet: {avg_cached:.2f}s")
    print(f"Speedup vs first call: {first_duration / avg_cached:.1f}x")

if __name__ == "__main__":
    benchmark()
