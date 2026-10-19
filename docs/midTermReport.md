---
title: |
    **ProgMesh group -- Mid Term Report**
subtitle: |
    Subject understanding, Project architecture and management.
author:
  - Elias Berlioz
  - Alice Dissoubray
  - Iman-norr Draou
  - Cyrian Ragot
  - Yan Rabefaniraka
date: "2026-10-23"
fontsize: 12pt
colorlinks: true
documentclass: report
csl: format.csl
nocite: '@*'
header-includes:
  - \usepackage{fvextra}
  - \DefineVerbatimEnvironment{Highlighting}{Verbatim}{linenos,breaklines,commandchars=\\\{\}}
  - \usepackage{float}
  - \usepackage{subfig}
  - \floatplacement{figure}{H}
output: pdf_document
toc: true
number_sections: true
fig_caption: true
papersize: a4
geometry: margin=1.125cm
---

**Note**:

- Ce document a été compilé en pdf en utilisant *pandoc* comme suit:

```bash
cd docs
pandoc midTermReport.md -o midTermReport.pdf --pdf-engine=xelatex --citeproc --highlight-style=tango
```

- L'IA Générative a pu y être utilisée pour vérifier la grammaire et la cohérence des liaisons entre les différents propos (Le Stream of Conciousness prend vite de la place).

# Papiers fournis

## Principe initial du Progressive Mesh

Notre équipe base principalement son projet de transmission progressive de mailles 3D sur l'historique papier "**Progressive Meshes**" de Hugues Hoppe. Il y propose la simplification de maille 3D par "contractions" d'arêtes (*Edge Collapse*), chacune stockée sous forme d'enregistrement réversible (*Vertex Split*). Cela permet la transmission progressive des mesh, selon différents niveaux de détail (*LOD*). En clair, on nous donne un algorithme reversible de simplification d'un maillage 3D (Réduction de son niveau de détail par Edge Collapse) à plusieurs échelles, nous permettant donc de streamer à différents degrés de détails l'objet (Retrouver des niveaux de détail plus élevés avec le Vertex Split).

## Travaux connexes

Trois propositions d'implémentation supplémentaires, plus ou moins proche des "Progressive Meshes" nous sont fournies selon les priorités choisies:

### Multiresolution Streaming Mesh with Shape Preserving and QoS-like Controlling

- "Ce papier se concentre sur l'ajout des *progressive meshes* à la transmission Internet, avec des simplifications non destructives des modèles avec un système de "*QoS*" qui priorise et contrôle le streaming du maillage selon le réseau. En clair, leur papier vise à proposer un ajustement du niveau de détail selon le débit et la latence du "client". On a notamment trouvé intéressant dans ce papier la structure de données "Half Edge Collapse" qui vient compléter l'*Edge Collapse* de Hoppe. C'est cette dernière qui permet un meilleur contrôle topologique lors des contractions.

- Le **mécanisme de "priorité"** du papier se base sur le **poids** des arêtes, défini comme la différences des attributs scalaires $S$ (dont vecteurs normaux) entre ses sommets. Cette méthode va donc mettre dans une queue l'ordre de contraction des arêtes selon le plus faibles poids.

- Complexité à vérifier mais je crois me souvenir aue c'est $O(n \log n)$.

### Surface Simplification Using Quadric Error Metrics

- Ce papier propose comme mesure d'énergie pour les "Edge Collapses" une **métrique quadratique** non destructive, qui conserve bien la géométrie globale. Cette priorité veut simplifier statistiquement la recherche de la prochaine contraction par approximations rapides, en agrégeant les *quadriques* des sommets contractés. Le papier ne propose cependant pas de technique de streaming de mesh, nous offrant avant tout un critère priorité supplémentaire dans notre pipeline.

- Plus spécifiquement, le **mécanisme de "priorité"** du papier calcule l'erreur quadratique à un sommet $v$, $E(v) = v^T Q v$, où $Q = \sum K_p$ est la **quadrique**, une matrice $4 \times 4$ associée à $v$, avec $K_p$ sont les matrices des plans adjacents à $v$. Ainsi, il évalue une contraction de sommets $(v_1, v_2)$ par sa quadrique $Q_{1/2} = Q_1 + Q_2$. La priorité des contractions se trouve alors par le classement croissant des erreurs de contraction: $E = v_{opt}^T (Q_1 + Q_2) v_{opt}$.

- Pareil à voir mais logiquement c'est du $O(n \log n)$.

### Mesh Saliency Analysis via Local Curvature Entropy

- Ce papier propose une mesure de **saillance** des sommets, *i.e* une recherche de zones d'intérêts, basée sur l'entropie de la courbure locale (entropie de Shannon). En effet, une zone saillante est à forte variation géométrique locale, càd à haute Entropie de SHannon. Cette méthode veut donc identifier les régions visuellement importantes d'un maillage comme **métrique de priorité** pour les *Edge Collapses*, en simplifiant agressivement les zones peu "saillantes" et en préservant le détail des zones saillantes. Le papier ne propose pas non plus de technique de streaming, mais offre un critère complémentaire à la métrique géométrique de QEM, directement intégrable dans notre pipeline.

## Création d'un modèle progressif au format obja

Notre objectif est donc d'augmenter la portée d'un mesh 3D (OBJ) en lui faisant passer au format OBJA, fait pour le streaming. Il s'agit donc plus d'un flux d'instructions à interpréter et appliquer côté client afin d'effectuer l'affichage progressif du modèle 3D.

# Architecture de notre implémentation

Notre projet est structuré comme suit:

## dataflow

TODO

## dependecies

TODO

## testing (unit)

TODO

## testing global

TODO

# Point organisationnel

TODO

## Répartition des tâches

refer to github

## Plannification de l'avancée

TODO
# Conclusion mid-terms

En somme, ...
