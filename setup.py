from setuptools import setup, find_packages
import sys
import os
import re


# Source files are expected to exist at: github.com/{orga}/{repo}/{name}
org = 'dilpath'
repo = 'petab_control'
name = 'petab_control'


def read(fname):
    """Read a file."""
    return open(fname).read()


def absolute_links(txt):
    """Replace relative petab github links by absolute links."""

    raw_base = \
        f"(https://raw.githubusercontent.com/{org}/{repo}/main/"
    embedded_base = \
        f"(https://github.com/{org}/{repo}/tree/main/"
    # iterate over links
    for var in re.findall(r'\[.*?\]\((?!http).*?\)', txt):
        if re.match(r'.*?.(png|svg)\)', var):
            # link to raw file
            rep = var.replace("(", raw_base)
        else:
            # link to github embedded file
            rep = var.replace("(", embedded_base)
        txt = txt.replace(var, rep)
    return txt


# 3.7.1 for NumPy
minimum_python_version = '3.7.1'
if sys.version_info < tuple(map(int, minimum_python_version.split('.'))):
    sys.exit(f'PEtab Control requires Python >= {minimum_python_version}.')

# read version from file
__version__ = ''
version_file = os.path.join(name, 'version.py')
# sets __version__
exec(read(version_file))  # pylint: disable=W0122 # nosec

#ENTRY_POINTS = {
#    'console_scripts': [
#        f'{name} = {name}.control',
#    ]
#}

# project metadata
# noinspection PyUnresolvedReferences
setup(
    name=name,
    version=__version__,
    description='Optimal control extension for PEtab',
    long_description=absolute_links(read('README.md')),
    long_description_content_type="text/markdown",
    #author='The PEtab optimal control extension developers',
    #author_email='dilan.pathirana@uni-bonn.de',
    url=f'https://github.com/{org}/{repo}',
    packages=find_packages(exclude=['doc*', 'test*']),
    install_requires=[
        'petab>=0.1.19',
        'python-slugify',  # TODO version
        #'numpy>=1.15.1',
        #'pandas>=1.2.0',
        #'matplotlib>=2.2.3',
        #'python-libsbml>=5.17.0',
        #'sympy',
        #'colorama',
        #'seaborn',
        #'pyyaml',
        #'jsonschema',
    ],
    include_package_data=True,
    tests_require=[
        #'flake8',
        'pytest',
        #'python-libcombine',
    ],
    python_requires=f'>={minimum_python_version}',
    #entry_points=ENTRY_POINTS,
    extras_require={
        'examples': [
            'amici',
            'fides',
            'pypesto',
            'more_itertools',
            'notebook',
            'numpy',
            'pandas',
            'yaml2sbml',
            'petab_timecourse',
        ],
        #'reports': ['Jinja2'],
        #'combine': ['python-libcombine>=0.2.6'],
        #'doc': [
        #    'sphinx>=3.5.3',
        #    'sphinxcontrib-napoleon>=0.7',
        #    'sphinx-markdown-tables>=0.0.15',
        #    'sphinx-rtd-theme>=0.5.1',
        #    'recommonmark>=0.7.1',
        #    'nbsphinx>=0.8.2',
        #    'm2r>=0.2.1',
        #    'ipython>=7.21.0',
        #]
    }
)
