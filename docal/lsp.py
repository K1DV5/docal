from ast import Assign, Constant, Name, Starred, Tuple, parse, unparse
from typing import List
from pygls.server import LanguageServer
from lsprotocol.types import (
    InitializeParams,
    TextDocumentSyncKind,
    Diagnostic,
    DiagnosticSeverity,
    Position,
    Range
)

class DocalLSP(LanguageServer):
    pass

servername = 'docal'
server = DocalLSP(servername, '4.0.0')

def is_docal_file(uri: str) -> bool:
    return uri.endswith(".docal.py")

@server.feature('initialize')
def on_initialize(ls: DocalLSP, params: InitializeParams):
    return {
        'capabilities': {
            'textDocumentSync': TextDocumentSyncKind.Full,
        }
    }

def find_name_targets(target) -> list[Name]:
    targets = []
    if type(target) is Tuple or type(target) is List:
        for elem in target.elts:
            targets += find_name_targets(elem)
    elif type(target) is Name:
        targets.append(target)
    elif isinstance(target, Starred):
        targets += find_name_targets(target.value)
    else:
        raise TypeError('Unknown target', target)
    return targets

@server.feature('textDocument/didOpen')
@server.feature('textDocument/didChange')
def on_change(ls: DocalLSP, params):
    if not is_docal_file(params.text_document.uri):
        return
    text = ls.workspace.get_document(params.text_document.uri).source
    diagnostics = []

    globals = {}
    try:
        tree = parse(text)
    except SyntaxError:
        return
    for part in tree.body:
        try:
            exec(unparse(part), globals=globals)
        except:
            break
        if type(part) is not Assign:
            continue
        targets: list[Name] = []
        for target in part.targets:
            targets += find_name_targets(target)
        len_targets = len(targets)
        if len_targets == 1 and type(part.value) is Constant:
            continue
        for target in targets:
            diagnostics.append(Diagnostic(
                range=Range(
                    start=Position(line=target.lineno-1, character=target.col_offset),
                    end=Position(line=target.lineno-1, character=target.end_col_offset),
                ),
                message=f'{target.id if len_targets > 1 else ""} = {globals[target.id]}'.strip(),
                severity=DiagnosticSeverity.Information,
                source=servername,
            ))

    ls.publish_diagnostics(params.text_document.uri, diagnostics)

if __name__ == '__main__':
    server.start_io()
