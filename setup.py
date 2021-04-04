#!/usr/bin/env python3
import setuptools

with open('README.md', 'r') as fp:
    long_description = fp.read()

setuptools.setup(
    name='ts_machine',
    version='2021.04.04',
    description='no longer working',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/gcrtnst/ts_machine',
    author='gcrtnst',
    license='MIT',
    project_urls={
        'Source': 'https://github.com/gcrtnst/ts_machine',
        'Tracker': 'https://github.com/gcrtnst/ts_machine/issues',
    },
    packages=setuptools.find_packages(),
    python_requires='~=3.7',
    entry_points={'console_scripts': {'tsm = tsm:main'}},
)
