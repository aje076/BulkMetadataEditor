import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess, json, os, sys, shutil, pathlib, re

APP_NAME = "Bulk Metadata Editor"
FIELDS = {
    "Type": "XMP.dc.Type",
    "Comments": "XMP.photoshop.Instructions",
    "Composers": "XMP.audio.Composer",
    "Contributors": "XMP.dc.Contributor",
    "Copyright": "XMP.dc.Rights",
    "Creators": "XMP.dc.Creator",
    "Directors": "XMP.video.Director",
    "Title": "XMP.dc.Title",
    "Genre": "XMP.video.Genre",
    "Kind": "XMP.dc.Type",
    "Label": "XMP.xmp.Label",
    "Mood": "XMP.audio.Mood",
    "Owner": "XMP.xmpRights.Owner",
    "Parental Rating": "XMP.xmp.Rating",
    "Producers": "XMP.video.Producer",
    "Protected": "XMP.xmpRights.Marked",
    "Publisher": "XMP.dc.Publisher",
    "Rating": "XMP.xmp.Rating",
    "Tags": "XMP.dc.Subject",
    "Writers": "XMP.video.Writer",
    "Author": "XMP.dc.Creator",
    "Subject": "XMP.dc.Subject",
    "Keywords": "XMP.dc.Subject",
    "Created Date": "XMP.xmp.CreateDate",
    "Modified Date": "XMP.xmp.ModifyDate",
}
SUPPORTED = {".jpg",".jpeg",".png",".tif",".tiff",".webp",".heic",".mp3",".flac",".wav",".m4a",".aac",".ogg",".mp4",".m4v",".mov",".mkv",".avi",".wmv",".pdf",".docx",".xlsx",".pptx",".txt"}

def resource_path(rel):
    root = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, rel)

def exiftool_path():
    candidates = [
        resource_path(os.path.join("exiftool", "exiftool.exe")),
        os.path.join(os.path.dirname(sys.executable), "exiftool", "exiftool.exe"),
        shutil.which("exiftool")
    ]
    for p in candidates:
        if p and os.path.isfile(p): return p
    return None

