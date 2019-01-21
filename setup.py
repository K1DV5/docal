# -{python %f install}-
# -{python %f sdist bdist_wheel --universal}-
import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='doCal',
    version='0.4.0',
    author='K1DV5',
    author_email='kidusadugna@gmail.com',
    description='Inject Python calculations into Word and LaTeX documents with ease!',
    long_description_content_type='text/markdown',
    long_description=long_description,
    url='https://github.com/K1DV5/doCal',
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': [
            'docal = docal.__main__:main'
            ]
        },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent'
        ]
)

