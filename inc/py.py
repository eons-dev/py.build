import os
import logging
import shutil
from distutils.file_util import copy_file
from distutils.dir_util import copy_tree, mkpath
from ebbs import Builder

#Class name is what is used at cli, so we defy convention here in favor of ease-of-use.
class py(Builder):
    def __init__(self, name="Python Builder"):
        super().__init__(name)
        
        self.supportedProjectTypes.append("lib")
        self.supportedProjectTypes.append("bin")

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
        
        self.validPyExtensions = [
            ".py"
        ]

        self.imports = []
        self.usedModules = []
        self.requiredModules = []

        self.PopulateBuiltInModules() #see end of file.

    def PreCall(self, **kwargs):
        super().PreCall(**kwargs)
        self.outFile = None
        self.decomposedFiles = []
        self.imports = [] #all import statements
        self.consolidatedContents = [] #all file contents. FIXME: This doesn't scale but need to write imports first.

    #Required Builder method. See that class for details.
    def Build(self):
        self.packagePath = os.path.abspath(os.path.join(self.buildPath, self.projectName))
        mkpath(self.packagePath)
        os.chdir(self.packagePath)
        logging.info(f"Using package path {self.packagePath}")
        self.outFile = self.CreateFile(f"{self.projectName}.py")
        logging.info(f"Consolidating python files from {self.srcPath}")
        self.DecomposePyFiles(self.srcPath)
        self.WriteImports()
        self.outFile.write(f'''
######## START CONTENT ########
''')
        self.WriteContents()
        self.outFile.close()
        if (self.projectType == "lib"):
            self.MakeLib()
        elif (self.projectType == "bin"):
            self.MakeBin()
        self.CopyIncludes()
        self.PopulateRequiredModules()
        self.WriteRequirements()
        self.WritePyproject()
        self.WriteSetup()
        # If we can build our prepared project, let's do it!
        if (os.path.isfile(os.path.join(self.rootPath, "setup.cfg"))):
            logging.info(f"Begining python build process")
            os.chdir(self.rootPath)
            self.InstallDependencies()
            self.BuildPackage()
            if (self.testPath is not None):
                self.RunCommand("pytest test/*")
            self.InstallPackage()
            if(self.pypi_username is not None and self.pypi_password is not None):
                self.RunCommand(f"twine upload -u {self.pypi_username} -p {self.pypi_password} dist/*")

    #Adds an import line to *this.
    #Prevents duplicates.
    def AddImport(self, line):
        if (line in self.imports):
            return
        self.imports.append(line)

    #Decompose a python file into imports and content.
    #Both are currently stored in member variables.
    #Recursive to account for dependencies.
    #Does not operate on the same file more than once.
    def Decompose(self, pyFile):
        absPyFilePath = os.path.abspath(pyFile)
        if (absPyFilePath in self.decomposedFiles):
            logging.debug(f"Already decomposed {absPyFilePath}")
            return
        logging.debug(f"Starting to decompose {absPyFilePath}")
        py = open(pyFile, "r")
        for line in py:
            if (line.startswith("from") or line.startswith("import")): #handle import parsing
                spaced = line.split(' ')
                if (spaced[1].startswith(".")): #Decompose dependency first.
                    #TODO: Isn't "...", etc. a thing with relative imports?
                    dependency = spaced[1].replace(".", "/") + ".py"
                    if (dependency.startswith("/") and not dependency.startswith("//")):
                        dependency = dependency[1:]
                    dependency = dependency.replace("//", "../")
                    logging.debug(f"Found dependency {dependency}")
                    self.Decompose(os.path.join(os.path.dirname(pyFile), dependency))
                    continue
                multiports = line.split(",")
                if (len(multiports) > 1): #break out multiple imports for duplicate checking
                    # logging.debug(f"Breaking up multiple imports from {line}")
                    begin = " ".join(multiports[0].split(" ")[:-1])
                    # logging.debug(f"Beginning = {begin}")
                    #TODO: Do we need to support "\r\n" for windows?
                    #TODO: What's up with all this [:-1]+"\n" nonsense? Why does that invisible line ending change the uniqueness of the string (i.e. what is the line ending if not "\n")?
                    for i, imp in enumerate(multiports):
                        if (i == 0):
                            self.AddImport(imp + "\n")
                            continue
                        elif (i == len(multiports)-1):
                            self.AddImport(begin + imp[:-1] + "\n")
                        else:
                            self.AddImport(begin + imp + "\n")
                        # logging.debug(f"Got new import: {begin + imp}")
                else:
                    self.AddImport(line[:-1] + "\n")

            #TODO: Strip comments and newlines for smaller file footprint

            else: #content line
                #FIXME: See above FIXME. This should be self.outFile.write(line) but imports need to be written first.
                #FIXME: Need to enforce each line ending with a newline without things becoming weird.
                self.consolidatedContents.append(line)
        self.consolidatedContents.append("\n")
        self.decomposedFiles.append(absPyFilePath)
        logging.debug(f"Finished decomposing {absPyFilePath}")

    #Walk a directory and Decompose all python files in it.
    def DecomposePyFiles(self, directory):
        for root, dirs, files in os.walk(directory):
            for f in files:
                name, ext = os.path.splitext(f)
                if (ext in self.validPyExtensions):
                    # logging.info(f"    {os.path.join(root, f)}")
                    self.Decompose(os.path.join(root,f))

    #Dump contents of import member buffer to disk.
    def WriteImports(self):
        for imp in self.imports:
            self.outFile.write(imp)

    #Dump contents of content member buffer to disk.
    def WriteContents(self):
        for line in self.consolidatedContents:
            self.outFile.write(line)

    #Makes an empty init file
    def MakeEmptyInitFile(self, path):
        initFile = self.CreateFile(os.path.join(path, "__init__.py"))
        initFile.write(f'''
''')
        initFile.close()

    #Makes package a library
    def MakeLib(self):
        initFile = self.CreateFile(os.path.join(self.packagePath, "__init__.py"))
        initFile.write(f'''from .{self.projectName} import *
''')
        initFile.close()

    #Makes package executable
    def MakeBin(self):
        logging.info(f"Adding binary specific code.")
        initFile = self.CreateFile("__init__.py")
        #TODO: Support projects that aren't capitalized acronyms. For now, though, this is easy.
        initFile.write(f'''#!/usr/bin/env python3
from .{self.projectName} import *
{self.projectName} = {self.projectName.upper()}()
''')
        initFile.close()

        mainFile = self.CreateFile("__main__.py")
        mainFile.write(f'''from . import {self.projectName}
if __name__ == '__main__':
    {self.projectName}()
''')
        mainFile.close()

    #Copy all files from the project include directory into our build folder.
    def CopyIncludes(self):
        if (self.incPath):
            logging.info("Copying includes")
        else:
            return

        #This nonsense is required because we need `cp incPath/* buildpath/` behavior instead of `cp incPath buildpath/`
        #TODO: is there a better way?
        for thing in os.listdir(self.incPath):
            thingPath = os.path.join(self.incPath, thing)
            destPath = os.path.join(self.packagePath, thing)
            if os.path.isfile(thingPath):
                copy_file(thingPath, destPath)
            elif os.path.isdir(thingPath):
                copy_tree(thingPath, destPath)
        for root, dirs, files in os.walk(self.packagePath):
            for d in dirs:
                self.MakeEmptyInitFile(os.path.join(root,d))

    #Create requirements.txt
    def WriteRequirements(self):
        requirementsFileName = os.path.join(self.rootPath, "requirements.txt")
        logging.debug(f"Writing {requirementsFileName}")
        requirementsFile = self.CreateFile(requirementsFileName)
        requirementsFile.write(f'''pip
build
wheel
setuptools
twine
pytest
''')
        #TODO: determine required package versions.
        for req in self.requiredModules:
            requirementsFile.write(f"{req}\n")
        requirementsFile.close()

    #Create pyproject.toml
    def WritePyproject(self):
        pyprojectFileName = os.path.join(self.rootPath, "pyproject.toml")
        logging.debug(f"Writing {pyprojectFileName}")
        pyprojectFile = self.CreateFile(pyprojectFileName)
        pyprojectFile.write(f'''[build-system]
requires = [
    "setuptools>=42",
    "wheel"
]
build-backend = "setuptools.build_meta"
''')
        pyprojectFile.close()

    #Create setup.cfg
    def WriteSetup(self):
        setupFileName = os.path.join(self.rootPath,"setup.cfg")
        logging.debug(f"Writing {setupFileName}")
        setupFile = self.CreateFile(setupFileName)
        setupFile.write(f'''
[metadata]
name = {self.projectName}
version = {self.version}
author = {self.author_name}
author_email = {self.author_email}
description = {self.description}
license_files = LICENSE.txt
long_description = file: README.md
long_description_content_type = text/markdown
''')
        if (self.package_url is not None):
            setupFile.write(f'''
url = {self.package_url}
project_urls =
    Bug Tracker = {self.package_url}/issues
''')
        setupFile.write(f'''
classifiers =
    Programming Language :: Python :: 3
    License :: OSI Approved :: {self.license}
    Operating System :: OS Independent
''')
        for cls in self.classifiers:
            setupFile.write(f"    {cls}\n")

        setupFile.write(f'''
[options]
package_dir =
    = {os.path.basename(self.buildPath)}
packages = find:
python_requires = >={self.python_min}
install_requires = 
''')
        for req in self.requiredModules:
            setupFile.write(f"    {req}\n")

        setupFile.write(f'''
[options.packages.find]
where = {os.path.basename(self.buildPath)}
''')
        if (self.projectType in ["bin"]):
            setupFile.write(f'''
[options.entry_points]
console_scripts =
    {self.projectName} = {self.projectName}:{self.projectName}
''')
        setupFile.close()

    #Install any necessary packages.
    def InstallDependencies(self):
        self.RunCommand(f"python3 -m pip install -U -r {self.rootPath}/requirements.txt")

    #Builds the thing.
    def BuildPackage(self):
        self.RunCommand("python3 -m build")

    #Installs the built package!
    def InstallPackage(self):
        self.RunCommand("python3 -m pip install . -U")

    #Figure out which modules have been included and aren't built in.
    def PopulateRequiredModules(self):
        self.usedModules = list(set([i.split(' ')[1].split('.')[0].rstrip() for i in self.imports]))
        logging.debug(f"Modules used: {self.usedModules}")
        self.requiredModules = [m for m in self.usedModules if not m in self.pythonBuiltInModules]
        logging.debug(f"Modules not built-in: {self.requiredModules}")

    #Hard coded list of built in modules.
    def PopulateBuiltInModules(self):
        self.pythonBuiltInModules = [
            "__future__",
            "_abc",
            "_ast",
            "_asyncio",
            "_bisect",
            "_blake2",
            "_bootlocale",
            "_bz2",
            "_codecs",
            "_codecs_cn",
            "_codecs_hk",
            "_codecs_iso2022",
            "_codecs_jp",
            "_codecs_kr",
            "_codecs_tw",
            "_collections",
            "_collections_abc",
            "_compat_pickle",
            "_compression",
            "_contextvars",
            "_csv",
            "_ctypes",
            "_ctypes_test",
            "_datetime",
            "_decimal",
            "_distutils_findvs",
            "_dummy_thread",
            "_elementtree",
            "_functools",
            "_hashlib",
            "_heapq",
            "_imp",
            "_io",
            "_json",
            "_locale",
            "_lsprof",
            "_lzma",
            "_markupbase",
            "_md5",
            "_msi",
            "_multibytecodec",
            "_multiprocessing",
            "_opcode",
            "_operator",
            "_osx_support",
            "_overlapped",
            "_pickle",
            "_py_abc",
            "_pydecimal",
            "_pyio",
            "_queue",
            "_random",
            "_sha1",
            "_sha256",
            "_sha3",
            "_sha512",
            "_signal",
            "_sitebuiltins",
            "_socket",
            "_sqlite3",
            "_sre",
            "_ssl",
            "_stat",
            "_string",
            "_strptime",
            "_struct",
            "_symtable",
            "_testbuffer",
            "_testcapi",
            "_testconsole",
            "_testimportmultiple",
            "_testmultiphase",
            "_thread",
            "_threading_local",
            "_tkinter",
            "_tracemalloc",
            "_warnings",
            "_weakref",
            "_weakrefset",
            "_winapi",
            "abc",
            "aifc",
            "antigravity",
            "argparse",
            "array",
            "ast",
            "asynchat",
            "asyncio",
            "asyncore",
            "atexit",
            "audioop",
            "autoreload",
            "backcall",
            "base64",
            "bdb",
            "binascii",
            "binhex",
            "bisect",
            "builtins",
            "bz2",
            "calendar",
            "cgi",
            "cgitb",
            "chunk",
            "cmath",
            "cmd",
            "code",
            "codecs",
            "codeop",
            "collections",
            "colorama",
            "colorsys",
            "compileall",
            "concurrent",
            "configparser",
            "contextlib",
            "contextvars",
            "copy",
            "copyreg",
            "cProfile",
            "crypt",
            "csv",
            "ctypes",
            "curses",
            "cythonmagic",
            "dataclasses",
            "datetime",
            "dbm",
            "decimal",
            "decorator",
            "difflib",
            "dis",
            "distutils",
            "doctest",
            "dummy_threading",
            "easy_install",
            "email",
            "encodings",
            "ensurepip",
            "enum",
            "errno",
            "faulthandler",
            "filecmp",
            "fileinput",
            "fnmatch",
            "formatter",
            "fractions",
            "ftplib",
            "functools",
            "gc",
            "genericpath",
            "getopt",
            "getpass",
            "gettext",
            "glob",
            "gzip",
            "hashlib",
            "heapq",
            "hmac",
            "html",
            "http",
            "idlelib",
            "imaplib",
            "imghdr",
            "imp",
            "importlib",
            "ind",
            "inspect",
            "io",
            "ipaddress",
            "IPython",
            "ipython_genutils",
            "itertools",
            "jedi",
            "json",
            "keyword",
            "lib2to3",
            "linecache",
            "locale",
            "logging",
            "lzma",
            "macpath",
            "mailbox",
            "mailcap",
            "marshal",
            "math",
            "mimetypes",
            "mmap",
            "modulefinder",
            "msilib",
            "msvcrt",
            "multiprocessing",
            "netrc",
            "nntplib",
            "nt",
            "ntpath",
            "nturl2path",
            "numbers",
            "opcode",
            "operator",
            "optparse",
            "os",
            "parser",
            "parso",
            "pathlib",
            "pdb",
            "pickle",
            "pickleshare",
            "pickletools",
            "pip",
            "pipes",
            "pkg_resources",
            "pkgutil",
            "platform",
            "plistlib",
            "poplib",
            "posixpath",
            "pprint",
            "profile",
            "prompt_toolkit",
            "pstats",
            "pty",
            "py_compile",
            "pyclbr",
            "pydoc",
            "pydoc_data",
            "pyexpat",
            "pygments",
            "queue",
            "quopri",
            "random",
            "re",
            "reprlib",
            "rlcompleter",
            "rmagic",
            "runpy",
            "sched",
            "secrets",
            "select",
            "selectors",
            "setuptools",
            "shelve",
            "shlex",
            "shutil",
            "signal",
            "simplegeneric",
            "site",
            "six",
            "smtpd",
            "smtplib",
            "sndhdr",
            "socket",
            "socketserver",
            "sqlite3",
            "sre_compile",
            "sre_constants",
            "sre_parse",
            "ssl",
            "stat",
            "statistics",
            "storemagic",
            "string",
            "stringprep",
            "struct",
            "subprocess",
            "sunau",
            "symbol",
            "sympyprinting",
            "symtable",
            "sys",
            "sysconfig",
            "tabnanny",
            "tarfile",
            "telnetlib",
            "tempfile",
            "test",
            "tests",
            "textwrap",
            "this",
            "threading",
            "time",
            "timeit",
            "tkinter",
            "token",
            "tokenize",
            "trace",
            "traceback",
            "tracemalloc",
            "traitlets",
            "tty",
            "turtle",
            "turtledemo",
            "types",
            "typing",
            "unicodedata",
            "unittest",
            "urllib",
            "uu",
            "uuid",
            "venv",
            "warnings",
            "wave",
            "wcwidth",
            "weakref",
            "webbrowser",
            "winreg",
            "winsound",
            "wsgiref",
            "xdrlib",
            "xml",
            "xmlrpc",
            "xxsubtype",
            "zipapp",
            "zipfile",
            "zipimport",
            "zlib"
        ]