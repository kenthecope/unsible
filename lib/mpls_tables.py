import jnpr.junos
if jnpr.junos.__version__[0] == '1':
    from jnpr.junos.factory import loadyaml
    from os.path import splitext
    _YAML_ = splitext(__file__)[0] + '.yml'
    globals().update(loadyaml(_YAML_))
else:
    from jnpr.junos.factory import loadyaml
    from os.path import splitext
    _YAML_ = splitext(__file__)[0] + '.yml'
    catalog = loadyaml( _YAML_ )
    globals().update(loadyaml(_YAML_))
