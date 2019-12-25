import sys

# the local will take precedence
sys.path.insert(1, '..')

from subprocess import run
import docal
from docal import document
from os import path

tex = path.abspath('./test/t.tex')
d = document(tex, tex)

d.send(r'''
x = 5
# then
''')

d.write()

run(['do.bat', tex])
