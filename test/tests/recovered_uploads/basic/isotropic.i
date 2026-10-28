!include common.i

[Materials/gp]
  initial_pressure = 100000
[]

[Functions]
  [radial_pressure]
    type = ParsedFunction
    expression = '100000+600000*t'
  []
  [axial_pressure]
    type = ParsedFunction
    expression = '100000+600000*t'
  []
[]

[Executioner]
  end_time = 1
[]

[Outputs]
  file_base = isotropic_out
[]