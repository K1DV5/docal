import sys

sys.path.append('..')

import docal
from docal import document

tex = 'test/t.tex'
d = document(tex, tex)

d.send(r'''
#@ kg, #the answer
x = 5
y = 5*x
#@
v = 45
''')

d.write()


