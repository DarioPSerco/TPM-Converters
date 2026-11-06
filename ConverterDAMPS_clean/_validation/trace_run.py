"""Audit-hook tracer: records every file 'open' + final sys.modules.

Usage:
  python trace_run.py OUT.json script TARGET.py [args...]
  python trace_run.py OUT.json pytest TESTDIR
"""
import json
import os
import runpy
import sys


def main():
    out_path = sys.argv[1]
    mode = sys.argv[2]
    target = sys.argv[3]
    rest = sys.argv[4:]

    opens = set()

    def hook(event, args):
        if event == "open":
            p = args[0]
            if isinstance(p, (str, bytes)):
                try:
                    opens.add(os.path.abspath(os.fsdecode(p)))
                except Exception:
                    pass

    sys.addaudithook(hook)

    code = 0
    try:
        if mode == "script":
            sys.argv = [target] + rest
            runpy.run_path(target, run_name="__main__")
        elif mode == "pytest":
            import pytest
            code = pytest.main(["-q", target] + rest)
        else:
            raise ValueError(mode)
    except SystemExit as e:
        code = e.code
    except BaseException as e:
        code = "EXC: %r" % (e,)
    finally:
        mods = {}
        for name, m in list(sys.modules.items()):
            f = getattr(m, "__file__", None)
            if f:
                try:
                    mods[name] = os.path.abspath(f)
                except Exception:
                    pass
        with open(out_path, "w", encoding="utf-8") as fd:
            json.dump({"exit": str(code), "opens": sorted(opens),
                       "modules": mods}, fd, indent=1)
        print("TRACE_WRITTEN %s exit=%s opens=%d modules=%d"
              % (out_path, code, len(opens), len(mods)))


main()
