import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="OViewPy",
    version="1.2.0",
    author="louis.li",
    author_email="louis.li@pilotgaea.com.tw",
    description="PilotGaea O'View Map Server API for Python",
    packages=setuptools.find_packages(),
    url="https://github.com/PilotGaea/OViewPy",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Topic :: Scientific/Engineering :: GIS"
    ],
    install_requires=[
        "requests",
        "numpy ",
        "opencv-python",
        "progress",
        "shapely",
        "PyShp",
        "rasterio",
        "matplotlib",
        "sridentify",
        "geojsoncontour"
    ],
    python_requires=">=3.6",
)