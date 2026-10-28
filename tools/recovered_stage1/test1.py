"""
朱晟等（2014）广义塑性模型：第一阶段材料点程序。

单位：Pa；应变为无量纲小数；压缩为正。
适用域：p > 0，q >= 0，eta < Mf，sigma_c = 0。
采用常数 Mc，不包含 Lode 角修正。

应力控制：默认中点积分。
应变控制：冻结子步起点系数。
历史状态机为本版数值约定，不代表作者公开程序。
"""

from dataclasses import dataclass, replace, asdict
from pathlib import Path
import argparse
import csv
import json
import math
import os
import tempfile


@dataclass(frozen=True)
class Parameters:
    # 论文表2：花岗岩堆石料
    ct: float = 0.0074
    ce: float = 0.0015
    m: float = 0.702
    mf0: float = 2.322
    nf: float = 0.888
    mc: float = 1.562
    alpha: float = 0.99
    beta: float = 0.08
    d: float = 1.022
    gamma_dm: float = 3.3
    gamma_den: float = 150.0
    gamma_u: float = 30.0

    # pa 为本程序显式选值；nu 采用正文建议值
    pa: float = 100000.0
    nu: float = 0.3

    def __post_init__(self):
        if not all(math.isfinite(v) for v in self.__dict__.values()):
            raise ValueError("Parameters must be finite")
        if not (self.ct > self.ce > 0 and self.m > 0 and self.pa > 0):
            raise ValueError("Require ct > ce > 0, m > 0, pa > 0")
        if not (-1 < self.nu < 0.5 and self.mc > 0 and self.mf0 > 0):
            raise ValueError("Invalid elastic or strength parameters")
        if not (self.alpha > 0 and self.beta > 0 and self.d > 0):
            raise ValueError("Stage 1 requires alpha, beta, d > 0")
        if min(self.gamma_dm, self.gamma_den, self.gamma_u) < 0:
            raise ValueError("History exponents must be nonnegative")


@dataclass(frozen=True)
class State:
    p: float
    q: float = 0.0
    ev: float = 0.0
    es: float = 0.0
    evp: float = 0.0
    esp: float = 0.0
    eta_max: float = 0.0
    eta_u: float = 0.0
    evp0: float = 0.0
    branch: str = "L"
    has_unloaded: bool = False

    @property
    def ea(self):
        return self.ev / 3 + self.es

    @property
    def er(self):
        return self.ev / 3 - self.es / 2


class DomainError(ValueError):
    pass


