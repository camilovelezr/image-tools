import polus.plugins as pp

bf = pp.plugins.BasicFlatfieldCorrectionPlugin

print(bf)

bf2 = pp.plugins.get_plugin("BasicFlatfieldCorrectionPlugin")
bf3 = pp.get_plugin("BasicFlatfieldCorrectionPlugin")
assert bf3 == bf2



bf_123 = pp.plugins.get_plugin("BasicFlatfieldCorrectionPlugin", "1.2.3")
print(bf_123)

