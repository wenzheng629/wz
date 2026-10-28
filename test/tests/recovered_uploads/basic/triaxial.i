!include common.i

[Materials/gp]
  initial_pressure = 700000
[]

[Functions]
  [radial_pressure]
    type = ParsedFunction
    expression = '700000'
  []
  [axial_pressure]
    type = ParsedFunction
    expression = '700000+420000*t'
  []
[]

[Executioner]
  end_time = 1
[]

[Outputs]
  file_base = triaxial_out
[]