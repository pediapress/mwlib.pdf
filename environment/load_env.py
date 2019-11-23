"""
-w writer
-c collection samples/amphibious_aircrafts.zip
-o samples/amphibious_aircrafts.pdf

env.images
env.metabook
env.wiki
"""
def get_environment(self):
    from mwlib.status import Status
    from mwlib import nuwiki

    env = self.parser.makewiki()
    if (isinstance(env.wiki, (nuwiki.NuWiki, nuwiki.adapt))
            or isinstance(env, wiki.MultiEnvironment)):
        self.status = Status(self.options.status_file, progress_range=(0, 100))
        return env

    from mwlib.apps.buildzip import make_zip
    self.zip_filename = make_zip(output=self.options.keep_zip,
                                 options=self.options, metabook=env.metabook, status=self.status)

    if env.images:
        try:
            env.images.clear()
        except OSError as err:
            if err.errno != errno.ENOENT:
                raise

    env = wiki.makewiki(self.zip_filename)
    self.status = Status(self.options.status_file, progress_range=(34, 100))
    return env