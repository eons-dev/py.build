# EBBS Python Builder

Do you hate having empty `__init__.py` files and other nonsense strewn about your project? Do you hate having to manually update the version in your setup.cfg file before publishing a new release? Do you wish requirements.txt could be auto-calculated from your `import` statements?
This builder does all that and more!

This will copy all `*.py` files out of `src` and compile them into a single `PROJECT_NAME.py` in a dependency-aware fashion.  
It will also copy all files and directories from `inc` and add them to the build folder. 
Then, it creates python project files, like `__main__.py` and `__init__.py`s.  
After your code has been digested and is ready for packaging, this will compute the necessary dependencies for you project and create all the files required to build, package, & install your code.
Lastly, it builds, tests, packages, installs, and publishes your code, neglecting the actions it can't perform (e.g. if there are no tests, nothing is tested; if there are no pypi credentials found, nothing is published; etc.).

IMPORTANT: DO NOT USE THIS IN A `build` FOLDER!  
Building packages from a folder named "build" with `python -m build` (and setuptools?) will result in an empty package as all `*.py` files in that directory are ignored.
Someone please fix this...

Supported project types:
* bin
* lib


## build.json
The easiest way to use this builder is with a build.json file in the root of your project directory (or in a build folder if you adjust the copy file paths).
That file should look something like:
```json
{
  "clear_build_path" : true,
  "ebbs_next": [
    {
      "build" : "py",
      "build_in" : "generated",
      "copy" : [
        {"../src/" : "src/"},
        {"../inc/" : "inc/"},
        {"../test/" : "test/"}
      ],
      "config" : {
        "author_name" : "eons",
        "author_email" : "support@eons.llc",
        "desrciption" : "eons Basic Build System",
        "package_url" : "https://github.com/eons-dev",
        "license" : "MIT License",
        "python_min" : "3.7",
        "classifiers" : [
          "Development Status :: 4 - Beta"
        ]
      }
    }
  ]
}
```
You can then invoke ebbs with a command like `ebbs . --version "0.0.0"`. Alternatively, you can place that code in your github workflow file (see [the ebbs publish workflow](https://github.com/eons-dev/bin_ebbs/blob/main/.github/workflows/python-publish.yml) for an example).

The full list of options is for this Builder are:
```python
self.optionalKWArgs["version"] = "v0.0.0"
self.optionalKWArgs["author_name"] = "eons"
self.optionalKWArgs["author_email"] = "support@eons.llc"
self.optionalKWArgs["description"] = ""
self.optionalKWArgs["package_url"] = None
self.optionalKWArgs["classifiers"] = []
self.optionalKWArgs["license"] = "MIT License"
self.optionalKWArgs["python_min"] = "3.7"
self.optionalKWArgs["pypi_username"] = None
self.optionalKWArgs["pypi_password"] = None
```

**ALTERNATIVES:** as with all ebbs 2 projects, the above variables can be supplied via build.json, environment variables, and/or command line arguments. You decide what fits your workflow the best!
