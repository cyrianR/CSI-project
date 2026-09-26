# Compression Streaming and Interaction Project

Implementation of algorithms for progressive transmission of 3D models descibed in [research papers](./papers/). This [project](./papers/ProjetCSI2026.pdf) is part of the ENSEEIHT curriculum for students specialized in Image & Multimedia.

## Developer tutorial

Create a vitrual environment and install dependencies :
```
python3 -m venv .venv
source .venv/bin/activate 
pip install -r requirements.txt
```

Run the server :
```
./server.py
```

Visualize a first example of transmission of 3D models at these urls :
```
http://localhost:8000/?example/bunny.obja
http://localhost:8000/?example/suzanne.obja
```