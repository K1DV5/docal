'''
script handler
'''
from sys import argv
from os import path
from glob import glob
from docal import document
from docal.parsing import color

def next_to(script):
    next_to = [f for f in glob(path.splitext(script)[0] + '.*')
            if path.splitext(f)[1] in ['.tex', '.docx']]
    if next_to:
        infile = next_to[0]
    else:
        print(color('ERROR:', 'red'), 'Cannot find a word or tex file here')
        exit()

    return infile


def main():
    arglen = len(argv)
    if arglen == 1:
        print(color('ERROR:', 'red'), 'No script name given.')
        exit()
    elif arglen == 2:
        script = argv[1]
        # find either a tex or docx file next to the script
        infile = next_to(script)
        outfile = None
    elif arglen == 3:
        script = argv[1]
        if argv[2] == '0':
            infile = next_to(script)
            outfile = 0
        else:
            infile = argv[2]
            outfile = None
    elif arglen == 4:
        script = argv[1]
        infile = argv[2]
        outfile = 0 if argv[3] == '0' else argv[3]

    with open(script) as file:
        instructions = file.read()

    d = document(infile)
    d.send(instructions)
    d.write(outfile)

try:
    main()
except Exception as exc:
    print(color('ERROR:', 'red'), f'[{exc.__class__.__name__}]', exc.args[0])
    exit()
