import pip

if hasattr(pip, 'main'):
    pip.main(['install', "."])
else:
    pip._internal.main(['install', "."])
