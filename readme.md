# EBBS Python Builder

Do you hate having empty `__init__.py` files and other nonsense strewn about your project? This fixes that. Somehow.  
To build a python library or binary, go to the root of your project and run `ebbs -l py generated`.  
This will copy all `*.py` files out of `src` and compile them into a single `PROJECT_NAME.py` in a dependency-aware fashion.  
It will also copy all files and directories from `inc` and add them to the build folder.  
Then, it creates python project files, like `__main__.py` and `__init__.py`s.  
Lastly, it invokes python's build package and pip to build and install your code. This will fail if the necessary dependencies are not installed.

IMPORTANT: DO NOT USE THIS IN A `build` FOLDER!  
Building packages from a folder named "build" with `python -m build` (and setuptools?) will result in an empty package as all `*.py` files in that directory are ignored.
Someone please fix this...

Supported project types:
* bin
* lib

Prerequisites:
* `build` python package
* valid setup and pyproject.toml files  

See [how to package python projects](https://packaging.python.org/tutorials/packaging-projects/) for information on required files.  
NOTE: Setup files are not created for you, since there is some variability in what you might want.
