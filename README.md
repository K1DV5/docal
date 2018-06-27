# ScpyCalc

ScpyCalc is a scientific report document calculation back-end that aims to reduce the routine code used inside Python chunks in Pweave and/or PythonTEX documents. While embeding python code inside a document is a big advantage, it should not be the end. It is still required to format Python calculations output and equations to LaTeX form. Thus the user still has to write significantly more code to make the results flow with the surrounding document.

This library aims to use the above tools as infrustructure and make it easy to write reports, by doing the heavy lifting for the user and letting the user focus on the content (a LaTeX advantage).

## Features
* Automatic calculation and unit conversion and handling (idea from Mathcad, using Sympy units)
* Automatic formatting of equations, calculations and results into LaTeX form (using Sympy)
* LaTeX (.tex) file output that can be converted to other formats via pandoc (including MS Word .docx)
* Clear LaTeX formatted calculation procedure output

###An Example:
Inside a Pweave source document the user (having imported necessary modules and defined variables) writes
```latex
...
The area moment of inertia is:

<%aserar('I_R = (b*(h**3))/12 - ((b-2*t)*(h-2*t)**3)/12')%>

The center of gravity is
...
```
Now when the file is weaved into a .tex file:
```latex
...
The area moment of inertia is:

\begin{align}
\begin{split}
I_{R}	&= \frac{b}{12} \cdot h^{3} - \frac{1}{12} \cdot \left(b - 2 \cdot t\right) \cdot \left(h - 2 \cdot t\right)^{3}\\
		&= \frac{5\,\mathrm{cm}}{12} \times \left(11\,\mathrm{cm}\right)^{3} - \frac{1}{12} \times \left(5\,\mathrm{cm} - 2 \times 1\,\mathrm{mm}\right) \times \left(11\,\mathrm{cm} - 2 \times 1\,\mathrm{mm}\right)^{3}\\
		&= 5.07(10^{-07})\,\mathrm{m^{4}}\\
\end{split}
\end{align}

The center of gravity is
...
```
which, when compiled to pdf will look like
![PDF preview](https://raw.githubusercontent.com/K1DV5/ScpyCalc/tree/master/examples/figures/pdfpre.PNG "PDF preview")

### Note:
The project is currently under development and since I am not experienced, any suggestion or contribution is very welcome.
