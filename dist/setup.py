from setuptools import setup

setup(
        name='gmail.py',
        version='1.0',
        author='Harshavardhan Rangan',
        url='https://github.com/hrangan/gmail.py',
        packages=['gmail',],
        scripts=['gmail/gmail.py',],
        description='A command line tool to check gmail',
        long_description=open('README').read(),
        entry_points={
            'console_scripts': ['gmail = gmail:main',]
            }
        )
