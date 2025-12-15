# 5G or not 5G ?

Vous venez d'être recruté·e par un opérateur téléphonique qui souhaite déployer son réseau sur une nouvelle ville. Votre mission : installer des antennes pour couvrir tous les bâtiments de la zone, tout en minimisant les coûts d'installation.

Le défi ? La population des bâtiments varie selon l'heure de la journée : bureaux bondés en journée mais déserts la nuit, immeubles résidentiels pleins la nuit mais vides le jour... Et vos antennes doivent pouvoir gérer le pic de fréquentation !

Chaque jeu de données vous rapportera jusqu'à 1 million de points pour le classement (voir détail plus bas).

---

## Entrée

Chaque ville est modélisée par un ensemble de bâtiments, chacun ayant des coordonnées et une population variable selon trois périodes de la journée.

Le format JSON des fichiers fournis est détaillé ci-dessous :

```json
{
    "comment": "Exemple de ville",
    "buildings": [
        {
            "id": 0,
            "x": 100,
            "y": 250,
            "populationPeakHours": 500,      // Population pendant les heures pleines
            "populationOffPeakHours": 150,   // Population pendant les heures creuses
            "populationNight": 50            // Population pendant la nuit
        },
        {
            "id": 1,
            "x": 300,
            "y": 100,
            "populationPeakHours": 80,
            "populationOffPeakHours": 200,
            "populationNight": 450
        },
        ...
    ]
}
```

**Notes importantes :**
- Toutes les coordonnées sont des **nombres entiers positifs**
- Chaque bâtiment doit être relié à **une et une seule** antenne
- L'antenne choisie doit pouvoir gérer le **pic maximum** de population du bâtiment sur les trois périodes

---

## Antennes disponibles

Vous disposez de **4 types d'antennes** avec des caractéristiques différentes :

| Type | Portée | Capacité | Coût (sur bâtiment) | Coût (hors bâtiment) |
|------|--------|----------|---------------------|----------------------|
| **Nano** | 50 | 200 | 5 000 € | 6 000 € |
| **Spot** | 100 | 800 | 15 000 € | 20 000 € |
| **Density** | 150 | 5 000 | 30 000 € | 50 000 € |
| **MaxRange** | 400 | 3 500 | 40 000 € | 50 000 € |

Ce catalogue d'antennes est le même pour tous les jeux de données, et il n'y a pas de limite sur le nombre d'antennes de chaque type.

**Contraintes de placement :**
- Une antenne peut être placée **n'importe où** sur la carte, aux coordonnées entières (x, y)
- Si une antenne est placée **exactement sur les coordonnées d'un bâtiment**, elle coûte moins cher (prix "sur bâtiment")
- Plusieurs antennes peuvent être placées au même endroit (y compris sur un même bâtiment)

**Contraintes de couverture :**
- Un bâtiment en (x_b, y_b) peut être relié à une antenne en (x_a, y_a) si la **distance euclidienne** entre les deux est inférieure ou égale à la portée de l'antenne : √((x_a - x_b)² + (y_a - y_b)²) ≤ portée
- La **somme des populations maximales** de tous les bâtiments reliés à une antenne ne doit pas dépasser sa capacité (le maximum étant pris sur les 3 périodes pour chaque bâtiment)

---

## Sortie

Pour chaque ville, vous devez soumettre votre solution sous la forme d'un fichier JSON contenant la liste des antennes installées.

```json
{
    "antennas": [
        {
            "type": "Spot",           // Type d'antenne : "Nano", "Spot", "Density" ou "MaxRange"
            "x": 150,                  // Coordonnée x (entier)
            "y": 200,                  // Coordonnée y (entier)
            "buildings": [0, 3, 7]     // Liste des identifiants des bâtiments reliés à cette antenne
        },
        {
            "type": "Nano",
            "x": 100,
            "y": 250,
            "buildings": [1]
        },
        ...
    ]
}
```

**Important :** Chaque bâtiment doit apparaître dans **exactement une** liste de bâtiments : il n'est pas possible de répartir la population d'un bâtiment sur plusieurs antennes.

---

## Calcul du score

Votre objectif est de **minimiser le coût total** de l'installation des antennes.

Le score de votre solution est égal à la **somme des coûts** de toutes les antennes installées.

Si votre solution ne respecte pas les contraintes (bâtiment hors de portée, capacité dépassée, bâtiment non couvert ou couvert plusieurs fois), elle sera considérée comme invalide et ne rapportera aucun point.

---

## Classement global

Pour chaque jeu de données, le joueur avec la meilleure solution (coût le plus bas) remporte 1 million de points de classement. Le score des autres joueurs est calculé en fonction de la solution du meilleur joueur avec la formule suivante :

```
1 000 000 * score_meilleur / score_joueur
```

Par exemple, si votre solution coûte deux fois plus cher que celle du meilleur adversaire, votre score sur ce jeu de données sera de 500 000 points.

Le classement est déterminé en fonction du total de points obtenus. Vous pouvez soumettre autant de fois que vous le souhaitez, seule votre meilleure soumission sur chaque jeu de données sera prise en compte.
