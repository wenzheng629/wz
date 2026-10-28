!include common.i

[Postprocessors/eta_max]
  type = ElementAverageMaterialProperty
  mat_prop = gp_eta_max
  execute_on = 'INITIAL TIMESTEP_END'
[]

[Postprocessors/eta_u]
  type = ElementAverageMaterialProperty
  mat_prop = gp_eta_u
  execute_on = 'INITIAL TIMESTEP_END'
[]

[Postprocessors/evp0]
  type = ElementAverageMaterialProperty
  mat_prop = gp_evp0
  execute_on = 'INITIAL TIMESTEP_END'
[]

[Postprocessors/inv_h]
  type = ElementAverageMaterialProperty
  mat_prop = gp_inv_h
  execute_on = 'INITIAL TIMESTEP_END'
[]

[Postprocessors/has_unloaded]
  type = ElementAverageMaterialProperty
  mat_prop = gp_has_unloaded
  execute_on = 'INITIAL TIMESTEP_END'
[]

[AuxVariables/plastic_xx]
  family = MONOMIAL
  order = CONSTANT
[]

[AuxKernels/plastic_xx]
  type = RankTwoAux
  variable = plastic_xx
  rank_two_tensor = plastic_strain
  index_i = 0
  index_j = 0
  execute_on = 'INITIAL TIMESTEP_END'
[]

[Postprocessors/plastic_xx]
  type = ElementAverageValue
  variable = plastic_xx
  execute_on = 'INITIAL TIMESTEP_END'
[]

[AuxVariables/plastic_yy]
  family = MONOMIAL
  order = CONSTANT
[]

[AuxKernels/plastic_yy]
  type = RankTwoAux
  variable = plastic_yy
  rank_two_tensor = plastic_strain
  index_i = 1
  index_j = 1
  execute_on = 'INITIAL TIMESTEP_END'
[]

[Postprocessors/plastic_yy]
  type = ElementAverageValue
  variable = plastic_yy
  execute_on = 'INITIAL TIMESTEP_END'
[]

[AuxVariables/plastic_zz]
  family = MONOMIAL
  order = CONSTANT
[]

[AuxKernels/plastic_zz]
  type = RankTwoAux
  variable = plastic_zz
  rank_two_tensor = plastic_strain
  index_i = 2
  index_j = 2
  execute_on = 'INITIAL TIMESTEP_END'
[]

[Postprocessors/plastic_zz]
  type = ElementAverageValue
  variable = plastic_zz
  execute_on = 'INITIAL TIMESTEP_END'
[]

[AuxVariables/sigma_xx]
  family = MONOMIAL
  order = CONSTANT
[]

[AuxKernels/sigma_xx]
  type = RankTwoAux
  variable = sigma_xx
  rank_two_tensor = stress
  index_i = 0
  index_j = 0
  execute_on = 'INITIAL TIMESTEP_END'
[]

[Postprocessors/sigma_xx]
  type = ElementAverageValue
  variable = sigma_xx
  execute_on = 'INITIAL TIMESTEP_END'
[]

[AuxVariables/sigma_yy]
  family = MONOMIAL
  order = CONSTANT
[]

[AuxKernels/sigma_yy]
  type = RankTwoAux
  variable = sigma_yy
  rank_two_tensor = stress
  index_i = 1
  index_j = 1
  execute_on = 'INITIAL TIMESTEP_END'
[]

[Postprocessors/sigma_yy]
  type = ElementAverageValue
  variable = sigma_yy
  execute_on = 'INITIAL TIMESTEP_END'
[]

[AuxVariables/sigma_zz]
  family = MONOMIAL
  order = CONSTANT
[]

[AuxKernels/sigma_zz]
  type = RankTwoAux
  variable = sigma_zz
  rank_two_tensor = stress
  index_i = 2
  index_j = 2
  execute_on = 'INITIAL TIMESTEP_END'
[]

[Postprocessors/sigma_zz]
  type = ElementAverageValue
  variable = sigma_zz
  execute_on = 'INITIAL TIMESTEP_END'
[]

[Postprocessors/nl_iterations]
  type = NumNonlinearIterations
  execute_on = TIMESTEP_END
[]

[Postprocessors/linear_iterations]
  type = NumLinearIterations
  execute_on = TIMESTEP_END
[]

