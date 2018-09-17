from setuptools import setup, find_packages
import os.path

# Version comes from a file 'version' in the main directory, if it
# exists; otherwise it has a sensible (but probably wrong) default
def readversion():
    try:
        with open('version') as f:
            return f.read().rstrip()
    except IOError:
        return "1.0.0"


# Long description comes from the README
def readme():
    try:
        with open('README.md') as f:
            return f.read()
    except IOError:
        return "The long description appears to be missing."


# History comes from git log
def history():
    try:
        with open('HISTORY.md') as f:
            return "HISTORY\n=======\n\n" + f.read()
    except IOError:
        return ""


# The meat
setup(
    name='tpen2tei',
    version=readversion(),
    description='A module for conversion of SharedCanvas-JSON transcription data to TEI XML',
    long_description=readme() + "\n\n" + history(),
    long_description_content_type="text/markdown",

    # The project's main homepage.
    url='https://github.com/DHUniWien/tpen2tei',

    # Author details
    author='Tara L Andrews',
    author_email='tla@mit.edu',

    # Choose your license
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Topic :: Text Processing :: Markup :: XML',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],

    keywords='TEI-XML SC-JSON manuscript transcription',
    packages=find_packages(exclude=['contrib', 'tests']),
    install_requires=['lxml'],
    python_requires='>3'
)
