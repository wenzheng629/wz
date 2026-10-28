#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>
#include <string>

namespace Zhu2014
{
using Tensor = std::array<double, 6>;
using Tangent = std::array<Tensor, 6>;

// Order: xx, yy, zz, xy, yz, xz.
// Shear components are tensor shear, not engineering shear.
inline double trace(const Tensor & a)
{
  return a[0] + a[1] + a[2];
}

inline double dot(const Tensor & a, const Tensor & b)
{
  double r = 0;
  for (unsigned i = 0; i < 6; ++i)
    r += (i < 3 ? 1.0 : 2.0) * a[i] * b[i];
  return r;
}

inline Tensor deviator(Tensor a)
{
  const double p = trace(a) / 3;
  for (unsigned i = 0; i < 3; ++i)
    a[i] -= p;
  return a;
}

inline double q(const Tensor & a)
{
  return std::sqrt(1.5 * dot(deviator(a), deviator(a)));
}

struct Parameters
{
  double ct = .0074, ce = .0015, m = .702;
  double mf0 = 2.322, nf = .888, mc = 1.562;
  double alpha = .99, beta = .08, d = 1.022;
  double gamma_dm = 3.3, gamma_den = 150, gamma_u = 30;
  double pa = 1e5, nu = .3, pressure_floor = 1e3;

  void validate() const
  {
    for (double v : {ct, ce, m, mf0, nf, mc, alpha, beta, d,
                     gamma_dm, gamma_den, gamma_u,
                     pa, nu, pressure_floor})
      if (!std::isfinite(v))
        throw std::invalid_argument("Nonfinite Zhu2014 parameter");

    if (!(ct > ce && ce > 0 && m > 0 &&
          mf0 > 0 && mc > 0 && alpha > 0 &&
          beta > 0 && d > 0 && pa > 0 &&
          nu > -1 && nu < .5 && pressure_floor > 0 &&
          gamma_dm >= 0 && gamma_den >= 0 && gamma_u >= 0))
      throw std::invalid_argument(
          "Invalid Zhu2014 parameters: require "
          "ct>ce>0, beta>0, -1<nu<0.5");
  }
};

struct State
{
  Tensor stress{}, plastic{};
  double eta_max = 0;
  double eta_u = 0;
  double evp0 = 0;
  double inv_h = 0;

  // 1: loading, -1: unloading, 2: reloading
  int branch = 1;
  bool has_unloaded = false;
};

class Model
{
public:
  explicit Model(Parameters parameters) : a(parameters)
  {
    a.validate();
  }

  const Parameters a;

  double pressure(const Tensor & stress) const
  {
    for (double x : stress)
      if (!std::isfinite(x))
        throw std::runtime_error("Nonfinite stress");

    const double raw = trace(stress) / 3;

    if (raw < -1e-8 * a.pressure_floor)
      throw std::runtime_error(
          "Tensile mean stress: outside the implemented domain");

    // Regularize coefficients only; do not insert fictitious stress.
    return std::max(raw, a.pressure_floor);
  }

  void check(const Tensor & stress) const
  {
    const double p = pressure(stress);
    const double mf = a.mf0 * std::pow(p / a.pa, a.nf - 1);

    if (q(stress) / p >= mf)
      throw std::runtime_error(
          "eta >= Mf: post-peak response is not implemented");
  }

  Tensor elastic(const Tensor & e, double p) const
  {
    const double K =
        std::pow(a.pa, a.m) /
        (a.m * a.ce * std::pow(p, a.m - 1));

    const double G =
        3 * (1 - 2 * a.nu) * K / (2 * (1 + a.nu));

    Tensor r = deviator(e);

    for (unsigned i = 0; i < 6; ++i)
      r[i] = 2 * G * r[i] + (i < 3 ? K * trace(e) : 0);

    return r;
  }

  Tensor direction(const Tensor & s,
                   double p,
                   double eta,
                   double M,
                   bool unloading) const
  {
    const double v =
        a.alpha * (eta + a.beta * M) * (M - eta);
    const double norm = std::hypot(v, eta);
    const double nv =
        unloading ? -std::abs(v / norm) : v / norm;

    Tensor r{};

    for (unsigned i = 0; i < 6; ++i)
      r[i] = 1.5 * s[i] / (p * norm) +
             (i < 3 ? nv / 3 : 0);

    // Analytic q -> 0 limit; beta must be positive.
    return r;
  }

