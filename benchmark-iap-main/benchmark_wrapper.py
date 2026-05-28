#!/usr/bin/env python3
"""CLI wrapper: read optional paths from stdin JSON, print benchmark JSON to stdout."""
import json
import os
import sys

def main():
    original_stdout = sys.stdout
    sys.stdout = sys.stderr

    root = os.path.dirname(os.path.abspath(__file__))
    if root not in sys.path:
        sys.path.insert(0, root)

    overrides = {}
    try:
        raw = sys.stdin.read()
        if raw.strip():
            overrides = json.loads(raw)
    except Exception as e:
        print(f"[benchmark_wrapper] stdin parse error: {e}")

    from benchmark import benchmark_metrics

    weight_overrides = overrides.get('weights') or overrides.get('config') or {}
    result = benchmark_metrics(
        staff_path=overrides.get('staffPath'),
        shift_path=overrides.get('shiftPath'),
        schedule_path=overrides.get('schedulePath'),
        weight_overrides=weight_overrides or None,
    )
    original_stdout.write(json.dumps(result, ensure_ascii=False) + '\n')
    original_stdout.flush()

if __name__ == '__main__':
    main()
