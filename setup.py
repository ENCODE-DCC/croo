import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='croo',
    version='v0.1.1',
    scripts=['bin/croo'],
    author='Jin Lee',
    author_email='leepc12@gmail.com',
    description='CRomwell Output Organizer',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/ENCODE-DCC/croo',
    packages=setuptools.find_packages(exclude=['examples', 'docs']),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
    ],
    install_requires=['caper']
)
