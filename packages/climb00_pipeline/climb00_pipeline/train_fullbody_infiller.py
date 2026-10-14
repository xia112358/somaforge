"""Compatibility alias for :mod:`generator.train_fullbody_infiller`."""
if __name__ == "__main__":
    import runpy
    runpy.run_module("generator.train_fullbody_infiller", run_name="__main__")
else:
    import importlib
    import sys
    sys.modules[__name__] = importlib.import_module("generator.train_fullbody_infiller")
