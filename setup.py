from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()

setup(name='souspi',
      version='0.1',
      description='Raspberry Pi based sous vide cooker',
      long_description=readme(),
      url='http://github.com/jrheling/souspi',
      author='Joshua Heling',
      author_email='jrh@netfluvia.org',
      license='Apache',
      packages=['souspi'],
      scripts=['souspi/bin/SousVideCLI', 'souspi/bin/SousVideControllerApp', 'souspi/bin/SousVideLCDUI', 
               'souspi/bin/SousVideWebUI', 'souspi/bin/temptrackd'],
      include_package_data=True,    ## causes non-python files in the MANIFEST to be included at install time
      install_requires=[
                'pid_controller',  
                'RPi.GPIO',
                'w1thermsensor'
            ],
      zip_safe=False)