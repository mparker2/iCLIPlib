import glob
from setuptools import setup

setup(
    name="iCLIPLib",
    version="0.1",
    packages=["iCLIP"],
    scripts=glob.glob('bin/*.py'),
)