class App:
    def __init__(self, root):
        self.root=root
        root.title(APP_NAME); root.geometry("1120x720"); root.minsize(850,560)
        self.files=[]
        self.meta={}
        self.tool=exiftool_path()
        self.backup=tk.BooleanVar(value=True)
        self._ui()
        if not self.tool:
            self.status.set("ExifTool not found. Place exiftool.exe and its exiftool_files folder in an 'exiftool' subfolder.")
        else:
            self.status.set("Ready. Add files or folders to begin.")

    def _ui(self):
        top=ttk.Frame(self.root,padding=10); top.pack(fill="x")
        ttk.Button(top,text="Add Files",command=self.add_files).pack(side="left",padx=3)
        ttk.Button(top,text="Add Folder",command=self.add_folder).pack(side="left",padx=3)
        ttk.Button(top,text="Remove Selected",command=self.remove).pack(side="left",padx=3)
        ttk.Button(top,text="Read Metadata",command=self.read_metadata).pack(side="left",padx=3)
        ttk.Button(top,text="Export CSV",command=self.export_csv).pack(side="left",padx=3)
        ttk.Checkbutton(top,text="Create backups (_original)",variable=self.backup).pack(side="right",padx=8)
        panes=ttk.Panedwindow(self.root,orient="horizontal"); panes.pack(fill="both",expand=True,padx=10,pady=5)
        left=ttk.Frame(panes); right=ttk.Frame(panes); panes.add(left,weight=3); panes.add(right,weight=2)
        ttk.Label(left,text="Files").pack(anchor="w")
        self.list=ttk.Treeview(left,columns=("type","status"),show="tree headings",selectmode="extended")
        self.list.heading("#0",text="File"); self.list.heading("type",text="Type"); self.list.heading("status",text="Status")
        self.list.column("#0",width=360); self.list.column("type",width=85); self.list.column("status",width=100)
        sy=ttk.Scrollbar(left,orient="vertical",command=self.list.yview); self.list.configure(yscrollcommand=sy.set)
        self.list.pack(side="left",fill="both",expand=True); sy.pack(side="right",fill="y")
        ttk.Label(right,text="Edit selected metadata").pack(anchor="w")
        form=ttk.Frame(right); form.pack(fill="both",expand=True,pady=5)
        self.vars={}
        canvas=tk.Canvas(form,highlightthickness=0); sb=ttk.Scrollbar(form,orient="vertical",command=canvas.yview)
        inner=ttk.Frame(canvas); inner.bind("<Configure>",lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0),window=inner,anchor="nw"); canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
        for i,(name,tag) in enumerate(FIELDS.items()):
            ttk.Label(inner,text=name).grid(row=i,column=0,sticky="w",padx=5,pady=3)
            v=tk.StringVar()
            ent=ttk.Entry(inner,textvariable=v,width=32); ent.grid(row=i,column=1,sticky="ew",padx=5,pady=3)
            self.vars[name]=v
        inner.columnconfigure(1,weight=1)
        ttk.Button(right,text="Apply fields to selected files",command=self.apply).pack(fill="x",pady=5)
        ttk.Label(right,text="Filename is changed using the Rename box below. Blank fields are ignored; use Clear Field to remove a tag.").pack(anchor="w",pady=3)
        rename=ttk.Frame(right); rename.pack(fill="x",pady=4)
        ttk.Label(rename,text="Rename selected files to:").pack(side="left")
        self.rename_var=tk.StringVar(); ttk.Entry(rename,textvariable=self.rename_var).pack(side="left",fill="x",expand=True,padx=5)
        ttk.Button(rename,text="Rename",command=self.rename).pack(side="left")
        self.status=tk.StringVar(value="Starting...")
        ttk.Label(self.root,textvariable=self.status,relief="sunken",anchor="w",padding=5).pack(fill="x",side="bottom")

    def add_files(self):
        paths=filedialog.askopenfilenames(title="Select files")
        self._add(paths)
    def add_folder(self):
        folder=filedialog.askdirectory()
        if folder:
            paths=[]
            for root,dirs,files in os.walk(folder):
                for f in files:
                    p=os.path.join(root,f)
                    if pathlib.Path(p).suffix.lower() in SUPPORTED: paths.append(p)
            self._add(paths)
    def _add(self,paths):
        for p in paths:
            if p not in self.files and os.path.isfile(p):
                self.files.append(p); self.list.insert("", "end", iid=str(len(self.files)-1), text=os.path.basename(p), values=(pathlib.Path(p).suffix.upper().lstrip("."),"Not read"))
        self.status.set(f"{len(self.files)} file(s) in list.")
    def remove(self):
        ids=sorted([int(x) for x in self.list.selection()],reverse=True)
        for idx in ids:
            p=self.files[idx]
            self.files[idx]=None
            self.list.delete(str(idx))
        self.files=[p for p in self.files if p]
        self._rebuild()
    def _rebuild(self):
        for x in self.list.get_children(): self.list.delete(x)
        for i,p in enumerate(self.files):
            self.list.insert("","end",iid=str(i),text=os.path.basename(p),values=(pathlib.Path(p).suffix.upper().lstrip("."),"Ready"))
    def run_tool(self,args):
        if not self.tool: raise RuntimeError("ExifTool is missing. See README for setup.")
        cp=subprocess.run([self.tool]+args,capture_output=True,text=True,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        if cp.returncode not in (0,1): raise RuntimeError(cp.stderr.strip() or cp.stdout.strip() or "ExifTool failed")
        return cp.stdout
    def read_metadata(self):
        if not self.files: return
        self.status.set("Reading metadata..."); self.root.update_idletasks()
        try:
            out=self.run_tool(["-json","-G1","-s"]+self.files)
            records=json.loads(out)
            self.meta={r.get("SourceFile"):r for r in records}
            for i,p in enumerate(self.files):
                vals=list(self.list.item(str(i),"values")); vals[1]="Read"
                self.list.item(str(i),values=vals)
            if records:
                first=records[0]
                for name,tag in FIELDS.items():
                    short=tag.split(".")[-1]
                    value=first.get(tag,first.get("XMP:"+short,first.get(short,"")))
                    if isinstance(value,list): value=", ".join(map(str,value))
                    self.vars[name].set(str(value) if value is not None else "")
            self.status.set(f"Metadata read for {len(records)} file(s). Fields shown are from the first file.")
        except Exception as e: messagebox.showerror("Read error",str(e)); self.status.set("Read failed.")
    def apply(self):
        chosen=[self.files[int(x)] for x in self.list.selection()]
        if not chosen: messagebox.showinfo("Select files","Select one or more files first."); return
        updates={n:v.get().strip() for n,v in self.vars.items() if v.get().strip()}
        if not updates: messagebox.showinfo("No changes","Enter at least one metadata value."); return
        if not messagebox.askyesno("Confirm changes",f"Apply {len(updates)} metadata field(s) to {len(chosen)} file(s)?"): return
        args=[]
        if not self.backup.get(): args.append("-overwrite_original")
        for n,value in updates.items(): args.append("-"+FIELDS[n]+"="+value)
        args.extend(chosen)
        try:
            self.run_tool(args)
            self.status.set(f"Updated {len(chosen)} file(s).")
            messagebox.showinfo("Complete",f"Metadata updated for {len(chosen)} file(s).")
        except Exception as e: messagebox.showerror("Write error",str(e))
    def rename(self):
        chosen=[self.files[int(x)] for x in self.list.selection()]
        pattern=self.rename_var.get().strip()
        if not chosen or not pattern: messagebox.showinfo("Rename","Select files and enter a new filename."); return
        if len(chosen)>1 and "{n}" not in pattern:
            messagebox.showwarning("Filename pattern","For multiple files, include {n} (sequence number), e.g. Holiday_{n}.jpg"); return
        if not messagebox.askyesno("Confirm rename",f"Rename {len(chosen)} selected file(s)?"): return
        errors=[]
        for i,p in enumerate(chosen,1):
            ext=pathlib.Path(p).suffix
            stem=pattern.replace("{n}",str(i))
            if not pathlib.Path(stem).suffix: stem+=ext
            dest=os.path.join(os.path.dirname(p),stem)
            if os.path.exists(dest): errors.append(f"Already exists: {dest}"); continue
            try: os.rename(p,dest); self.files[self.files.index(p)]=dest
            except Exception as e: errors.append(str(e))
        self._rebuild()
        messagebox.showinfo("Rename complete","\n".join(errors) if errors else "Files renamed successfully.")
    def export_csv(self):
        if not self.meta: self.read_metadata()
        if not self.meta: return
        import csv
        path=filedialog.asksaveasfilename(defaultextension=".csv",filetypes=[("CSV","*.csv")])
        if not path:return
        keys=sorted(set(k for r in self.meta.values() for k in r))
        with open(path,"w",newline="",encoding="utf-8-sig") as f:
            w=csv.DictWriter(f,fieldnames=keys); w.writeheader(); w.writerows(self.meta.values())
        self.status.set("CSV exported.")

if __name__=="__main__":
    root=tk.Tk()
    try: ttk.Style().theme_use("vista")
    except: pass
    App(root)
    root.mainloop()
