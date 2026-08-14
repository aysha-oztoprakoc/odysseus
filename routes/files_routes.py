import os
import shutil
import zipfile
import tarfile
from fastapi import APIRouter, Request, HTTPException, Query, Body, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from src.auth_helpers import get_current_user
from src.tool_security import owner_is_admin_or_single_user

class WriteRequest(BaseModel):
    path: str
    content: str

class PathRequest(BaseModel):
    path: str

def setup_files_routes():
    router = APIRouter(prefix="/api/files", tags=["files"])

    def _vet_admin(request: Request):
        owner = get_current_user(request)
        if not owner_is_admin_or_single_user(owner):
            raise HTTPException(status_code=403, detail="File management is admin-only")

    @router.get("/browse")
    def browse(request: Request, path: str = Query(default="")):
        _vet_admin(request)
        target = os.path.realpath(os.path.expanduser(path.strip() or "~"))
        if not os.path.exists(target) or not os.path.isdir(target):
            target = os.path.realpath(os.path.expanduser("~"))

        items = []
        try:
            with os.scandir(target) as it:
                for entry in it:
                    try:
                        is_dir = entry.is_dir(follow_symlinks=False)
                        stat = entry.stat(follow_symlinks=False)
                        items.append({
                            "name": entry.name,
                            "path": os.path.join(target, entry.name),
                            "is_dir": is_dir,
                            "size": stat.st_size if not is_dir else 0,
                            "mtime": stat.st_mtime
                        })
                    except OSError:
                        continue
        except (PermissionError, OSError) as e:
            raise HTTPException(status_code=500, detail=str(e))

        # Sort: directories first, then alphabetical
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        parent = os.path.dirname(target)
        
        return {
            "path": target,
            "parent": parent if parent and parent != target else None,
            "items": items
        }

    @router.get("/read")
    def read_file(request: Request, path: str = Query(...)):
        _vet_admin(request)
        target = os.path.realpath(os.path.expanduser(path))
        if not os.path.isfile(target):
            raise HTTPException(status_code=404, detail="File not found")
        try:
            with open(target, "r", encoding="utf-8") as f:
                content = f.read()
            return {"content": content}
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File is binary or not UTF-8")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/write")
    def write_file(request: Request, req: WriteRequest):
        _vet_admin(request)
        target = os.path.realpath(os.path.expanduser(req.path))
        try:
            with open(target, "w", encoding="utf-8") as f:
                f.write(req.content)
            return {"status": "ok"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/delete")
    def delete_path(request: Request, req: PathRequest):
        _vet_admin(request)
        target = os.path.realpath(os.path.expanduser(req.path))
        if not os.path.exists(target):
            raise HTTPException(status_code=404, detail="Path not found")
        try:
            if os.path.isdir(target):
                shutil.rmtree(target)
            else:
                os.remove(target)
            return {"status": "ok"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/extract")
    def extract_archive(request: Request, req: PathRequest):
        _vet_admin(request)
        target = os.path.realpath(os.path.expanduser(req.path))
        if not os.path.isfile(target):
            raise HTTPException(status_code=404, detail="File not found")
        
        extract_dir = os.path.dirname(target)
        try:
            if target.endswith(".zip"):
                with zipfile.ZipFile(target, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)
            elif target.endswith(".tar.gz") or target.endswith(".tgz") or target.endswith(".tar"):
                with tarfile.open(target, "r:*") as tar_ref:
                    tar_ref.extractall(extract_dir)
            else:
                raise HTTPException(status_code=400, detail="Unsupported archive format")
            return {"status": "ok", "extract_dir": extract_dir}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/download")
    def download_file(request: Request, path: str = Query(...)):
        _vet_admin(request)
        target = os.path.realpath(os.path.expanduser(path))
        if not os.path.isfile(target):
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(target, filename=os.path.basename(target))

    @router.post("/upload")
    async def upload_file(request: Request, dir_path: str = Query(...), file: UploadFile = File(...)):
        _vet_admin(request)
        target_dir = os.path.realpath(os.path.expanduser(dir_path))
        if not os.path.isdir(target_dir):
            raise HTTPException(status_code=400, detail="Target is not a directory")
        target_file = os.path.join(target_dir, file.filename)
        try:
            with open(target_file, "wb") as f:
                while contents := await file.read(1024 * 1024):
                    f.write(contents)
            return {"status": "ok"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router
