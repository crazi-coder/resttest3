from setuptools import setup, find_packages

with open(u"requirements.txt") as fp:
    install_requires = [lib_str.strip() for lib_str in fp.read().split("\n") if not lib_str.startswith("#")]

with open(u"requirements.txt") as fp:
    test_dependencies = [lib_str.strip() for lib_str in fp.read().split("\n") if not lib_str.startswith("#")]

setup(
    name='py3resttest',
    version='1.0.0.dev',
    description='Python RESTful API Testing & Micro benchmarking Tool',
    long_description='Python RESTful API Testing & Microbenchmarking Tool '
                     '\n Documentation at https://github.com/svanoort/pyresttest',
    author='Abhilash Joseph C',
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
    license='Apache License, Version 2.0',
    install_requires=install_requires,
    tests_require=test_dependencies,
    test_suite="py3resttest.tests",
    entry_points={
        'console_scripts': ['resttest=py3resttest.resttest:command_line_run'],
    }

)
