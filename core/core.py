import os
import hashlib
import folder_paths
from comfy_api.latest import ComfyAPI
from nodes import MAX_RESOLUTION

API = ComfyAPI()
MISSING = object()
MAX_RESOLUTION = MAX_RESOLUTION


# Set progressbar
async def set_progress(current=1, total=1):
    await API.execution.set_progress(
        value=current,
        max_value=total,
    )


# Load files
def load_files(keys, extensions, none_label="[no files found]"):
    extensions = {e.lower() for e in extensions}
    files = set()

    for key in keys:
        try:
            files.update(folder_paths.get_filename_list(key))
        except Exception:
            pass

    for key in keys:
        try:
            for base in folder_paths.get_folder_paths(key):
                for root, _, fnames in os.walk(base):
                    for f in fnames:
                        if os.path.splitext(f)[1].lower() in extensions:
                            rel = os.path.relpath(os.path.join(root, f), base)
                            files.add(rel)
        except Exception:
            pass

    return sorted(files) or [none_label]


# Get file hash
def get_annotated_file_hash(file):
    if not file or file == "none":
        return "none"

    image_path = folder_paths.get_annotated_filepath(file)
    h = hashlib.sha256()
    h.update(image_path.encode())
    h.update(str(os.path.getmtime(image_path)).encode())
    return h.hexdigest()


# Validate annotated file
def validate_annotated_file(file, className):
    if file == "none":
        return True
    if not folder_paths.exists_annotated_filepath(file):
        return f"[Nifty{className}] Invalid image file: {file}"
    return True
