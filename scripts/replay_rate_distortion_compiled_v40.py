"""Fresh-process replay of retained V40 pure-array backup operators."""
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

module_file = Path(__file__).resolve().parents[1] / "src/acfqp/science/rate_distortion_compiled_v40.py"
spec = importlib.util.spec_from_file_location("compiled_v40_arrays", module_file)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
directory = Path(sys.argv[1])
rows = []
for path in sorted(directory.glob("*.operator.npz")):
    operator = module.CompiledOperator.load(path)
    with np.load(path.with_name(path.name.replace(".operator.npz", ".snapshot.npz")), allow_pickle=False) as snapshot:
        error = float(np.max(np.abs(operator.backup(snapshot["u"]) - snapshot["expected_backup"])))
    if error > 1e-12:
        raise ValueError("Retained compiled operator differs from author witness")
    rows.append({"operator": path.name, "max_error": error})
for name in sys.modules:
    if name == "core" or name.startswith("core.") or name == "acfqp" or name.startswith("acfqp."):
        raise RuntimeError("Fresh replay imported original model code")
if len(rows) != 6:
    raise ValueError("Expected all six frozen operators")
print(json.dumps({"operators": rows, "original_model_modules_imported": False, "valid": True}))
