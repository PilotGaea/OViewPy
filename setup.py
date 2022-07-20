import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pgpy",
    version="1.0",
    author="louis.li",
    author_email="louis.li@pilotgaea.com.tw",
    description="PilotGaea O'View Map Server API for Python",
    packages=setuptools.find_packages(),
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Independent",
    ],
    install_requires=[
        "requests",
        "numpy ",
        "opencv-python",
        "progress",
        "shapely",
        "PyShp"
    ],
    python_requires=">=3.6",
)