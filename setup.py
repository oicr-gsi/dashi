from setuptools import setup, find_packages

setup(
   name='dashi',
   version='0.1.0',
   description='Visualizer for GSI QC data',
   author='Savo Lazic',
   author_email='savo.lazic@oicr.on.ca',
   python_requires='>=3.6.0',
   packages=find_packages(),
   install_requires=[
      'dash==1.2.0',
      'plotly==4.0.0',
      'scipy==1.2.0',
      'pandas==0.23.4',
      'tables==3.5.1',
      'numpy==1.15.4',
      'sd-material-ui==3.1.2',
      'gsiqcetl @ git+https://bitbucket.oicr.on.ca/scm/gsi/gsi-qc-etl.git@master'
   ],
)