import os
import re
from pathlib import Path

import setuptools

META_PATH = Path('croo', '__init__.py')
HERE = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    """
    Build an absolute path from *parts* and and return the contents of the
    resulting file.  Assume UTF-8 encoding.
    """
    with Path(HERE, *parts).open(encoding='utf-8') as f:
        return f.read()


META_FILE = read(META_PATH)


def find_meta(meta):
    """
    Extract __*meta*__ from META_FILE.
    """
    meta_match = re.search(
        r"^__{meta}__ = ['\"]([^'\"]*)['\"]".format(meta=meta), META_FILE, re.M
    )
    if meta_match:
        return meta_match.group(1)
    raise


with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='croo',
    version=find_meta("version"),
    scripts=['bin/croo'],
    python_requires='>=3.6',
    author='Jin Lee',
    author_email='leepc12@gmail.com',
    description='CRomwell Output Organizer',
    long_description='https://github.com/ENCODE-DCC/croo',
    long_description_content_type='text/markdown',
    url='https://github.com/ENCODE-DCC/croo',
    packages=setuptools.find_packages(exclude=['examples', 'docs']),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
    ],
    install_requires=['autouri>=0.2.3', 'graphviz', 'miniwdl', 'caper'],
)
