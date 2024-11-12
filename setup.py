from setuptools import setup, find_packages

setup(
    name="darc-django",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "Django>=5",
    ],
    description="Allows atomate and customize a REST interface for Django models",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Saul Esteban López Bermúdez",
    author_email="sauleta.selb@gmail.com",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Framework :: Django",
        "License :: MIT License",
    ],
)
