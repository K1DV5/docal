from ast import Assign, Name, parse, unparse
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

@server.feature('textDocument/didOpen')
@server.feature('textDocument/didChange')
def on_change(ls: DocalLSP, params):
    if not is_docal_file(params.text_document.uri):
        return
    text = ls.workspace.get_document(params.text_document.uri).source
    diagnostics = []

    globals = {}
    for part in parse(text).body:
        exec(unparse(part), globals=globals)
        if type(part) != Assign:
            continue
        target: Name
        for target in part.targets:
            diagnostics.append(Diagnostic(
                range=Range(
                    start=Position(line=target.lineno-1, character=target.col_offset),
                    end=Position(line=target.lineno-1, character=target.end_col_offset),
                ),
                message=f'{target.id} = {globals[target.id]}',
                severity=DiagnosticSeverity.Information,
                source=servername,
            ))

    ls.publish_diagnostics(params.text_document.uri, diagnostics)

if __name__ == '__main__':
    server.start_io()
