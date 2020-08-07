# from games import admin, deleting_entries, generic_functions, models, naming, tests, urls, views
#
# # This solution that dynamically creates the __all__ method isn't probably supported by pycharm
# # from os.path import dirname, basename, isfile
# # import glob
# # modules = glob.glob(dirname(__file__)+"/*.py")
# # __all__ = [basename(f)[:-3] for f in modules if isfile(f) and not basename(f).startswith('_') and not f.endswith('__init__.py')]
# # print [basename(f)[:-3] for f in modules if isfile(f) and not basename(f).startswith('_') and not f.endswith('__init__.py')]
#
# # Using the __all__ method caused an unsupported django 1.9 warning
# __all__ = [admin, deleting_entries, generic_functions, models, naming, tests, urls, views]

default_app_config = 'games.apps.GamesConfig'
