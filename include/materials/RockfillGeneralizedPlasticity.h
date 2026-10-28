#pragma once

#include "ComputeStressBase.h"
#include "Zhu2014Core.h"

class RockfillGeneralizedPlasticity : public ComputeStressBase
{
public:
  static InputParameters validParams();
  RockfillGeneralizedPlasticity(
      const InputParameters & parameters);

protected:
  void initQpStatefulProperties() override;
  void computeQpStress() override;

  const MaterialProperty<RankTwoTensor> & _increment;
  const MaterialProperty<RankTwoTensor> & _old_stress;

  MaterialProperty<RankTwoTensor> & _plastic;
  const MaterialProperty<RankTwoTensor> & _old_plastic;

  MaterialProperty<Real> & _eta_max;
  const MaterialProperty<Real> & _old_eta_max;

  MaterialProperty<Real> & _eta_u;
  const MaterialProperty<Real> & _old_eta_u;

  MaterialProperty<Real> & _evp0;
  const MaterialProperty<Real> & _old_evp0;

  MaterialProperty<Real> & _branch;
  const MaterialProperty<Real> & _old_branch;

  MaterialProperty<Real> & _unloaded;
  const MaterialProperty<Real> & _old_unloaded;

  MaterialProperty<Real> & _p;
  MaterialProperty<Real> & _q;
  MaterialProperty<Real> & _evp;
  MaterialProperty<Real> & _ev;
  MaterialProperty<Real> & _inv_h;

  const Real _initial_pressure;
  const Real _fd_step;
  const unsigned int _substeps;

  Zhu2014::Parameters _parameters;
};