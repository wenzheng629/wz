# Shared input. Run isotropic.i, triaxial.i or cycle.i.

[Mesh]
  type = GeneratedMesh
  dim = 3
  nx = 1
  ny = 1
  nz = 1
  elem_type = HEX8
[]

[GlobalParams]
  displacements = 'disp_x disp_y disp_z'
  use_displaced_mesh = false
[]

[Physics/SolidMechanics/QuasiStatic/all]
  strain = SMALL
  incremental = true
  add_variables = true
  generate_output = 'stress_xx stress_yy stress_zz strain_xx strain_yy strain_zz'
[]

[BCs]
  [fix_x]
    type = DirichletBC
    variable = disp_x
    boundary = left
    value = 0
  []
  [fix_y]
    type = DirichletBC
    variable = disp_y
    boundary = bottom
    value = 0
  []
  [fix_z]
    type = DirichletBC
    variable = disp_z
    boundary = back
    value = 0
  []

  [Pressure]
    [radial]
      boundary = 'right top'
      function = radial_pressure
      use_displaced_mesh = false
    []
    [axial]
      boundary = front
      function = axial_pressure
      use_displaced_mesh = false
    []
  []
[]

[Materials/gp]
  type = RockfillGeneralizedPlasticity

  # Paper Table 2 granite: verification parameters.
  ct = 0.0074
  ce = 0.0015
  m = 0.702
  mf0 = 2.322
  nf = 0.888
  mc = 1.562
  alpha = 0.99
  beta = 0.08
  d = 1.022
  gamma_dm = 3.3
  gamma_den = 150
  gamma_u = 30

  pa = 1e5
  nu = 0.3
  pressure_floor = 1000
  substeps = 32
  fd_step = 1e-8
[]

[Postprocessors]
  [p]
    type = ElementAverageMaterialProperty
    mat_prop = gp_p
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [q]
    type = ElementAverageMaterialProperty
    mat_prop = gp_q
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [ev]
    type = ElementAverageMaterialProperty
    mat_prop = gp_ev
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [evp]
    type = ElementAverageMaterialProperty
    mat_prop = gp_evp
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [branch]
    type = ElementAverageMaterialProperty
    mat_prop = gp_branch
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [axial_strain_tension_positive]
    type = ElementAverageValue
    variable = strain_zz
    execute_on = 'INITIAL TIMESTEP_END'
  []
[]

[Preconditioning/smp]
  type = SMP
  full = true
[]

[Executioner]
  type = Transient
  solve_type = NEWTON
  dt = 0.01
  nl_abs_tol = 1e-7
  nl_rel_tol = 1e-10
  nl_max_its = 40
  l_tol = 1e-10
  petsc_options_iname = '-ksp_type -pc_type'
  petsc_options_value = 'preonly lu'
[]

[Outputs]
  csv = true
  exodus = true
[]