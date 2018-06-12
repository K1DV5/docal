# SciRep

SciRep is a scientific report document generation project that aims to be used mainly by students. While there are many tools for this job, from open source (mainly Jupyter) to commercial (Mathcad, Matlab's Live Script, etc.), as far as I know none can output __a document that can just be printed and submitted__ as a normal report to a school or college.

Jupyter requires the receiver to be acquainted with Python (or any of the language used). Same goes for Matlab. Mathcad comes pretty close but falls short when it comes to flexibility (mainly on the equations).

There is a python library that does this job: PyLaTeX. But it too didn't fit because the user has to do additional typing which is significantly more than the content, which creates the possibility of making the python source document difficult to read and maintain.

This library aims to combine the strengths of the above tools and make it easy to write reports, by doing the heavy lifting for the user and letting the user focus on the content.

## Features
* Automatic calculation and unit conversion and handling (idea from Mathcad)
* LaTeX (.tex) output that can be compiled to PDF or...
* Optional MS Word document output (via pandoc)
* Conversion of equations and expressions from python form to LaTeX
* Clear calculation procedure output

### Note:
The project is currently under development.