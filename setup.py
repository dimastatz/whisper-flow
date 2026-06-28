from pathlib import Path
from setuptools import setup, find_packages
from whisperflow import __version__


this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")
requirements = (
    (this_directory / "requirements.txt").read_text(encoding="utf-8").splitlines()
)
install_requires = [
    line.strip()
    for line in requirements
    if line.strip() and not line.startswith("#")
]


setup(
    name="whisperflow",
    version=__version__,
    url="https://github.com/dimastatz/whisper-flow",
    author="Dima Statz",
    author_email="dima.statz@gmail.com",
    license="MIT",
    packages=find_packages(exclude=("tests", "tests.*")),
    python_requires=">=3.8",
    install_requires=install_requires,
    description="WhisperFlow: Real-Time Transcription Powered by OpenAI Whisper",
    long_description=long_description,
    long_description_content_type="text/markdown",
    include_package_data=True,
    package_data={"whisperflow": ["models/*.pt"]},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
