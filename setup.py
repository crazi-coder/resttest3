from setuptools import setup, find_packages
import py3resttest
with open(u"requirements.txt") as fp:
    install_requires = [lib_str.strip() for lib_str in fp.read().split("\n") if not lib_str.startswith("#")]

with open(u"requirements.txt") as fp:
    test_dependencies = [lib_str.strip() for lib_str in fp.read().split("\n") if not lib_str.startswith("#")]

setup(
    name='resttest3',
    version=py3resttest.__version__,
    description='Python RESTful API Testing & Micro benchmarking Tool',
    long_description='Python RESTful API Testing & Microbenchmarking Tool '
                     '\n Documentation at https://abhijo89-to.github.io/py3resttest/',
    author=py3resttest.__author__,
    author_email='abhilash@softlinkweb.com',
    url='https://github.com/abhijo89-to/py3resttest',
    keywords=['rest', 'web', 'http', 'testing', 'api'],
    classifiers=[
        'Environment :: Console',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Software Development :: Testing',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Utilities'
    ],
    packages=find_packages(),
    python_requires='>=3.5',
    license='Apache License, Version 2.0',
    install_requires=install_requires,
    tests_require=test_dependencies,
    test_suite="py3resttest.tests",
    entry_points={
        'console_scripts': ['resttest3=py3resttest.runner:main'],
    }

)
