from setuptools import setup

version = "0.1.0"

setup(name="jicgo",
      packages=["jicgo"],
      version=version,
      description="Automation assistant",
      author='Matthew Hartley',
      author_email="matthew.hartley@jic.ac.uk",
      install_requires=[
          "pyyaml",
      ],
      entry_points={
          'console_scripts': ['jicgo=jicgo.cli:cli']
      },
      license="MIT")
