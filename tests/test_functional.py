# -{pytest %f --capture=no}
import sys
from subprocess import run

# the local will take precedence
sys.path.insert(1, '..')
from docal import document
from docal.handlers.latex import handler as handler_t
from docal.handlers.word import handler as handler_w
from docal.parsers.excel import parse as parse_xl

calculation = r'''
# Normal assignment
x = 5 #kg

# Value reference
# then x is #x and 
#$$ v*x + 34 = d/#x

# Function creation
d = lambda x: 8*x

# Calculation refering anything
y= 34*x + d(x)
z = {'x_foo': 4, 5: 'foo'}[5]

# after text
'''

def test_latex():
    tex = 'test/t.tex'
    d = document(tex, tex, handler_t)
    d.send(calculation)
    assert d.write() == True
    # run(['do.bat', tex])

def test_word():
    word = 'test/w.docx'
    d = document(word, None, handler_w)
    d.send(calculation)
    assert d.write() == True
    # run(['start', 'test/w-out.docx'])

def test_excel():
    tex = 'test/t.tex'
    d = document(tex, tex, handler_t)
    calculation = parse_xl('test/e.xlsx')
    d.send(calculation)
    assert d.write() == True

