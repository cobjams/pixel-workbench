from setuptools import setup

setup(
    name="pixel-workbench",
    version="0.2.0",
    description="Semantic Reasoning and Deterministic Construction Engine for Pixel Art",
    package_dir={"pixel_workbench": "."},
    packages=[
        "pixel_workbench",
        "pixel_workbench.analysis",
        "pixel_workbench.analysis.adapters",
        "pixel_workbench.analysis.repair",
        "pixel_workbench.core",
        "pixel_workbench.gui",
        "pixel_workbench.scripting",
        "pixel_workbench.tools",
    ],
    install_requires=["Pillow>=7.0.0"],
    entry_points={
        "console_scripts": [
            "pixel-workbench=pixel_workbench.__main__:main",
        ],
    },
)
