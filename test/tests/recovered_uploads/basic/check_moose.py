import csv
from pathlib import Path


def read(name):
    path = Path(__file__).parent / (name + "_out.csv")
    if not path.exists():
        raise SystemExit(
            f"Missing {path.name}: run the MOOSE example first."
        )
    with path.open() as f:
        return [
            {k: float(v) for k, v in row.items()}
            for row in csv.DictReader(f)
        ]


def near(actual, target, tolerance, name):
    if abs(actual - target) > tolerance:
        raise SystemExit(
            f"FAIL {name}: got {actual}, "
            f"expected {target} +/- {tolerance}"
        )


iso = read("isotropic")[-1]
exact_ev = 0.0074 * (7 ** 0.702 - 1)

near(iso["p"], 700000, 1, "isotropic p")
near(iso["q"], 0, 1, "isotropic q")
near(
    iso["ev"], exact_ev, exact_ev * 0.001,
    "equation (5) total volume strain"
)
near(
    iso["evp"],
    exact_ev * (0.0074 - 0.0015) / 0.0074,
    exact_ev * 0.001,
    "plastic volume strain",
)

tri = read("triaxial")[-1]
near(tri["p"], 840000, 1, "triaxial p")
near(tri["q"], 420000, 1, "triaxial q")
near(
    tri["evp"],
    0.005630875078183934,
    0.005630875078183934 * 0.002,
    "triaxial plastic volume strain",
)

cycle = read("cycle")
peak = min(cycle, key=lambda r: abs(r["time"] - 1))
last = cycle[-1]

near(peak["time"], 1, 1e-10, "first peak time")
near(last["time"], 3, 1e-10, "cycle end time")
near(last["p"], 840000, 1, "cycle end p")
near(last["q"], 420000, 1, "cycle end q")

residual = last["evp"] - peak["evp"]
reference = 0.0006829460346435277

near(
    residual, reference, reference * 0.005,
    "closed-cycle plastic volume strain"
)

if not any(abs(r["branch"] + 1) < 0.01 for r in cycle):
    raise SystemExit("FAIL: unloading branch missing")

if not any(abs(r["branch"] - 2) < 0.01 for r in cycle):
    raise SystemExit("FAIL: reloading branch missing")

print("PASS: three MOOSE single-element examples")
print("Cycle residual plastic volume strain =", residual)