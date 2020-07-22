import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="mash-poofjunior", # Replace with your own username
    version="0.0.1",
    author="Joshua Vasquez",
    author_email="joshua@doublejumpelectric.com",
    description="An inferrable line oriented command prompt interpreter",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/poofjunior/mash",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
