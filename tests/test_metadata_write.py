import json
import os
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
try:
    import tkinter  # noqa: F401
except ImportError:
    tkinter = None


@pytest.fixture
def editor_module():
    if tkinter is None:
        pytest.skip("Tkinter is not available")
    if not os.environ.get("EXIFTOOL_PATH"):
        pytest.skip("EXIFTOOL_PATH is not set")
    import bulk_metadata_editor
    return bulk_metadata_editor


class FakeVar:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeList:
    def __init__(self, count):
        self.values = {str(i): ("XMP", "Ready") for i in range(count)}

    def selection(self):
        return tuple(self.values)

    def item(self, iid, option=None, **kwargs):
        if "values" in kwargs:
            self.values[iid] = tuple(kwargs["values"])
        if option == "values":
            return self.values[iid]


class FakeRoot:
    def update_idletasks(self):
        pass


class FakeBackup:
    def get(self):
        return True


XMP_SAMPLE = '''<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/">
   <dc:title><rdf:Alt><rdf:li xml:lang="x-default">Original title</rdf:li></rdf:Alt></dc:title>
   <dc:description><rdf:Alt><rdf:li xml:lang="x-default">Preserve description</rdf:li></rdf:Alt></dc:description>
   <photoshop:Instructions>Preserve instructions</photoshop:Instructions>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
'''


def read_metadata(exiftool, path):
    result = subprocess.run(
        [exiftool, "-json", "-G1", "-s", str(path)],
        check=True,
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return json.loads(result.stdout)[0]


def build_fake_app(paths, editor_module):
    app = editor_module.App.__new__(editor_module.App)
    app.files = [str(path) for path in paths]
    app.tool = os.environ["EXIFTOOL_PATH"]
    app.backup = FakeBackup()
    app.list = FakeList(len(paths))
    app.vars = {name: FakeVar() for name in editor_module.FIELDS}
    app.root = FakeRoot()
    app.status = FakeVar()
    app.results = None
    app._show_write_results = lambda successes, failures: setattr(app, "results", (successes, failures))
    return app


def test_apply_writes_filled_fields_to_multiple_files_and_preserves_blanks(tmp_path, monkeypatch, editor_module):
    exiftool = os.environ.get("EXIFTOOL_PATH")
    paths = [tmp_path / "sample one.xmp", tmp_path / "sample two.xmp"]
    for path in paths:
        path.write_text(XMP_SAMPLE, encoding="utf-8")

    app = build_fake_app(paths, editor_module)
    app.vars["Title"].set("Updated title")
    app.vars["Comments"].set("")
    monkeypatch.setattr(editor_module.messagebox, "askyesno", lambda *args, **kwargs: True)

    app.apply()

    successes, failures = app.results
    assert len(successes) == 2
    assert failures == []
    for path in paths:
        values = read_metadata(exiftool, path)
        assert values["XMP-dc:Title"] == "Updated title"
        assert values["XMP-dc:Description"] == "Preserve description"
        assert values["XMP-photoshop:Instructions"] == "Preserve instructions"


def test_missing_file_failure_has_a_specific_recovery_hint(tmp_path, editor_module):
    app = build_fake_app([], editor_module)
    missing_path = tmp_path / "does-not-exist.xmp"
    with pytest.raises(RuntimeError) as error:
        app._write_one_file(str(missing_path), {"XMP-dc:Title": "Sample title"})

    hint = app._solution_for_error(str(error.value))
    assert "add it again" in hint.lower()
