import os
from setuptools import setup, find_packages

def _read(fn):
    path = os.path.join(os.path.dirname(__file__), fn)
    return open(path).read()

setup(
      name='vamtb',
      version='0.8',
      author_email='foo@bar.com',
      long_description=_read('README.rst'),
      packages=[
        'vamtb',
        'vamtb.vamdirs',
        'vamtb.varfile',
        'vamtb.vamex'
      ],
      package_data={},
      install_requires=[
        "click", 
        "jinja2", 
        "Pillow", 
        "piexif",
      ],
      extras_require={
        'test': [
        ],
      },   
      entry_points={
        'console_scripts': [
          'vamtb = vamtb.vamtb:cli'
        ]
      }
)