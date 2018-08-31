import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='doCal',
    version='0.1.2',
    author='K1DV5',
    author_email='kidusadugna@gmail.com',
    description='A Scientific Document Calculation Assistant',
    long_description_content_type='text/markdown',
    long_description=long_description,
    url='https://github.com/K1DV5/doCal',
    packages=setuptools.find_packages(),
    classifiers=(
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent'
    )
)

