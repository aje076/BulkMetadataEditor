import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess, json, os, sys, shutil, pathlib, re

APP_NAME = "Bulk Metadata Editor"
FIELDS = {
    # ExifTool's write syntax uses group:tag names (for example XMP-dc:Title).
    "Type": "XMP-dc:Type",
    "Comments": "XMP-photoshop:Instructions",
    "Composers": "XMP-xmpDM:Composer",
    "Contributors": "XMP-dc:Contributor",
    "Copyright": "XMP-dc:Rights",
    "Creators": "XMP-dc:Creator",
    "Directors": "XMP-xmpDM:Director",
    "Title": "XMP-dc:Title",
    "Genre": "XMP-xmpDM:Genre",
    "Kind": "XMP-dc:Type",
    "Label": "XMP-xmp:Label",
    "Mood": "XMP-audio:Mood",
    "Owner": "XMP-xmpRights:Owner",
    "Parental Rating": "XMP-xmp:Rating",
    "Producers": "XMP-xmpDM:Producer",
    "Protected": "XMP-xmpRights:Marked",
    "Publisher": "XMP-dc:Publisher",
    "Rating": "XMP-xmp:Rating",
    "Tags": "XMP-dc:Subject",
    "Writers": "XMP-xmpDM:Writer",
    "Author": "XMP-dc:Creator",
    "Subject": "XMP-dc:Subject",
    "Keywords": "XMP-dc:Subject",
    "Created Date": "XMP-xmp:CreateDate",
    "Modified Date": "XMP-xmp:ModifyDate",
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
        ttk.Label(left,text="Select one file, or Ctrl/Shift-click to select multiple files.").pack(anchor="w",pady=3)
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
        ttk.Label(right,text="Only filled fields are written. Blank fields leave existing metadata unchanged.").pack(anchor="w",pady=3)
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

    def _write_one_file(self,path,updates):
        args=[]
        if not self.backup.get(): args.append("-overwrite_original")
        for tag,value in updates.items(): args.append("-"+tag+"="+value)
        args.append(path)
        cp=subprocess.run([self.tool]+args,capture_output=True,text=True,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        output="\n".join(x.strip() for x in (cp.stdout,cp.stderr) if x and x.strip())

        # Read the requested tags back so a no-op or unsupported tag is not
        # reported as a successful write just because ExifTool started.
        check_args=["-json","-G1","-s"]+["-"+tag for tag in updates]+[path]
        verify=subprocess.run([self.tool]+check_args,capture_output=True,text=True,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        if verify.returncode != 0:
            reason=verify.stderr.strip() or verify.stdout.strip() or "Could not verify the written metadata."
            if cp.returncode != 0: reason=f"ExifTool exited with code {cp.returncode}: {output or 'write error'}; verification also failed: {reason}"
            raise RuntimeError(reason)
        try:
            records=json.loads(verify.stdout)
            record=records[0]
        except (ValueError,IndexError,TypeError):
            raise RuntimeError("ExifTool could not read the file back to verify the changes. Check that the file is supported and readable.")
        mismatches=[]
        lowered={str(k).lower():v for k,v in record.items()}
        for tag,expected in updates.items():
            actual=record.get(tag,lowered.get(tag.lower()))
            if isinstance(actual,list): actual=", ".join(str(x) for x in actual)
            if actual is None or self._normalise_value(tag,str(actual)) != self._normalise_value(tag,expected):
                mismatches.append(f"{tag} was not saved as entered")
        if mismatches:
            reason="; ".join(mismatches)+". The file format may not support this XMP field."
            if cp.returncode != 0: reason+=f" ExifTool also reported: {output or 'write error'}. Some other fields may have been applied."
            raise RuntimeError(reason)
        return (f"ExifTool returned code {cp.returncode}: {output}" if cp.returncode != 0 else "")

    @staticmethod
    def _normalise_value(tag,value):
        value=str(value).strip()
        if tag in {"XMP-xmp:CreateDate","XMP-xmp:ModifyDate"}:
            # ExifTool commonly renders XMP dates as YYYY:MM:DD HH:MM:SSZ,
            # while users usually enter ISO dates or timestamps.
            match=re.match(r"^(\d{4})[:-](\d{2})[:-](\d{2})(?:[ T](\d{2}:\d{2}:\d{2}))?",value)
            if match:
                date="-".join(match.group(i) for i in (1,2,3))
                time=match.group(4)
                return date+("T"+time if time and time != "00:00:00" else "")
        return value

    @staticmethod
    def _solution_for_error(error):
        message=error.lower()
        if "permission" in message or "access is denied" in message or "read-only" in message:
            return "Check that the file is not read-only and that your Windows account can edit its folder. If it is on a removable or shared drive, check that drive's write access."
        if "being used" in message or "in use" in message or "locked" in message:
            return "Close the file in other programs, then try again."
        if "unsupported" in message or "not saved" in message or "not writable" in message:
            return "This file type may not support the requested XMP field. Try a supported format or remove that field for this file."
        if "no such file" in message or "cannot open" in message or "could not be found" in message:
            return "Check that the file still exists at the listed location, then remove it and add it again."
        return "Check that the file is accessible and supported, close it in other programs, then retry. Keep the original backup until you confirm the result."

    def _show_write_results(self,successes,failures):
        summary=f"Processed {len(successes)+len(failures)} file(s): {len(successes)} successful, {len(failures)} failed."
        lines=[summary,"", "SUCCESSFUL FILES"]
        lines.extend("  "+path+("\n    Note: "+note if note else "") for path,note in successes) if successes else lines.append("  None")
        lines.extend(["", "FILES THAT FAILED"])
        if failures:
            for path,error in failures:
                lines.extend(["  "+path,"    Reason: "+error,"    Try: "+self._solution_for_error(error)])
        else:
            lines.append("  None")
        report="\n".join(lines)
        win=tk.Toplevel(self.root); win.title("Metadata update results"); win.geometry("760x480"); win.transient(self.root)
        ttk.Label(win,text=summary,padding=10).pack(anchor="w")
        body=ttk.Frame(win,padding=(10,0,10,10)); body.pack(fill="both",expand=True)
        text=tk.Text(body,wrap="word",height=20); scroll=ttk.Scrollbar(body,orient="vertical",command=text.yview)
        text.configure(yscrollcommand=scroll.set); text.pack(side="left",fill="both",expand=True); scroll.pack(side="right",fill="y")
        text.insert("1.0",report); text.configure(state="disabled")
        buttons=ttk.Frame(win,padding=10); buttons.pack(fill="x")
        def copy_report():
            win.clipboard_clear(); win.clipboard_append(report); self.status.set("Processing report copied to clipboard.")
        ttk.Button(buttons,text="Copy report",command=copy_report).pack(side="left")
        ttk.Button(buttons,text="Close",command=win.destroy).pack(side="right")
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
                    short=tag.split(":")[-1]
                    value=first.get(tag,first.get("XMP:"+short,first.get(short,"")))
                    if isinstance(value,list): value=", ".join(map(str,value))
                    self.vars[name].set(str(value) if value is not None else "")
            self.status.set(f"Metadata read for {len(records)} file(s). Fields shown are from the first file.")
        except Exception as e: messagebox.showerror("Read error",str(e)); self.status.set("Read failed.")
    def apply(self):
        chosen=[self.files[int(x)] for x in self.list.selection()]
        if not chosen: messagebox.showinfo("Select files","Select one or more files first."); return
        if not self.tool:
            messagebox.showerror("ExifTool missing","ExifTool was not found. Place exiftool.exe and its exiftool_files folder in the application's exiftool folder.")
            return
        filled={n:v.get().strip() for n,v in self.vars.items() if v.get().strip()}
        by_tag={}
        for name,value in filled.items():
            tag=FIELDS[name]
            if tag in by_tag and by_tag[tag][1] != value:
                messagebox.showerror("Conflicting fields",f"{by_tag[tag][0]} and {name} refer to the same metadata tag but have different values. Use the same value in both fields or leave one blank.")
                return
            by_tag[tag]=(name,value)
        updates={tag:value for tag,(name,value) in by_tag.items()}
        if not updates: messagebox.showinfo("No changes","Enter at least one metadata value."); return
        if not messagebox.askyesno("Confirm changes",f"Apply {len(filled)} filled metadata field(s) to {len(chosen)} selected file(s)? Blank fields will be left unchanged."): return
        successes=[]; failures=[]
        for path in chosen:
            try:
                note=self._write_one_file(path,updates)
                successes.append((path,note))
                i=self.files.index(path); vals=list(self.list.item(str(i),"values")); vals[1]="Updated"; self.list.item(str(i),values=vals)
            except Exception as e:
                failures.append((path,str(e)))
                i=self.files.index(path); vals=list(self.list.item(str(i),"values")); vals[1]="Failed"; self.list.item(str(i),values=vals)
            self.status.set(f"Processed {len(successes)+len(failures)} of {len(chosen)} selected file(s)...")
            self.root.update_idletasks()
        self.status.set(f"Finished: {len(successes)} successful, {len(failures)} failed.")
        self._show_write_results(successes,failures)
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
