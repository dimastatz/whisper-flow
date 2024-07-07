from setuptools import setup
from whisperflow import __version__


setup(
    name='whisperflow',
    version=__version__,

    url='https://github.com/dimastatz/whisper-flow',
    author='Dima Statz',
    author_email='dima.statz@gmail.com',
    py_modules=['whisperflow'],
    install_requires=[
        "jiwer==3.0.4",
        "pytest==7.3.2",
        "black==23.3.0",
        "httpx==0.27.0",
        "pylint==2.17.4",
        "fastapi==0.108.0",
        "pytest-cov==4.1.0",
        "pytest-timeout==2.3.1",
        "pytest-asyncio==0.23.7",
        "websocket-client==1.8.0",
        "python-multipart==0.0.9",
        "openai-whisper==20231117",
        "pylint-fail-under==0.3.0",
        "uvicorn[standard]==0.30.1",
    ],
)