class Model:
    def __init__(self, parameters=Parameters()):
        self.a = parameters

    def check_stress(self, p, q):
        if not (
            math.isfinite(p) and math.isfinite(q)
            and p > 0 and q >= 0
        ):
            raise DomainError("Stage 1 requires finite p > 0 and q >= 0")
        mf = self.a.mf0 * (p / self.a.pa) ** (self.a.nf - 1)
        if q / p >= mf:
            raise DomainError(
                "eta >= Mf: failure/post-peak integration is not implemented"
            )
        return mf

    def initial(self, p, q=0.0):
        self.check_stress(p, q)
        # 这是给定初始应力下的零应变参考状态，
        # 并未模拟此前的固结历史。
        return State(p=p, q=q, eta_max=q / p)

    def elastic(self, p):
        a = self.a
        bulk = a.pa ** a.m / (a.m * a.ce * p ** (a.m - 1))
        young = 3 * (1 - 2 * a.nu) * bulk
        return bulk, 3 * young / (2 * (1 + a.nu))  # K、3G

    def direction(self, eta, ratio):
        # 将方向表达式分子分母同乘 eta，消除 1/eta 奇点。
        # beta > 0 时，eta=0 的精确极限为 (1, 0)。
        v = self.a.alpha * (eta + self.a.beta * ratio) * (ratio - eta)
        norm = math.hypot(v, eta)
        return v / norm, eta / norm

    def directions(self, p, q):
        mf = self.check_stress(p, q)
        return (
            self.direction(q / p, mf),
            self.direction(q / p, self.a.mc),
        )

    def history(self, old, projection, scale):
        if abs(projection) <= 1e-12 * max(scale, 1.0):
            return old, "N"

        eta = old.q / old.p
        hist = replace(old, eta_max=max(old.eta_max, eta))

        if projection < 0:
            if old.branch != "U":
                hist = replace(hist, eta_u=eta, has_unloaded=True)
            return replace(hist, branch="U"), "U"

        if old.branch == "U":
            # 再加载起点快照，不随再加载子步重复更新。
            hist = replace(hist, evp0=max(old.evp, 0.0))

        branch = (
            "RL"
            if hist.has_unloaded and eta < hist.eta_max - 1e-12
            else "L"
        )
        return replace(hist, branch=branch), branch

    def compliance(self, p, q, hist, branch):
        """返回 1/H 和 log(H)，避免大模量直接计算溢出。"""
        a = self.a
        mf = self.check_stress(p, q)
        eta = q / p
        rf, rc = eta / mf, eta / a.mc

        # 论文式（14）的 Omega
        log_omega = (
            math.log1p(rf * rf) - math.log1p(rc * rc)
            + math.log1p(rf) - math.log1p(rc)
            + a.d * math.log1p(-rf) + rc
        )

        compressibility = a.ce if branch == "U" else a.ct - a.ce
        log_h = (
            a.m * math.log(a.pa) + log_omega
            - math.log(a.m * compressibility)
            - (a.m - 1) * math.log(p)
        )

        if branch in ("U", "RL"):
            if hist.eta_max > 0 and a.gamma_dm > 0:
                if eta == 0:
                    return 0.0, math.inf
                log_h += -a.gamma_dm * math.log(eta / hist.eta_max)
            log_h += a.gamma_den * hist.evp0

        if branch == "U" and a.gamma_u > 0:
            if hist.eta_u == 0:
                return 0.0, math.inf
            log_h += a.gamma_u * max(
                0.0, math.log(a.mc / hist.eta_u)
            )

        inverse_h = math.exp(-log_h)
        if not math.isfinite(inverse_h):
            raise DomainError(
                "Nonfinite compliance; reduce increment/check parameters"
            )
        return inverse_h, log_h

    def coefficients(self, p, q, hist, branch):
        n, ng = self.directions(p, q)
        if branch == "U":
            ng = -abs(ng[0]), ng[1]

        if branch == "N":
            inv_h, log_h = 0.0, math.inf
        else:
            inv_h, log_h = self.compliance(p, q, hist, branch)

        return self.elastic(p), n, ng, inv_h, log_h

    @staticmethod
    def diagnostic(branch, log_h, dlambda, p, q, inv_h):
        return dict(
            branch=branch,
            H=math.exp(log_h) if log_h < 709 else math.inf,
            log_H=log_h,
            inv_H=inv_h,
            dlambda=dlambda,
            eval_p=p,
            eval_q=q,
        )

    def stress_step(self, old, dp, dq, rule="midpoint"):
        """应力控制；返回新试算状态，不修改 old。"""
        if rule not in ("left", "midpoint"):
            raise ValueError("rule must be left or midpoint")
        if dp == 0 and dq == 0:
            return old, {"branch": "N", "H": math.inf, "dlambda": 0.0}

        self.check_stress(old.p, old.q)
        self.check_stress(old.p + dp, old.q + dq)

        fraction = 0.5 if rule == "midpoint" else 0.0
        p, q = old.p + fraction * dp, old.q + fraction * dq
        n, _ = self.directions(p, q)

        hist, branch = self.history(
            old,
            n[0] * dp + n[1] * dq,
            math.hypot(dp, dq),
        )
        de, n, ng, inv_h, log_h = self.coefficients(
            p, q, hist, branch
        )

        dlambda = inv_h * (n[0] * dp + n[1] * dq)
        devp, desp = ng[0] * dlambda, ng[1] * dlambda

        new = replace(
            hist,
            p=old.p + dp,
            q=old.q + dq,
            ev=old.ev + dp / de[0] + devp,
            es=old.es + dq / de[1] + desp,
            evp=old.evp + devp,
            esp=old.esp + desp,
            eta_max=max(
                hist.eta_max,
                (old.q + dq) / (old.p + dp),
            ),
        )
        return new, self.diagnostic(
            branch, log_h, dlambda, p, q, inv_h
        )

    def strain_step(self, old, dev, des):
        """
        应变控制：冻结子步起点系数。

        返回的切线只对应当前子步，
        不能直接当作完整多子步映射的算法一致切线。
        """
        self.check_stress(old.p, old.q)
        de = self.elastic(old.p)
        n, _ = self.directions(old.p, old.q)
        trial = de[0] * dev, de[1] * des
        projection = n[0] * trial[0] + n[1] * trial[1]

        hist, branch = self.history(
            old, projection, math.hypot(*trial)
        )
        de, n, ng, inv_h, log_h = self.coefficients(
            old.p, old.q, hist, branch
        )

        a = de[0] * ng[0], de[1] * ng[1]
        b = n[0] * de[0], n[1] * de[1]
        denominator = 1 + inv_h * (
            n[0] * a[0] + n[1] * a[1]
        )
        if denominator <= 1e-12:
            raise DomainError(
                "Nonpositive/singular incremental denominator; "
                "no silent clipping"
            )

        dlambda = inv_h * projection / denominator
        devp, desp = ng[0] * dlambda, ng[1] * dlambda
        dp = trial[0] - de[0] * devp
        dq = trial[1] - de[1] * desp
        self.check_stress(old.p + dp, old.q + dq)

        new = replace(
            hist,
            p=old.p + dp,
            q=old.q + dq,
            ev=old.ev + dev,
            es=old.es + des,
            evp=old.evp + devp,
            esp=old.esp + desp,
            eta_max=max(
                hist.eta_max,
                (old.q + dq) / (old.p + dp),
            ),
        )

        tangent = tuple(
            tuple(
                (de[i] if i == j else 0.0)
                - a[i] * b[j] * inv_h / denominator
                for j in range(2)
            )
            for i in range(2)
        )
        info = self.diagnostic(
            branch, log_h, dlambda, old.p, old.q, inv_h
        )
        info["tangent"] = tangent
        return new, info

    def integrate_strain(self, old, dev, des, substeps=100):
        if not isinstance(substeps, int) or substeps < 1:
            raise ValueError("substeps must be a positive integer")
        state = old
        for _ in range(substeps):
            state, _ = self.strain_step(
                state, dev / substeps, des / substeps
            )
        return state


