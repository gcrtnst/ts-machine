#!/usr/bin/env python3
import setuptools

with open('README.md', 'r') as fp:
    long_description = fp.read()

setuptools.setup(
    name='ts_machine',
    version='2019.7.16',
    description='ニコニコ生放送のタイムシフト予約を自動化',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/gcrtnst/ts_machine',
    author='gcrtnst',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: Japanese',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Games/Entertainment',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Multimedia :: Video',
    ],
    keywords='niconico time-shift',
    project_urls={
        'Source': 'https://github.com/gcrtnst/ts_machine',
        'Tracker': 'https://github.com/gcrtnst/ts_machine/issues',
    },
    packages=setuptools.find_packages(),
    install_requires=[
        'beautifulsoup4>=4.9.3',
        'Cerberus>=1.3.2',
        'html5lib>=1.1',
        'python-dateutil>=2.8.1',
        'requests>=2.24.0',
        'toml>=0.10.1',
    ],
    python_requires='~=3.7',
    entry_points={'console_scripts': {'tsm = tsm:main'}},
)
