# Compression Streaming and Interaction Project

Implementation of algorithms for progressive transmission of 3D models descibed in [research papers](./papers/). This [project](./papers/ProjetCSI2026.pdf) is part of the ENSEEIHT curriculum for students specialized in Image & Multimedia.

## Developer tutorial and example

Create a vitrual environment and install dependencies :
```
python3 -m venv .venv
source .venv/bin/activate 
pip install -r requirements.txt
```

Create an obja model with desired method:
```
mkdir server/data
python -m mesh_stream.decimate example/suzanne.obj server/data/suzanne-decimate.obja
```

```
mkdir server/data
python -m mesh_stream.progressive_mesh example/suzanne.obj server/data/suzanne-pm.obja
```


Run the server :
```
server/start.py
```

Visualize transmission of the 3D models :
```
http://localhost:8000/?data/suzanne-decimate.obja
```