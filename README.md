# ScpyCalc

ScpyCalc is a scientific report document calculation back-end that aims to reduce the routine code used inside Python chunks in Pweave and/or PythonTEX documents. While embeding python code inside a document is a big advantage, it should not be the end. It is still required to format Python calculations output and equations to LaTeX form. Thus the user still has to write significantly more code to make the results flow with the surrounding document.

This library aims to use the above tools as infrustructure and make it easy to write reports, by doing the heavy lifting for the user and letting the user focus on the content (a LaTeX advantage).

## Features
* Automatic calculation and unit conversion and handling (idea from Mathcad, using Sympy units)
* Automatic formatting of equations, calculations and results into LaTeX form (using Sympy)
* LaTeX (.tex) file output that can be converted to other formats via pandoc (including MS Word .docx)
* Clear LaTeX formatted calculation procedure output

### Note:
The project is currently under development and since I am not experienced, any suggestion or contribution is very welcome.
