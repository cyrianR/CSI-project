# OBJ augmenté

WaveFront OBJ est un format permettant d'encoder des modèles 3D de manière
simple. Cependant, il n'est pas adapté aux représentations progressives. Pour
cela, nous avons augmenté OBJ de nouvelles commandes qui permettent de modifier
le contenu préalablement déclaré.

## Utilisation

Vous pouvez récupérer les sources de cette application en lançant la commande
```
git clone https://gitea.tforgione.fr/tforgione/obja
```

## Écriture d'un logiciel de compression progressive

Le module `obja.py` permet de parser facilement des fichiers OBJ et de générer
des fichiers au format OBJA.

La classe `obja.Model` permet de facilement parser un fichier OBJ (grâce à la
méthode `parse_file`. Elle contient les attributs suivants :

  - `vertices` : une liste de `numpy.array` qui représente les sommets du
    modèle (attention, les vecteurs sont en ligne)
  - `faces` : une liste de `obja.Face`, qui contiennent eux-mêmes des attributs
    `a`, `b` et `c` qui sont les indices des sommets dans l'attribut
    `vertices` (les indices commencent à partir de 0).

La classe `obja.Output` permet de générer facilement un modèle OBJA. Lors de la
transformation d'un modèle pour l'adapter à un chargement progressif, le modèle
doit être reconstruit et les indices des sommets et faces sont changés. La
classe permet de travailler avec les indices du modèle d'origine, et donc de
gérer automatiquement la transformation des indices de l'ancien modèle vers le
nouveau modèle.

Le fichier `decimate.py` contient un exemple basique de programme permettant la
réécriture d'un fichier OBJ en OBJA de manière naïve. Il contient un programme
principal qui transforme le fichier `example/suzanne.obj` en
`example/suzanne.obja`, le rendant progressif.

## Visualisation du streaming

À la racine de ce projet, le script `server.py` vous permet de démarrer un
server de streaming. Vous pouvez l'exécuter en lançant `./server.py`. Une fois
cela fait, vous pouvez allez sur [localhost:8000](http://localhost:8000) pour
lancer le streaming. Le navigateur télécharge progressivement les données et
les affiche.

Les modèles peuvent être
visualisés en ajoutant `?chemin/nom_du_modele.obj` à la fin de l'url. Par exemple,
[localhost:8000/?example/bunny.obja](http://localhost:8000/?example/bunny.obja)
chargera le modèle `bunny.obja` du dossier `example`. Ce modèle est un modèle
d'exemple, il commence par encoder la version basse résolution du [Stanford
bunny](https://graphics.stanford.edu/data/3Dscanrep/), translate tous ses
sommets, les retranslate vers leurs positions d'origine puis supprime toutes
les faces.

### Détails du format OBJA

###### Ajout d'un sommet

Comme dans le OBJ standard, pour ajouter un sommet, il suffit d'utiliser le
caractère `v` suivi des coordonnées du sommet. Par exemple :

```
v 1.0 2.0 3.0
```

###### Ajout d'une face

Comme dans le OBJ standard, pour ajouter une face, il suffit d'utiliser le
caractère `f` suivi des indices des sommets de la face. Par exemple :

```
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 1.0 1.0 0.0
f 1 2 3
```

**Attention :** en OBJ, les indices commencent à partir de 1

**Attention :** dans notre logiciel, seules les faces triangulaires sont
implémentées.

###### Edition d'un sommet

Notre format OBJ permet la modification d'un ancien sommet. Pour modifier un
sommet, il suffit d'utiliser les caractères `ev` suivis de l'indice du sommet à
modifier puis de ses nouvelles coordonées. Par exemple :

```
v 0.0 0.0 0.0
ev 1 1.0 1.0 1.0
```

###### Translation d'un sommet

De la même façon, un sommet peut être translaté grâce aux caractères `tv`. Par
exemple :

```
v 1.0 2.0 3.0
tv 1 1.0 1.0 1.0
```

###### Edition d'une face

Notre format OBJ permet la modification d'une ancienne face. Pour modifier une
face, il suffit d'utiliser les caractères `ef` suivis de l'indice de la face à
modifier puis des indices de ses nouveaux sommets. Par exemple :

```
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 1.0 1.0 0.0
v 1.0 1.0 1.0
f 1 2 3
ef 1 1 2 4
```

On peut aussi changer un seul sommet d'une face grâce aux caractères `efv`,
suivi de l'indice de la face à modifier, de l'indice du sommet à modifier (1, 2
ou 3) et de la nouvelle valeur du sommet. Par exemple :

```
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 1.0 1.0 0.0
v 1.0 1.0 1.0
f 1 2 3
efv 1 3 4
```

###### Suppression d'une face
Notre format OBJ permet la suppression d'une ancienne face. Pour supprimer une
face, il suffit d'utiliser les caracètres `df` suivis de l'indice de la face à
supprimer. Par exemple :

```
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 1.0 1.0 0.0
v 1.0 1.0 1.0
f 1 2 3
df 1
```

**Attention :** les indices des faces suivantes ne sont pas changés après la
suppression d'une ancienne face.

##### Changer la couleur d'une face

Notre format OBJ permet de changer la couleur d'une face. Pour changer la
couleur d'une face, il suffit de d'utiliser les caractères `fc` suivis de
l'indice de la face dont vous souhaitez changer la couleur, puis des
composantes rouges, vertes et bleues, entre 0 et 1.


```
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 1.0 1.0 0.0
v 1.0 1.0 1.0
f 1 2 3
fc 1 1.0 0.0 0.0
```

###### Triangle strips et triangle fans
Pour la compression de contenu 3D, on peut utiliser des [Triangle
Strips](https://en.wikipedia.org/wiki/Triangle_strip) et des [Triangle
Fans](https://en.wikipedia.org/wiki/Triangle_fan).

Notre format OBJ augmenté permet la déclaration de strips et de fans en
utilisant respectivement les caractères `ts` et `tf` suivis des indices des
sommets. Par exemple :

```
v -1.0 0.0 0.0
v -0.5 1.0 0.0
v 0.0 0.0 0.0
v 0.5 1.0 0.0
v 1.0 0.0 0.0
ts 1 2 3 4 5
```

ou bien

```
v 0.0 0.0 0.0
v -1.0 0.0 0.0
v -0.707 0.707 0.0
v 0.0 1.0 0.0
v 0.707 0.707 0.0
v 1.0 0.0 0.0
tf 1 2 3 4 5 6
```

###### Déclaration de la taille en octets

À tout moment, dans votre fichier, vous pouvez utiliser l'instruction

```
s 35223
```

qui déclare la taille actuelle du modèle (cumulée, en octets). Cette instruction permettra
plus tard d'évaluer le débit distortion au cours du temps de chargement. Par exemple

```
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 0.0 1.0 0.0
f 1 2 3
s 43
ef 1 2 2 3
s 48
```

déclare un modèle de 43 octets défini par un triangle. Vous pouvez ensuite
rajouter d'autres instructions pour modifier le modèle puis remettre une
instruction `s` pour spécifier la nouvelle taille.
