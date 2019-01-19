# The gui script for DoCaL -i
# writtn by K1DV5
# based on https://github.com/Dvlv/Tkinter-By-Example/

# for gui elements
import tkinter as tk
# for non ordinary gui elements
from tkinter import filedialog, messagebox, ttk
# main purpose
from docal import document
# file system path manipulations and double clicking
from os import path, startfile
# to know the platform
from sys import platform


class Editor(tk.Tk):
    def __init__(self, document_in=None, document_out=None):
        super().__init__()

        self.FONT_SIZE = 12
        self.WINDOW_TITLE = "DoCaL"
        self.calc_file = ""

        self.title(self.WINDOW_TITLE)
        # self.geometry("900x600")

        self.menubar = tk.Menu(self, bg="lightgrey", fg="black")

        # File menu on the menubar
        self.file_menu = tk.Menu(
            self.menubar, tearoff=0, bg="#eeeeee", fg="black")
        self.file_menu.add_command(
            label="New", command=self.file_new, accelerator="Ctrl+N")
        self.file_menu.add_command(
            label="Open", command=self.file_open, accelerator="Ctrl+O")
        self.file_menu.add_command(
            label="Save", command=self.file_save, accelerator="Ctrl+S")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.quit)

        # Edit menu
        self.edit_menu = tk.Menu(
            self.menubar, tearoff=0, bg="#eeeeee", fg="black")
        self.edit_menu.add_command(
            label="Cut", command=self.edit_cut, accelerator="Ctrl+X")
        self.edit_menu.add_command(
            label="Paste", command=self.edit_paste, accelerator="Ctrl+V")
        self.edit_menu.add_command(
            label="Undo", command=self.edit_undo, accelerator="Ctrl+Z")
        self.edit_menu.add_command(
            label="Redo", command=self.edit_redo, accelerator="Ctrl+Y")

        # Operations menu
        self.ops_menu = tk.Menu(self.menubar, tearoff=0,
                                bg="#eeeeee", fg="black")
        self.ops_menu.add_command(
            label="Select Input Document", command=self.sel_doc_in)
        self.ops_menu.add_command(
            label="Select Output Document", command=self.sel_doc_out)
        self.ops_menu.add_command(
            label="Send Calculations", command=self.send_calcs)

        # Help menu
        self.help_menu = tk.Menu(self.menubar, tearoff=0,
                bg="#eeeeee", fg="black")
        self.help_menu.add_command(
                label="User Guide")
        self.help_menu.add_command(
                label="About", command=self.show_about
                )

        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.menubar.add_cascade(label="Edit", menu=self.edit_menu)
        self.menubar.add_cascade(label="Operate", menu=self.ops_menu)
        self.menubar.add_cascade(label="Help", menu=self.help_menu)

        self.configure(menu=self.menubar)
        self.main_text = tk.Text(
            self, bg="white", fg="black", font=("Consolas", self.FONT_SIZE))
        self.main_text.pack(expand=1, fill=tk.BOTH, side="right")

        self.sidebar = ttk.Frame(self)
        self.sidebar.pack(expand=1, fill=tk.BOTH)

        ttk.Label(self.sidebar, text="Document input:").grid(
            row=1, column=0, columnspan=2, sticky=tk.E+tk.W)
        self.document_in = tk.StringVar(value=document_in)
        ttk.Entry(self.sidebar, textvariable=self.document_in).grid(row=2, column=0)
        ttk.Button(self.sidebar, text="Browse...",
                   command=self.sel_doc_in).grid(row=2, column=1)

        ttk.Label(self.sidebar, text="Document output:").grid(
            row=4, column=0, columnspan=2, sticky=tk.E+tk.W)
        self.document_out = tk.StringVar(value=document_out)
        ttk.Entry(self.sidebar, textvariable=self.document_out).grid(row=5, column=0)
        ttk.Button(self.sidebar, text="Browse...",
                   command=self.sel_doc_out).grid(row=5, column=1)

        self.open_after = tk.IntVar()
        ttk.Checkbutton(self.sidebar, text="Open the document afterwards.",
                        variable=self.open_after).grid(row=7, column=0, columnspan=2)

        ttk.Button(self.sidebar, text="Send",
                   command=self.send_calcs).grid(row=9)
        ttk.Button(self.sidebar, text="Clear",
                   command=self.clear_calcs).grid(row=9, column=1)

        self.sidebar.grid_rowconfigure(0, minsize=10)
        self.sidebar.grid_rowconfigure(3, minsize=10)
        self.sidebar.grid_rowconfigure(6, minsize=10)
        self.sidebar.grid_rowconfigure(8, minsize=10)

        self.bind("<Control-s>", self.file_save)
        self.bind("<Control-o>", self.file_open)
        self.bind("<Control-n>", self.file_new)

        self.bind("<Control-z>", self.edit_undo)
        self.bind("<Control-y>", self.edit_redo)

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

    def edit_undo(self, event=None):
        self.main_text.event_generate("<<Undo>>")

    def edit_redo(self, event=None):
        self.main_text.event_generate("<<Redo>>")

    def sel_doc_in(self, event=None):
        doc_in = filedialog.askopenfilename()
        self.document_in.set(doc_in)
        # if the input doc is not empty and the output doc is
        if not self.document_out.get().strip() and doc_in.strip():
            base, ext = path.splitext(doc_in)
            if ext == '.tex':
                self.document_out.set(doc_in)
            else:
                self.document_out.set(''.join([base, '-out', ext]))

    def sel_doc_out(self, event=None):
        self.document_out.set(filedialog.askopenfilename())

    def send_calcs(self, event=None):
        try:
            doc = document(self.document_in.get())
            doc.send(self.main_text.get(1.0, "end"))
            doc.write(self.document_out.get())
        except Exception as exc:
            messagebox.showerror('Error', exc.args[0])
        else:
            if self.open_after.get():
                if platform == 'win32':
                    startfile(self.document_out.get())
            else:
                messagebox.showinfo('Success',
                                    'The calculations have been sent successfully.')

    def clear_calcs(self, event=None):
        try:
            doc = document(self.document_in.get(), True)
            doc.write(self.document_out.get())
        except Exception as exc:
            messagebox.showerror('Error', exc.args[0])
        else:
            messagebox.showinfo(
                'Success', 'The document has been cleared successfully.')

    def show_about(self, event=None):
        messagebox.showinfo('About', "DoCaL\nPython 3.7.1\n\n© 2019 K1DV5")


def interface(doc_in=None, doc_out=None):
    editor = Editor(doc_in, doc_out)
    editor.mainloop()
