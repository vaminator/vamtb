import os
from setuptools import setup, find_packages

def _read(fn):
    path = os.path.join(os.path.dirname(__file__), fn)
    return open(path).read()

setup(
      name='vamtb',
      version='0.11',
      author_email='foo@bar.com',
      long_description=_read('README.rst'),
      test_suite='vamtb.test.testall.suite',
      packages=[
        'vamtb',
        'vamtb.vamdirs',
        'vamtb.varfile',
        'vamtb.graph',
        'vamtb.utils',
        'vamtb.file',
        'vamtb.thumb',
        'vamtb.vamex',
        'vamtb.test',
        'vamtb.db',
      ],
      package_data={},
      install_requires=[
        "click", 
        "jinja2", 
        "Pillow", 
        "piexif",
        "tqdm",
        "colorama"
      ],
      extras_require={
         'test': [
            'pytest',
        ],     
      },   
      entry_points={
        'console_scripts': [
          'vamtb = vamtb.vamtb:cli'
        ]
      }
)