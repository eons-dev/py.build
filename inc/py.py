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

        self.validPyExtensions = [
            ".py"
        ]

    def PreCall(self, **kwargs):
        super().PreCall(**kwargs)
        self.outFile = None
        self.decomposedFiles = []
        self.imports = [] #all import statements
        self.consolidatedContents = [] #all file contents. FIXME: This doesn't scale but need to write imports first.

    #Required Builder method. See that class for details.
    def Build(self):
        self.buildPath = os.path.abspath(os.path.join(self.buildPath, self.projectName))
        mkpath(self.buildPath)
        os.chdir(self.buildPath)
        logging.info(f"Using build path {self.buildPath}")
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
        # If we can build our prepared project, let's do it!
        if (os.path.isfile(os.path.join(self.rootPath, "setup.cfg"))):
            logging.info(f"Begining python build process")
            os.chdir(self.rootPath)
            self.BuildPackage()
            self.InstallPackage()
        logging.info("Complete!")

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
        initFile = self.CreateFile(os.path.join(self.buildPath, "__init__.py"))
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
            destPath = os.path.join(self.buildPath, thing)
            if os.path.isfile(thingPath):
                copy_file(thingPath, destPath)
            elif os.path.isdir(thingPath):
                copy_tree(thingPath, destPath)
        for root, dirs, files in os.walk(self.buildPath):
            for d in dirs:
                self.MakeEmptyInitFile(os.path.join(root,d))

    #Builds the thing.
    def BuildPackage(self):
        self.RunCommand("python -m build")

    #Installs the built package!
    def InstallPackage(self):
        self.RunCommand("python -m pip install . -U")