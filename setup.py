# -{python %f install}
# -{twine upload dist/*}
# -{python %f sdist bdist_wheel}
"""
:copyright: (c) 2019 by K1DV5
:license: MIT, see LICENSE for more details.
"""

VERSION = '1.0.2'

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

setup_requirements = ['pytest-runner', ]

test_requirements = ['pytest', ]

setup(
    author="Kidus Adugna",
    author_email='kidusadugna@gmail.com',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="Inject Python calculations into Word and LaTeX documents with ease!",
    entry_points={
        'console_scripts': [
            'docal=docal.__main__:main',
        ],
    },
    license="MIT license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='docal',
    name='docal',
    packages=find_packages(include=['docal']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/K1DV5/docal',
    version=VERSION,
    zip_safe=False,
)
