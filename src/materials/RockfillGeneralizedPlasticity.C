#include "RockfillGeneralizedPlasticity.h"

registerMooseObject(
    "moosexApp", RockfillGeneralizedPlasticity);

InputParameters
RockfillGeneralizedPlasticity::validParams()
{
  InputParameters p = ComputeStressBase::validParams();

  p.addClassDescription(
      "Zhu2014 small-incremental-strain rockfill stress "
      "update; fixed Mc, no Lode correction.");

  for (const auto name :
       {"ct", "ce", "m", "mf0", "nf", "mc",
        "alpha", "beta", "d",
        "gamma_dm", "gamma_den", "gamma_u"})
    p.addRequiredParam<Real>(
        name,
        "Zhu2014 material parameter; "
        "strains are dimensionless.");

  p.addRangeCheckedParam<Real>(
      "pa", 1e5, "pa>0",
      "Reference atmospheric pressure in Pa.");

  p.addRangeCheckedParam<Real>(
      "nu", .3, "nu>-1 & nu<0.5",
      "Poisson ratio.");

  p.addRangeCheckedParam<Real>(
      "pressure_floor", 1e3, "pressure_floor>0",
      "Pa: coefficient regularization near zero pressure; "
      "does not insert initial stress.");

  p.addRangeCheckedParam<Real>(
      "initial_pressure", 0, "initial_pressure>=0",
      "Pa: actual initial isotropic compressive stress; "
      "must match boundary loads.");

  p.addRangeCheckedParam<unsigned int>(
      "substeps", 32, "substeps>0",
      "Fixed local strain substeps.");

  p.addRangeCheckedParam<Real>(
      "fd_step", 1e-8, "fd_step>0",
      "Strain perturbation for full-map numerical tangent.");

  return p;
}

RockfillGeneralizedPlasticity::
RockfillGeneralizedPlasticity(const InputParameters & p)
  : ComputeStressBase(p),
    _increment(
        getMaterialPropertyByName<RankTwoTensor>(
            _base_name + "strain_increment")),
    _old_stress(
        getMaterialPropertyOldByName<RankTwoTensor>(
            _base_name + "stress")),
    _plastic(
        declareProperty<RankTwoTensor>(
            _base_name + "plastic_strain")),
    _old_plastic(
        getMaterialPropertyOldByName<RankTwoTensor>(
            _base_name + "plastic_strain")),
    _eta_max(
        declareProperty<Real>(
            _base_name + "gp_eta_max")),
    _old_eta_max(
        getMaterialPropertyOldByName<Real>(
            _base_name + "gp_eta_max")),
    _eta_u(
        declareProperty<Real>(
            _base_name + "gp_eta_u")),
    _old_eta_u(
        getMaterialPropertyOldByName<Real>(
            _base_name + "gp_eta_u")),
    _evp0(
        declareProperty<Real>(
            _base_name + "gp_evp0")),
    _old_evp0(
        getMaterialPropertyOldByName<Real>(
            _base_name + "gp_evp0")),
    _branch(
        declareProperty<Real>(
            _base_name + "gp_branch")),
    _old_branch(
        getMaterialPropertyOldByName<Real>(
            _base_name + "gp_branch")),
    _unloaded(
        declareProperty<Real>(
            _base_name + "gp_has_unloaded")),
    _old_unloaded(
        getMaterialPropertyOldByName<Real>(
            _base_name + "gp_has_unloaded")),
    _p(
        declareProperty<Real>(
            _base_name + "gp_p")),
    _q(
        declareProperty<Real>(
            _base_name + "gp_q")),
    _evp(
        declareProperty<Real>(
            _base_name + "gp_evp")),
    _ev(
        declareProperty<Real>(
            _base_name + "gp_ev")),
    _inv_h(
        declareProperty<Real>(
            _base_name + "gp_inv_h")),
    _initial_pressure(
        getParam<Real>("initial_pressure")),
    _fd_step(
        getParam<Real>("fd_step")),
    _substeps(
        getParam<unsigned int>("substeps"))
{
  _parameters.ct = getParam<Real>("ct");
  _parameters.ce = getParam<Real>("ce");
  _parameters.m = getParam<Real>("m");
  _parameters.mf0 = getParam<Real>("mf0");
  _parameters.nf = getParam<Real>("nf");
  _parameters.mc = getParam<Real>("mc");
  _parameters.alpha = getParam<Real>("alpha");
  _parameters.beta = getParam<Real>("beta");
  _parameters.d = getParam<Real>("d");
  _parameters.gamma_dm = getParam<Real>("gamma_dm");
  _parameters.gamma_den = getParam<Real>("gamma_den");
  _parameters.gamma_u = getParam<Real>("gamma_u");
  _parameters.pa = getParam<Real>("pa");
  _parameters.nu = getParam<Real>("nu");
  _parameters.pressure_floor =
      getParam<Real>("pressure_floor");

  try
  {
    _parameters.validate();
  }
  catch (const std::exception & e)
  {
    mooseError(e.what());
  }
}

