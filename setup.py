import os
from setuptools import setup

def _read(fn):
    path = os.path.join(os.path.dirname(__file__), fn)
    return open(path).read()

setup(
      name='vamtb',
      version='0.12',
      author_email='foo@bar.com',
      long_description=_read('README.rst'),
      test_suite='vamtb.test.testall.suite',
      packages=[
        'vamtb',
        'vamtb.config',
        'vamtb.db',
        'vamtb.file',
        'vamtb.graph',
        'vamtb.hub',
        'vamtb.log',
        'vamtb.meta',
        'vamtb.profile',
        'vamtb.utils',
        'vamtb.vamex',
        'vamtb.var',
        'vamtb.varfile',
      ],
      package_data={},
      install_requires=[
        "click", 
        "jinja2", 
        "Pillow", 
        "piexif",
        "tqdm",
        "pyyaml",
        "colorama",
        "requests",
        "pyrfc6266",
        "beautifulsoup4",
        "internetarchive"
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