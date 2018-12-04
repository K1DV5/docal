'''
script handler
'''
from sys import argv
from docal import document

def main():
    arglen = len(argv)
    if arglen == 1:
        raise UserWarning('Input a script name')
    elif arglen == 2:
        script = argv[1]
        infile = script[:script.rfind('.') + 1] + 'tex'
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
    if outfile:
        d.write(outfile)
    else:
        d.write(0)

main()
