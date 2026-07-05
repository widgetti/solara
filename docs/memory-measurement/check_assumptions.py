"""Verify the claims made in docs/memory-usage-inspection.md by measuring.

Each check prints PASS/FAIL/INFO with numbers.
"""

import gc
import resource
import sys

import psutil

MB = 1e6


def rss():
    return psutil.Process().memory_info().rss


def check_maxrss_units():
    """Claim: ru_maxrss is bytes on macOS, KiB on Linux."""
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    current = rss()
    # if units were KiB on macOS, r*1024 would be ~1000x larger than RSS
    ratio = r / current
    print(f"[maxrss-units] ru_maxrss={r} rss={current} ratio={ratio:.2f}")
    if sys.platform == "darwin":
        ok = 0.5 < ratio < 20  # same order of magnitude => bytes
        print(f"[maxrss-units] macOS ru_maxrss is in BYTES: {'PASS' if ok else 'FAIL'}")


def check_pymalloc_retention():
    """Claim: freeing millions of small objects does not fully return RSS to the OS,
    and one surviving object per arena-region keeps memory pinned (fragmentation)."""
    gc.collect()
    before = rss()

    # 4 million small tuples ~ hundreds of MB
    data = [(i, i + 1) for i in range(4_000_000)]
    peak = rss()

    # free 100% of them
    del data
    gc.collect()
    after_full_free = rss()

    # now fragmentation: keep every 1000th object alive
    data = [(i, i + 1) for i in range(4_000_000)]
    survivors = data[::1000]
    del data
    gc.collect()
    after_fragmented = rss()
    del survivors
    gc.collect()

    grown = peak - before
    retained_full = after_full_free - before
    retained_frag = after_fragmented - before
    print(f"[pymalloc] baseline={before / MB:.0f}MB peak={peak / MB:.0f}MB (+{grown / MB:.0f}MB)")
    print(f"[pymalloc] after freeing ALL:        rss delta = {retained_full / MB:+.0f} MB")
    print(f"[pymalloc] after freeing 99.9%:      rss delta = {retained_frag / MB:+.0f} MB (fragmentation)")
    print(f"[pymalloc] fragmentation retains more than full free: {'PASS' if retained_frag > retained_full + grown * 0.2 else 'FAIL'}")


def check_debugmallocstats():
    """Claim: sys._debugmallocstats() shows arena usage."""
    import io
    import contextlib

    f = io.StringIO()
    try:
        with contextlib.redirect_stderr(f):
            sys._debugmallocstats()
    except Exception as e:
        print(f"[debugmallocstats] FAIL: {e}")
        return
    out = f.getvalue()
    has_arenas = "arenas" in out
    print(f"[debugmallocstats] output has arena stats: {'PASS' if has_arenas else 'FAIL'} ({len(out)} chars)")
    for line in out.splitlines():
        if "arenas allocated current" in line or "Total" in line and "arena" in line:
            print(f"[debugmallocstats]   {line.strip()}")


def check_tracemalloc_numpy():
    """Claim in doc: tracemalloc does NOT see native buffers (e.g. numpy).
    Modern numpy explicitly reports its buffers to tracemalloc, so this may be WRONG."""
    import tracemalloc

    try:
        import numpy as np
    except ImportError:
        print("[tracemalloc-numpy] numpy not installed, skip")
        return
    tracemalloc.start()
    snap1 = tracemalloc.take_snapshot()
    arr = np.zeros(50 * 1024 * 1024, dtype=np.uint8)  # 50 MB native buffer
    arr[:] = 1  # touch pages
    snap2 = tracemalloc.take_snapshot()
    tracemalloc.stop()
    diff = snap2.compare_to(snap1, "lineno")
    total = sum(s.size_diff for s in diff)
    sees_it = total > 40 * MB
    print(f"[tracemalloc-numpy] tracemalloc saw {total / MB:.0f} MB of the 50 MB numpy buffer")
    print(f"[tracemalloc-numpy] numpy IS visible to tracemalloc: {'YES' if sees_it else 'NO'}")
    del arr


def check_raw_malloc_invisible():
    """Claim: raw malloc via a C extension that does NOT integrate with tracemalloc is invisible.
    Use ctypes to malloc directly."""
    import ctypes
    import ctypes.util
    import tracemalloc

    libc = ctypes.CDLL(ctypes.util.find_library("c"))
    libc.malloc.restype = ctypes.c_void_p
    libc.free.argtypes = [ctypes.c_void_p]
    tracemalloc.start()
    snap1 = tracemalloc.take_snapshot()
    ptr = libc.malloc(50 * 1024 * 1024)
    ctypes.memset(ptr, 1, 50 * 1024 * 1024)
    snap2 = tracemalloc.take_snapshot()
    tracemalloc.stop()
    total = sum(s.size_diff for s in snap2.compare_to(snap1, "lineno"))
    print(f"[raw-malloc] tracemalloc saw {total / MB:.1f} MB of a 50 MB raw malloc")
    print(f"[raw-malloc] raw malloc invisible to tracemalloc: {'PASS' if total < 5 * MB else 'FAIL'}")
    libc.free(ptr)


if __name__ == "__main__":
    check_maxrss_units()
    check_debugmallocstats()
    check_pymalloc_retention()
    check_tracemalloc_numpy()
    check_raw_malloc_invisible()
