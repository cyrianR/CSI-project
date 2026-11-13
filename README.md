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
- Decimate
```
mkdir server/data
python -m mesh_stream.decimate example/suzanne.obj server/data/suzanne-decimate.obja
```

- Progressive mesh
> Note : change to the desired priority in the file progressive_mesh/model.py
> Usage : python -m mesh_stream.progressive_mesh <in_obj_file> <out_obja_file> <max_collapse>
```
mkdir server/data
python -m mesh_stream.progressive_mesh example/suzanne.obj server/data/suzanne-pm.obja 100
```


Run the server :
```
server/start.py
```

Visualize transmission of the 3D models :
```
http://localhost:8000/?data/suzanne-decimate.obja
```

Utilisation de l'IA :

- Debug des erreurs, warnings Pylance.
- Autocomplétion Copilot.
- Suggestion et utilisation de packages Python.
- Correction de grammaire / orthographe du mini-rapport.
- Aide à la compréhension et rappels de propriétés des mesh 3D : pas explication des papiers
- Github Copilot, Claude, ChatGPT.