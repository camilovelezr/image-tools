import polus.plugins as pp

print(pp.plugins)

bf = pp.plugins.BasicFlatfieldCorrectionPlugin

print(bf)

bf2 = pp.plugins.get_plugin("BasicFlatfieldCorrectionPlugin")
bf3 = pp.get_plugin("BasicFlatfieldCorrectionPlugin")
assert bf3 == bf2
print(bf2)

print(bf == bf2)

print(bf.versions)

bf_123 = pp.plugins.get_plugin("BasicFlatfieldCorrectionPlugin", "1.2.3")
print(bf_123)

