import setuptools

with open("README.md", "r", newline="", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="inpromptu",
    version="0.1.1",
    author="Joshua Vasquez",
    author_email="joshua@doublejumpelectric.com",
    description="An inferrable line oriented command prompt interpreter",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/poofjunior/inpromptu",
    license="MIT",
    keywords= ['interpreter', 'inspection', 'prompt', 'repl'],
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires='>=3.6',
    install_requires=['prompt_toolkit>=3.0.28']
)
