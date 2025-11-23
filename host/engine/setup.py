from setuptools import setup, Extension
import pybind11
import os

# Locate pybind11 include directory
include_dirs = [pybind11.get_include()]

# Define the extension module
ext_modules = [
    Extension(
        "groovebox_audio_cpp",
        ["cpp/audio_engine.cpp"],
        include_dirs=include_dirs,
        libraries=["portaudio"],  # Link against libportaudio
        language="c++",
        extra_compile_args=["-std=c++17", "-O3"],
    ),
]

setup(
    name="groovebox_audio_cpp",
    version="0.1.0",
    ext_modules=ext_modules,
)