void
RockfillGeneralizedPlasticity::initQpStatefulProperties()
{
  ComputeStressBase::initQpStatefulProperties();

  for (unsigned i = 0; i < 3; ++i)
    _stress[_qp](i, i) = -_initial_pressure;

  _plastic[_qp].zero();

  _eta_max[_qp] = 0;
  _eta_u[_qp] = 0;
  _evp0[_qp] = 0;
  _unloaded[_qp] = 0;
  _branch[_qp] = 1;

  _p[_qp] = _initial_pressure;
  _q[_qp] = 0;
  _evp[_qp] = 0;
  _ev[_qp] = 0;
  _inv_h[_qp] = 0;
}

void
RockfillGeneralizedPlasticity::computeQpStress()
{
  if (_extra_stress[_qp].L2norm() > 0)
    mooseError(
        "RockfillGeneralizedPlasticity does not support "
        "extra_stress; use initial_pressure.");

  static const unsigned pair[6][2] = {
      {0, 0}, {1, 1}, {2, 2},
      {0, 1}, {1, 2}, {0, 2}};

  Zhu2014::State old;
  Zhu2014::Tensor de{};

  // Convert MOOSE tension-positive tensors
  // to compression-positive core tensors.
  for (unsigned k = 0; k < 6; ++k)
  {
    const unsigned i = pair[k][0];
    const unsigned j = pair[k][1];

    old.stress[k] = -_old_stress[_qp](i, j);
    old.plastic[k] = -_old_plastic[_qp](i, j);
    de[k] = -_increment[_qp](i, j);
  }

  old.eta_max = _old_eta_max[_qp];
  old.eta_u = _old_eta_u[_qp];
  old.evp0 = _old_evp0[_qp];
  old.branch = static_cast<int>(_old_branch[_qp]);
  old.has_unloaded = _old_unloaded[_qp] > .5;

  try
  {
    const Zhu2014::Model model(_parameters);

    const auto next =
        model.integrate(old, de, _substeps);

    const auto J =
        model.tangent(old, de, _substeps, _fd_step);

    _Jacobian_mult[_qp].zero();

    for (unsigned r = 0; r < 6; ++r)
    {
      const unsigned i = pair[r][0];
      const unsigned j = pair[r][1];

      _stress[_qp](i, j) =
          _stress[_qp](j, i) = -next.stress[r];

      _plastic[_qp](i, j) =
          _plastic[_qp](j, i) = -next.plastic[r];

      for (unsigned c = 0; c < 6; ++c)
      {
        const unsigned k = pair[c][0];
        const unsigned l = pair[c][1];

        // The 6-column derivative is with respect to
        // tensor shear; split off-diagonal contributions.
        const Real value =
            J[r][c] / (k == l ? 1 : 2);

        _Jacobian_mult[_qp](i, j, k, l) =
            _Jacobian_mult[_qp](j, i, k, l) = value;

        _Jacobian_mult[_qp](i, j, l, k) =
            _Jacobian_mult[_qp](j, i, l, k) = value;
      }
    }

    _elastic_strain[_qp] =
        _mechanical_strain[_qp] - _plastic[_qp];

    _eta_max[_qp] = next.eta_max;
    _eta_u[_qp] = next.eta_u;
    _evp0[_qp] = next.evp0;
    _branch[_qp] = next.branch;
    _unloaded[_qp] = next.has_unloaded ? 1 : 0;

    _p[_qp] = Zhu2014::trace(next.stress) / 3;
    _q[_qp] = Zhu2014::q(next.stress);
    _evp[_qp] = Zhu2014::trace(next.plastic);
    _ev[_qp] = -_mechanical_strain[_qp].trace();
    _inv_h[_qp] = next.inv_h;
  }
  catch (const std::exception & e)
  {
    mooseException(
        "RockfillGeneralizedPlasticity integration failed: ",
        e.what());
  }
}