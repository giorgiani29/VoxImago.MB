# Sistemma de profile integrado para o Vox Imago
# Permite medir o desempenho de diferentes partes do código

import tracemalloc
import psutil
import time
import cProfile
import pstats
import io
from datetime import datetime
from functools import wraps
from typing import Dict, List, Optional
import os


class MemoryProfiler:
    def __init__(self):
        self.is_tracing = False
        self.snapshots = []
        self.baseline = None

    def start_tracing(self):
        if not self.is_tracing:
            tracemalloc.start()
            self.is_tracing = True
            self.baseline = self.take_snapshot()
            print("🔍 Memory tracking iniciado")

    def stop_tracing(self):
        if self.is_tracing:
            tracemalloc.stop()
            self.is_tracing = False
            print("⏹️ Memory tracking parado")

    def take_snapshot(self):
        if not self.is_tracing:
            return None

        snapshot = tracemalloc.take_snapshot()

        process = psutil.Process()
        memory_info = process.memory_info()

        snapshot_data = {
            'timestamp': time.time(),
            'tracemalloc_snapshot': snapshot,
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'cpu_percent': process.cpu_percent()
        }

        self.snapshots.append(snapshot_data)
        return snapshot_data

    def get_memory_stats(self) -> Dict:
        if not self.snapshots:
            return {}

        latest = self.snapshots[-1]
        stats = {
            'current_rss_mb': latest['rss_mb'],
            'current_vms_mb': latest['vms_mb'],
            'current_cpu_percent': latest['cpu_percent'],
            'snapshots_count': len(self.snapshots),
        }

        if self.baseline and len(self.snapshots) > 1:
            stats['memory_growth_mb'] = latest['rss_mb'] - \
                self.baseline['rss_mb']

        return stats

    def analyze_top_consumers(self, limit: int = 10) -> List[Dict]:
        if not self.is_tracing or not self.snapshots:
            return []

        latest_snapshot = self.snapshots[-1]['tracemalloc_snapshot']
        top_stats = latest_snapshot.statistics('lineno')

        consumers = []
        for stat in top_stats[:limit]:
            consumers.append({
                'filename': stat.traceback.format()[-1],
                'size_mb': stat.size / 1024 / 1024,
                'count': stat.count,
            })

        return consumers


def memory_profile(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        process = psutil.Process()
        mem_before = process.memory_info().rss / 1024 / 1024

        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()

        mem_after = process.memory_info().rss / 1024 / 1024

        print(
            f"📊 {func.__name__}: {mem_after - mem_before:.2f}MB, {end_time - start_time:.3f}s")
        return result
    return wrapper


class CPUProfiler:
    def __init__(self):
        self.profiler = None
        self.is_profiling = False
        self.profile_data = None

    def start_profiling(self):
        if not self.is_profiling:
            self.profiler = cProfile.Profile()
            self.profiler.enable()
            self.is_profiling = True
            print("🚀 CPU profiling iniciado...")
            return True
        else:
            if self.profiler:
                self.profiler.disable()
                self.is_profiling = False

                string_io = io.StringIO()
                ps = pstats.Stats(self.profiler, stream=string_io)
                ps.sort_stats('cumulative')
                ps.print_stats(20)

                self.profile_data = string_io.getvalue()
                print("⏹️ CPU profiling finalizado")
                return self.profile_data
        return None

    def get_top_functions(self, limit=10):
        if not self.profiler:
            return []

        string_io = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=string_io)
        ps.sort_stats('cumulative')
        ps.print_stats(limit)

        return string_io.getvalue()

    def profile_function(self, func, *args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()

        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()

        profiler.disable()

        string_io = io.StringIO()
        ps = pstats.Stats(profiler, stream=string_io)
        ps.sort_stats('cumulative')
        ps.print_stats(10)

        print(f"🔥 Function: {func.__name__}")
        print(f"⏱️ Time: {end_time - start_time:.3f}s")
        print("📊 Top calls:")
        print(string_io.getvalue()[:500] + "...")

        return result


cpu_profiler = CPUProfiler()
memory_profiler = MemoryProfiler()
