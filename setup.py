from setuptools import setup

import arggen


setup(
    name='arggen',
    version=arggen.__version__,
    py_modules=['arggen'],
    entry_points={
        'console_scripts': ['arggen=arggen:main'],
    },
    python_requires='>=3.6',
    extras_require={
        'ci': ['pytest', 'pytest-sugar', 'pytest-cov', 'codecov'],
    },
    url='https://github.com/account-login/arggen',
    license='MIT',
    author='account-login',
    author_email='',
    description='A tool to generate c++ argument parsing code.',
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Code Generators',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        'Operating System :: OS Independent',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='argument-parser option-parser c++ cpp',
)
