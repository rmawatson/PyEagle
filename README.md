PyEagle
=======

Open up eagle_python_dispatcher.ulp in the ulp/ path and customise the variables at the top. For your system

Make sure you add the ulp path to eagle, and the script path for the menu "python_tools.scr"

looking at python_tools.scr will show you how you can go about launching a python script from Eagle

for example : 

"RUN eagle_python_dispatcher.ulp alignment_tool.py"

as long as the paths are setup, this should just work.

You can drag this python_tools.scr onto an open schematic and you will get a new menu with the applications I have created.

Currently there is a dxf importer, Outliner (browser), group manager and alignment tool. All of these rely on PyQt4, and in future, PySide.

Best place to start is with "test.py", get this working first.


API
===

Most of the stuff in eagle has been wrapped.

Eaglepy module has everything that is wrapped so far. 

Either look at this python script to get an idea of what you can do, or check out some of the examples.

I'll write a proper readme with examples when I have time.

Cheers
