# setup.py
from setuptools import setup, find_packages

setup(
    name="greeninfer",
    version="0.1.0",
    author="Gayani Upeksha",
    author_email="gayaniupeksha2906@gmail.com",
    description="CO2 and water footprint estimator for AI inference queries",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/GanyaGit/GreenInfer",
    packages=find_packages(),
    package_data={
        "greeninfer": ["data/electricity-generation-by-source.csv"],
    },
    install_requires=[
        "pandas>=1.5.0",
        "pynvml>=11.0.0",
    ],
    python_requires=">=3.10",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Atmospheric Science",
    ],
    keywords="AI inference carbon footprint CO2 water sustainability green computing",
)