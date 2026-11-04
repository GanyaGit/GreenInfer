from setuptools import setup, find_packages

setup(
    name="greeninfer",
    version="0.1.0",
    author="Gayani Upeksha",
    author_email="gayaniupeksha2906@gmail.com",
    description="CO₂ and water footprint estimator for AI inference queries",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    package_data={
        "greeninfer": ["data/release_generation_yearly_global.csv"],
    },
    install_requires=[
        "pandas",
        "pynvml",
    ],
    python_requires=">=3.10",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