  double inverseH(double p,
                  double eta,
                  double mf,
                  const State & s) const
  {
    const double rf = eta / mf;
    const double rc = eta / a.mc;

    const double omega_log =
        std::log1p(rf * rf) - std::log1p(rc * rc) +
        std::log1p(rf) - std::log1p(rc) +
        a.d * std::log1p(-rf) + rc;

    const double c =
        s.branch == -1 ? a.ce : a.ct - a.ce;

    double h_log =
        a.m * std::log(a.pa) + omega_log -
        std::log(a.m * c) -
        (a.m - 1) * std::log(p);

    if (s.branch != 1)
    {
      if (s.eta_max > 0 && a.gamma_dm > 0)
      {
        if (eta == 0)
          return 0;

        h_log -=
            a.gamma_dm * std::log(eta / s.eta_max);
      }

      h_log += a.gamma_den * s.evp0;
    }

    if (s.branch == -1 && a.gamma_u > 0)
    {
      if (s.eta_u == 0)
        return 0;

      h_log += a.gamma_u *
          std::max(0.0, std::log(a.mc / s.eta_u));
    }

    const double inv = std::exp(-h_log);

    if (!std::isfinite(inv))
      throw std::runtime_error(
          "Nonfinite plastic compliance");

    return inv;
  }

  State step(const State & old, const Tensor & de) const
  {
    check(old.stress);

    for (double x : de)
      if (!std::isfinite(x))
        throw std::runtime_error(
            "Nonfinite strain increment");

    if (dot(de, de) == 0)
      return old;

    State s = old;

    const double p = pressure(old.stress);
    const double eta = q(old.stress) / p;
    const double mf =
        a.mf0 * std::pow(p / a.pa, a.nf - 1);

    const Tensor n =
        direction(deviator(old.stress), p, eta, mf, false);
    const Tensor trial = elastic(de, p);

    const double L = dot(n, trial);

    s.eta_max = std::max(s.eta_max, eta);

    const bool neutral =
        std::abs(L) <=
        1e-12 * std::max(1.0, std::sqrt(dot(trial, trial)));

    if (!neutral)
    {
      if (L < 0)
      {
        if (old.branch != -1)
          s.eta_u = eta;

        s.branch = -1;
        s.has_unloaded = true;
      }
      else
      {
        if (old.branch == -1)
          s.evp0 = std::max(0.0, trace(old.plastic));

        s.branch =
            s.has_unloaded && eta < s.eta_max - 1e-12
                ? 2
                : 1;
      }
    }

    const Tensor ng =
        direction(deviator(old.stress),
                  p, eta, a.mc, s.branch == -1);

    const Tensor Cng = elastic(ng, p);

    s.inv_h = neutral ? 0 : inverseH(p, eta, mf, s);

    const double den = 1 + s.inv_h * dot(n, Cng);

    if (!(den > 1e-12) || !std::isfinite(den))
      throw std::runtime_error(
          "Singular/nonpositive incremental denominator");

    const double dlambda = s.inv_h * L / den;

    for (unsigned i = 0; i < 6; ++i)
    {
      s.stress[i] += trial[i] - Cng[i] * dlambda;
      s.plastic[i] += ng[i] * dlambda;
    }

    check(s.stress);

    s.eta_max = std::max(
        s.eta_max, q(s.stress) / pressure(s.stress));

    return s;
  }

  State integrate(const State & old,
                  Tensor de,
                  unsigned count) const
  {
    if (!count)
      throw std::invalid_argument(
          "substeps must be positive");

    for (double & x : de)
      x /= count;

    State s = old;

    for (unsigned i = 0; i < count; ++i)
      s = step(s, de);

    return s;
  }

  // Differentiate the complete substep mapping.
  // All perturbations restart from the same committed old state.
  Tangent tangent(const State & old,
                  const Tensor & de,
                  unsigned count,
                  double h) const
  {
    if (!(h > 0) || !std::isfinite(h))
      throw std::invalid_argument(
          "fd_step must be positive and finite");

    const State base = integrate(old, de, count);
    Tangent J{};

    for (unsigned j = 0; j < 6; ++j)
    {
      Tensor ep = de;
      Tensor em = de;
      ep[j] += h;
      em[j] -= h;

      State plus, minus;
      bool okp = true;
      bool okm = true;

      try
      {
        plus = integrate(old, ep, count);
      }
      catch (const std::runtime_error &)
      {
        okp = false;
      }

      try
      {
        minus = integrate(old, em, count);
      }
      catch (const std::runtime_error &)
      {
        okm = false;
      }

      if (!okp && !okm)
        throw std::runtime_error(
            "Both tangent perturbations leave "
            "the admissible domain");

      for (unsigned i = 0; i < 6; ++i)
      {
        if (okp && okm)
          J[i][j] =
              (plus.stress[i] - minus.stress[i]) / (2 * h);
        else if (okp)
          J[i][j] =
              (plus.stress[i] - base.stress[i]) / h;
        else
          J[i][j] =
              (base.stress[i] - minus.stress[i]) / h;
      }
    }

    return J;
  }
};
} // namespace Zhu2014