def write_csv(path, rows):
    # utf-8-sig 便于使用 Excel 打开
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def cycle_run(n=400, cycles=10):
    m = Model()
    s = m.initial(700000)

    fields = dict(
        branch="INIT",
        H=math.nan,
        log_H=math.nan,
        inv_H=math.nan,
        dlambda=0,
        eval_p=s.p,
        eval_q=s.q,
    )

    rows = []

    def row(state, info, cycle, leg):
        data = asdict(state)
        data.update(info)
        data.update(
            step=len(rows),
            cycle=cycle,
            leg=leg,
            ea=state.ea,
            er=state.er,
        )
        return data

    rows.append(row(s, fields, 0, "initial"))
    summaries = []

    # 围压700 kPa；先加载 O→B，再计算 B→A→B 循环。
    # O/A: q=0, p=700 kPa
    # B:   q=420 kPa, p=840 kPa
    legs = [(0, "first_load", 420000)]
    for cycle in range(1, cycles + 1):
        legs += [
            (cycle, "unload", 0),
            (cycle, "reload", 420000),
        ]

    peak = None
    first_peak = None

    for cycle, leg, target_q in legs:
        start_q = s.q

        for j in range(1, n + 1):
            q = start_q + (target_q - start_q) * j / n
            p = 700000 + q / 3
            s, info = m.stress_step(s, p - s.p, q - s.q)
            rows.append(row(s, info, cycle, leg))

        if leg == "first_load":
            peak = first_peak = s

        if leg == "reload":
            summaries.append(dict(
                cycle=cycle,
                p=s.p,
                q=s.q,
                residual_evp=s.evp - peak.evp,
                residual_esp=s.esp - peak.esp,
                residual_ev=s.ev - peak.ev,
                residual_ea=s.ea - peak.ea,
                cumulative_evp=s.evp - first_peak.evp,
                cumulative_esp=s.esp - first_peak.esp,
                cumulative_ev=s.ev - first_peak.ev,
                cumulative_ea=s.ea - first_peak.ea,
            ))
            peak = s

    return rows, summaries


def plot(out, rows, summaries, convergence, iso):
    os.environ.setdefault(
        "MPLCONFIGDIR",
        str(Path(tempfile.gettempdir()) / "zhu2014-mpl-cache"),
    )

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(
        2, 2, figsize=(12, 8), constrained_layout=True
    )
    colors = {
        "first_load": "#111827",
        "unload": "#2563eb",
        "reload": "#d97706",
    }

    for leg in colors:
        cycles = sorted(
            set(r["cycle"] for r in rows if r["leg"] == leg)
        )
        for cycle in cycles:
            subset = [
                r for r in rows
                if r["leg"] == leg and r["cycle"] == cycle
            ]
            axes[0, 0].plot(
                [r["ea"] * 100 for r in subset],
                [r["q"] / 1000 for r in subset],
                color=colors[leg],
                lw=1,
                label=leg if cycle in (0, 1) else None,
            )

    axes[0, 0].set(
        xlabel="Axial strain (%)",
        ylabel="q (kPa)",
        title="Compression-only cyclic response",
    )
    axes[0, 0].legend(fontsize=8)

    axes[0, 1].plot(
        [r["cycle"] for r in summaries],
        [r["cumulative_evp"] * 100 for r in summaries],
        "o-",
        label="volumetric plastic",
    )
    axes[0, 1].plot(
        [r["cycle"] for r in summaries],
        [r["cumulative_esp"] * 100 for r in summaries],
        "s-",
        label="shear plastic",
    )
    axes[0, 1].set(
        xlabel="Closed cycle number",
        ylabel="Strain since first B (%)",
        title="Accumulation at the same peak stress",
    )
    axes[0, 1].legend(fontsize=8)

    axes[1, 0].plot(
        [r["substeps_per_leg"] for r in convergence],
        [r["residual_evp"] * 100 for r in convergence],
        "o-",
    )
    axes[1, 0].set(
        xscale="log",
        xlabel="Substeps per leg",
        ylabel="Cycle 1 residual plastic volume (%)",
        title="Step refinement",
    )

    axes[1, 1].loglog(
        [r["substeps"] for r in iso],
        [r["relative_error"] for r in iso],
        "o-",
    )
    axes[1, 1].set(
        xlabel="Substeps",
        ylabel="Relative error vs equation (5)",
        title="Isotropic compression analytic check",
    )

    for ax in axes.flat:
        ax.grid(True, alpha=0.25)

    fig.suptitle(
        "Zhu et al. (2014) - stage 1 verification, "
        "not Figure 6 reproduction",
        fontsize=13,
    )
    fig.savefig(out / "verification.png", dpi=180)
    fig.savefig(out / "verification.pdf")
    plt.close(fig)


