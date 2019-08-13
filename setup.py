from setuptools import setup, find_packages

setup(
   name='dashi',
<<<<<<< HEAD
<<<<<<< HEAD
   version='0.1.0',
=======
   version='0.0.1',
>>>>>>> Created setup.py for easy and consistent installs
=======
   version='0.1.0',
>>>>>>> Added `setup.py` and CHANGELOG
   description='Visualizer for GSI QC data',
   author='Savo Lazic',
   author_email='savo.lazic@oicr.on.ca',
   python_requires='>=3.6.0',
   packages=find_packages(),
   install_requires=[
      'dash==1.0.2',
      'plotly==4.0.0',
      'scipy==1.2.0',
      'pandas==0.23.4',
      'tables==3.5.1',
      'numpy==1.15.4',
<<<<<<< HEAD
<<<<<<< HEAD
      'sd-material-ui==3.1.2',
=======
>>>>>>> Created setup.py for easy and consistent installs
=======
      'sd-material-ui==3.1.2',
>>>>>>> Added Material UI as a dependency for the updated RNASeQC layout
      'gsiqcetl @ git+https://bitbucket.oicr.on.ca/scm/gsi/gsi-qc-etl.git@master'
   ],
)