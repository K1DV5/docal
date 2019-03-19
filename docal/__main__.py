'''
script handler
'''
from argparse import ArgumentParser
from os import path
from glob import glob
from docal import document


# command line arguments
parser = ArgumentParser(description="Process the script file, inject it to "
                        "the input document and produce the output document")
parser.add_argument('script', help='The calculation file/script')
parser.add_argument('-i', '--input', help='The document file to be modified')
parser.add_argument('-o', '--output', help='The destination document file')
parser.add_argument('-io', '--input-output',
                    help="The document file to be modified in place. Use this "
                    "when you don't want to create another file.")
parser.add_argument('-c', '--clear', action='store_true',
                    help='Clear the calculations and try to '
                    'revert the document to the previous state. '
                    'Only for the calculation ranges in LaTeX files.')
parser.add_argument('-l', '--log-level', choices=['INFO', 'WARNING', 'ERROR'],
        help='How much info you want to see')
args = parser.parse_args()

if args.input_output:
    args.input = args.output = args.input_output


def main():
    '''
    main function in this script
    '''
    try:
        if args.script:
            with open(args.script) as file:
                instructions = file.read()
        else:
            instructions = None
        d = document(args.input, to_clear=args.clear, log_level=args.log_level)
        d.send(instructions)
        d.write(args.output)
    except Exception as exc:
        print('ERROR:', exc)
        exit()


if __name__ == '__main__':
    main()