def run(out):
    out.mkdir(parents=True, exist_ok=True)

    # 1. 首次加载与10次循环
    rows, summaries = cycle_run()
    write_csv(out / "cycle_history.csv", rows)
    write_csv(out / "cycle_summary.csv", summaries)

    # 2. 第一圈的步长收敛检查
    convergence = []
    for n in (50, 100, 200, 400, 800, 1600):
        _, results = cycle_run(n, 1)
        convergence.append(
            dict(substeps_per_leg=n, **results[0])
        )

    ref = convergence[-1]["residual_evp"]
    for r in convergence:
        r["evp_relative_difference_to_1600"] = (
            abs(r["residual_evp"] - ref) / abs(ref)
        )
    write_csv(out / "convergence.csv", convergence)

    if convergence[-2]["evp_relative_difference_to_1600"] > 0.001:
        raise RuntimeError(
            "Cycle convergence failed: 800 vs 1600 exceeds 0.1%"
        )

    # 3. 等向压缩，与论文式（5）解析解对照
    m = Model()
    iso = []
    for n in (20, 40, 80, 160, 320):
        s = m.initial(100000)
        for _ in range(n):
            s, _ = m.stress_step(s, 600000 / n, 0)

        exact = m.a.ct * (7 ** m.a.m - 1)
        iso.append(dict(
            substeps=n,
            ev=s.ev,
            exact_ev=exact,
            relative_error=abs(s.ev - exact) / abs(exact),
            es=s.es,
        ))
    write_csv(out / "isotropic_check.csv", iso)

    # 4. 将应力控制产生的应变历程交给应变积分器重放
    # 两种积分分别为中点与左端方案，误差应随加密减小。
    replay = []
    for n in (100, 200, 400, 800):
        history, _ = cycle_run(n, 1)
        strain_state = m.initial(700000)

        for previous, current in zip(history, history[1:]):
            strain_state, _ = m.strain_step(
                strain_state,
                current["ev"] - previous["ev"],
                current["es"] - previous["es"],
            )

        last = history[-1]
        error = math.hypot(
            strain_state.p - last["p"],
            strain_state.q - last["q"],
        )
        replay.append(dict(
            substeps_per_leg=n,
            p=strain_state.p,
            q=strain_state.q,
            target_p=last["p"],
            target_q=last["q"],
            stress_error_Pa=error,
        ))

    write_csv(out / "strain_replay.csv", replay)
    if not all(
        a["stress_error_Pa"] > b["stress_error_Pa"]
        for a, b in zip(replay, replay[1:])
    ):
        raise RuntimeError("Strain replay does not converge")

    metadata = dict(
        parameters=asdict(Parameters()),
        units="Pa; dimensionless strain",
        stress_convention=(
            "compression positive; q = axial - radial >= 0"
        ),
        method=(
            "midpoint stress-control; "
            "frozen left-point strain-control"
        ),
        initial=(
            "p=700 kPa, q=0, all strain/history zero "
            "(reference state)"
        ),
        path=(
            "sigma_r=700 kPa; initial q:0->420 kPa; "
            "cycles q:420->0->420 kPa"
        ),
        figure6_reproduction=False,
        scope="stage 1 axisymmetric compression only",
        peak_first={
            k: rows[400][k]
            for k in ("p", "q", "ev", "es", "evp", "esp")
        },
        first_cycle=summaries[0],
        last_cycle=summaries[-1],
    )
    (out / "metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    plot(out, rows, summaries, convergence, iso)

    print(json.dumps(dict(
        first_cycle=summaries[0],
        last_cycle=summaries[-1],
        convergence=convergence[-2],
        strain_replay=replay[-1],
    ), indent=2))
    print("\nResults:", out.resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).parent / "results",
    )
    run(parser.parse_args().out)