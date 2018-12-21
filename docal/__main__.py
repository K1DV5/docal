'''
script handler
'''
from sys import argv
from os import path
from glob import glob
from docal import document
from docal.parsing import color


def main():
    arglen = len(argv)
    if arglen == 1:
        print(color('ERROR:', 'red'), 'Input a script name')
        exit()
    elif arglen == 2:
        script = argv[1]
        # find either a tex or docx file next to the script
        next_to = [f for f in glob(path.splitext(script)[0] + '.*')
                if path.splitext(f)[1] in ['.tex', '.docx']]
        if next_to:
            infile = next_to[0]
        else:
            print(color('ERROR:', 'red'), 'Cannot find a word or tex file here')
            exit()
        outfile = None
    elif arglen == 3:
        script = argv[1]
        infile = argv[2]
        outfile = None
    elif arglen == 4:
        script = argv[1]
        infile = argv[2]
        outfile = argv[3]

    with open(script) as file:
        instructions = file.read()

    d = document(infile)
    d.send(instructions)
    if outfile == '0':
        d.write(0)
    else:
        d.write(outfile)

main()
