from pathlib import Path
from setuptools import setup
from whisperflow import __version__
from pkg_resources import parse_requirements


this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name='whisperflow',
    version=__version__,
    url='https://github.com/dimastatz/whisper-flow',
    author='Dima Statz',
    author_email='dima.statz@gmail.com',
    py_modules=['whisperflow'],
    python_requires=">=3.8",
    install_requires=[
        str(r)
        for r in parse_requirements(
            Path(__file__).with_name("requirements.txt").open()
        )
    ],
    description='WhisperFlow: Real-Time Transcription Powered by OpenAI Whisper',
    long_description = long_description,
    long_description_content_type='text/markdown',
)
