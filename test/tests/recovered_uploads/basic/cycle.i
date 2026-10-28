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
    type = PiecewiseLinear
    x = '0 1 2 3'
    y = '700000 1120000 700000 1120000'
  []
[]

[Executioner]
  end_time = 3
[]

[Outputs]
  file_base = cycle_out
[]