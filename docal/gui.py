# The gui script for DoCaL
# writtn by K1DV5
# based on https://github.com/Dvlv/Tkinter-By-Example/

import tkinter as tk
from tkinter import filedialog
from docal import document


class Editor(tk.Tk):
    def __init__(self):
        super().__init__()

        self.FONT_SIZE = 12
        self.WINDOW_TITLE = "DoCaL"
        self.calc_file = ""
        self.document_in = ""
        self.document_out = ""

        self.title(self.WINDOW_TITLE)
        self.geometry("800x600")

        self.menubar = tk.Menu(self, bg="lightgrey", fg="black")

        # File menu on the menubar
        self.file_menu = tk.Menu(self.menubar, tearoff=0, bg="#eeeeee", fg="black")
        self.file_menu.add_command(label="New", command=self.file_new, accelerator="Ctrl+N")
        self.file_menu.add_command(label="Open", command=self.file_open, accelerator="Ctrl+O")
        self.file_menu.add_command(label="Save", command=self.file_save, accelerator="Ctrl+S")
        self.file_menu.add_command(label="Exit", command=self.quit)

        # Edit menu
        self.edit_menu = tk.Menu(self.menubar, tearoff=0, bg="#eeeeee", fg="black")
        self.edit_menu.add_command(label="Cut", command=self.edit_cut, accelerator="Ctrl+X")
        self.edit_menu.add_command(label="Paste", command=self.edit_paste, accelerator="Ctrl+V")
        self.edit_menu.add_command(label="Undo", command=self.edit_undo, accelerator="Ctrl+Z")
        self.edit_menu.add_command(label="Redo", command=self.edit_redo, accelerator="Ctrl+Y")

        # Operations menu
        self.ops_menu = tk.Menu(self.menubar, tearoff=0, bg="#eeeeee", fg="black")
        self.ops_menu.add_command(label="Select Input Document", command=self.sel_doc_in)
        self.ops_menu.add_command(label="Select Output Document", command=self.sel_doc_out)
        self.ops_menu.add_command(label="Send Calculations", command=self.send_calcs)

        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.menubar.add_cascade(label="Edit", menu=self.edit_menu)
        self.menubar.add_cascade(label="Operate", menu=self.ops_menu)

        self.configure(menu=self.menubar)
        self.main_text = tk.Text(self, bg="white", fg="black", font=("Consolas", self.FONT_SIZE))
        self.main_text.pack(expand=1, fill=tk.BOTH)

        self.bind("<Control-s>", self.file_save)
        self.bind("<Control-o>", self.file_open)
        self.bind("<Control-n>", self.file_new)

        self.bind("<Control-v>", self.edit_paste)
        self.main_text.bind("<Control-y>", self.edit_redo)

    def file_new(self, event=None):
        file_name = filedialog.asksaveasfilename()
        if file_name:
            self.calc_file = file_name
            self.main_text.delete(1.0, tk.END)
            self.title(" - ".join([self.WINDOW_TITLE, self.open_file]))

    def file_open(self, event=None):
        file_to_open = filedialog.askopenfilename()

        if file_to_open:
            self.calc_file = file_to_open
            self.main_text.delete(1.0, tk.END)

            with open(file_to_open, "r") as file_contents:
                file_lines = file_contents.readlines()
                if len(file_lines) > 0:
                    for index, line in enumerate(file_lines):
                        index = float(index) + 1.0
                        self.main_text.insert(index, line)

        self.title(" - ".join([self.WINDOW_TITLE, self.calc_file]))

    def file_save(self, event=None):
        if not self.calc_file:
            new_file_name = filedialog.asksaveasfilename()
            if new_file_name:
                self.calc_file = new_file_name

        if self.calc_file:
            new_contents = self.main_text.get(1.0, tk.END)
            with open(self.calc_file, "w") as open_file:
                open_file.write(new_contents)

    def edit_cut(self, event=None):
        self.main_text.event_generate("<<Cut>>")

    def edit_paste(self, event=None):
        self.main_text.event_generate("<<Paste>>")
        self.on_key_release()
        self.tag_all_lines()

    def edit_undo(self, event=None):
        self.main_text.event_generate("<<Undo>>")

    def edit_redo(self, event=None):
        self.main_text.event_generate("<<Redo>>")

    def sel_doc_in(self, event=None):
        self.document_in = filedialog.askopenfilename()

    def sel_doc_out(self, event=None):
        self.document_out = filedialog.askopenfilename()

    def send_calcs(self, event=None):
        doc = document(self.document_in)
        doc.send(self.main_text.get(1.0, "end"))
        doc.write(self.document_out)


def main():
    editor = Editor()
    editor.mainloop()


main()
