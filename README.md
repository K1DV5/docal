# doCal

[![CircleCI](https://circleci.com/gh/K1DV5/doCal.svg?style=svg)](https://circleci.com/gh/K1DV5/doCal)

doCal is a tool that can be used to send calculations that are written in
python to Word or LaTeX documents. It evaluates equations in a separate python
script from the document and replaces hashtags in the document that indicate
where the calculations should be with the results of the evaluation. It comes
with a powerful python expression to LaTeX converter built-in, so it converts
the calculations and their results to their appropriate LaTeX forms before
sending them, which makes it ideal to make academic and scientific reports.

## Installation

### Requirements

**Quick note**: in this document, shell means `cmd` (command prompt) or
`powershell` for Windows users and `sh` or `bash` for Linux and MacOS users.

A basic understanding of Python in general is necessary to have a smooth
experience here.  If you want to work with a little more advanvced stuff, like
arrays and matrices, more knowledge about python is necessary.

It must be obvious by now but you should have Python installed on your system.
You can check that by opening your shell (see above) and typing the command
`python` and hitting Enter. If it writes the version number and other info
about your python installation, you already have it installed. If the version
number starts with 2, you should probably install python 3 (the latest). If you
have python 3 or above, you\'re good to go. If either you don\'t have Python 3
or you don\'t have Python at all, you should go to [Python\'s
homepage](https://www.python.org) and install it, making sure to check the box
\"add python to path\" during installation.

If you want to work with word documents, you should have
[Pandoc](https://pandoc.org) installed on your system (and in your path).
Because docal internally only works with tex files and when a word file is
given, it internally converts it to tex, modifies it and converts it back to
word, using pandoc.

### Install

To install this package, (after making sure that you have a working internet
connection) type the following command and hit Enter.

```shell
pip install docal
```
Or if you have the source
```shell
pip install .
```

## Usage

### Typical workflow

* The user writes the static parts of the document as usual (Word or Latex) but
  leaving sort of unique hashtags (\#tagname) for the calculation parts (double
  hash signs for Wrod).
* The calculations are written on a separate text file with any text editor
  (Notepad included) and saved next to the document file. For the syntax of the
  calculation file, see below. But it\'s just a python script with comments.
* The tool is invoked with the following command:
  ```shell  docal
  [calculation-file] [input-file] [output-file]
  ```
  so for example,
  ```shell
  docal calcs.py document.tex document-out.tex
  ```
  will be valid.  
* Then voila! what is needed is done. The output file can be used normally.

### Syntax

The syntax is simple. Just write the equations one line at a time. What you
write in the syntax is a valid python file, (it is just a script with a lot of
assignments and comments).  The following should be a good starting point.

```python
## foo.py
## necessary for scientific functions
from math import *

#foo

# The first side of the first triangle is
x_1 = 5 #m
# and the second,
y_1 = 6 #m
# Therefore the length of the hypotenuse will be,
z_1 = sqrt(x_1**2 + y_1**2) #m

#bar

# Now the second triangle has sides that have lengths of
x_2 = 3
y_2 = 4
# and therefore has a hypotenuse of
z_2 = sqrt(x_2**2 + y_2**2) #m,13

# Then, we can say that the hypotenuse of the first triangle which is #z_1 long
# is longer than that of the second which is #z_2 long.
```

Now, looking at the above example line by line,

* The first part (starting with double hash signs) serves as a real comment
  that does not do anything in python or in docal.
* The second is a python import statement, to make things such as sqrt, sin, pi
  available.
* The line that only contains a hashtag is treated as a message that what
  follows, until the next tag or the end should be sent to the document and at
  this particular place. That\'s why tags are necessary in the document. It
  looks for those tags in the document and replaces them with the modified
  versions of the calculations and paragraphs below it.
* The lines starting with single hash characters are taken as parts of running
  text (paragraphs).
* The lines with equal signs are treated as calculations. when they end with
  comments, the part after the hash character is treated as options for that
  calculation. (in the first three cases, we want to display the unit m
  displayed besides the variables that we assign to. And in the last equation,
  the additional 13 is taken as thouth the user wants only the first and the
  last steps displayed.)
* The last two comments (treated as paragraphs), have tags in them, which are
  interpreted as variable references and thus are substituted by formatted
  values of those variables.

The output of the above example, inserted into a plain word file, containing
only two tags, \#\#foo and \#\#bar will look like the following figure.

![Word document output](https://github.com/K1DV5/doCal/blob/master/common/images/word-out.jpg "Word document output")

## Known Issues

* You cannot use python statements that need indenting. This is because docal
  reads the script line by line and uses exec to make the necessary
  assignments, and since you can't continue an already indented code with exec,
  that will result in an error. If you have an idea to overcome this problem,
  feel free to contact me.

## TODO

### Long term

* Add unit awareness. Currently the units don't take part in the number
  manipulations. They just appear besides the values when a variable is
  referenced. This means the numbers will be the same with or without the
  units.
