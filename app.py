import os
import shutil
import subprocess
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    # petites sécurités
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Upload une image (jpg/png/webp).")

    workdir = tempfile.mkdtemp(prefix="oemer_")
    try:
        in_path = os.path.join(workdir, file.filename or "input.jpg")
        with open(in_path, "wb") as f:
            f.write(await file.read())

        # oemer CLI: oemer <path_to_image> (README) :contentReference[oaicite:4]{index=4}
        # -o pour choisir le dossier de sortie (README options) :contentReference[oaicite:5]{index=5}
        cmd = ["oemer", in_path, "-o", workdir, "--without-deskew"]
        p = subprocess.run(cmd, capture_output=True, text=True)

        if p.returncode != 0:
            raise HTTPException(
                500,
                f"oemer failed.\nSTDOUT:\n{p.stdout[-1500:]}\nSTDERR:\n{p.stderr[-1500:]}"
            )

        # oemer produit un MusicXML dans le dossier de sortie (README) :contentReference[oaicite:6]{index=6}
        # On cherche un .musicxml ou .xml
        out_file = None
        for name in os.listdir(workdir):
            low = name.lower()
            if low.endswith(".musicxml") or low.endswith(".xml"):
                out_file = os.path.join(workdir, name)
                break

        if not out_file:
            raise HTTPException(500, "Pas de fichier MusicXML trouvé en sortie.")

        return FileResponse(out_file, media_type="application/xml", filename=os.path.basename(out_file))

    finally:
        shutil.rmtree(workdir, ignore_errors=True)
