# Compte-rendu TP3 - Cluster Cassandra : réplication et tolérance aux pannes

## 1) Architecture du cluster

- Cluster : tp2-cluster
- Datacenter : dc1
- Racks : rack1 (cass1), rack2 (cass2), rack3 (cass3)
- Nœuds : 3 (cass1,cass2,cass3). Après mise en route complète : UN/UN/UN.

## 2) Table métier du TP2

- Keyspace : velib_cluster (NetworkTopologyStrategy, dc1:3)
- Table : stations_velib
- Colonnes : station_id (text), nom_station (text), capacite (int), vatiques_disponibles (int), bornes_disponibles (int), derniere_mise_a_jour (timestamp)
- Partition key : station_id
- Clustering key : aucune
- Données : 1240 lignes

## 3) Replication Factor (RF)

RF = 3 (dc1) : chaque partition répliquée sur 3 nœuds distincts du DC.
- Partitionnement = PK → hash/token → nœud responsable
- Réplication = copies sur autres nœuds (tolérance aux pannes)

Chemin : PK → Murmur3 → token → nœud responsable + réplicas (NetworkTopologyStrategy dc1:3).

## 4) Tests de cohérence : ONE / QUORUM / ALL

Station : station_id='3004' (RF=3)

| CL | Requis | 3 nœuds UN | Garantie | Dispo |
|---|---:|---|---|---|
| ONE | 1 | OK | ≥1 réplica | Max |
| QUORUM | 2 | OK | majorité (2) | Moyenne |
| ALL | 3 | OK | tous les réplicas | Min |

## 5) Simulation de panne

`docker stop cass3` → cass1 UN, cass2 UN, cass3 DN (Unreachable). Nœuds disponibles : 2/3.

## 6) Résultats pendant la panne

| CL | Requis | Résultat | Observations |
|---|---:|---|---|
| ONE | 1 | OK | fonctionne |
| QUORUM | 2 | OK | quorum atteint (2/3) |
| ALL | 3 | ÉCHEC (NoHostAvailable / Cannot achieve consistency level ALL) | impossible (2 dispo < 3) |

## 7) Redémarrage de cass3

`docker start cass3` → ~60s, cass3 UN. Réintégration automatique (join/streaming). Cluster 3 UN.

## 8) Vérification finale des données

Lectures OK y compris ALL. Données accessibles. Réplicas se rééquilibrent au retour.

## 9) Observations et conclusions

Observations : avec RF=3, panne partielle tolérée selon CL. QUORUM garde disponibilité avec 1 panne ; ALL strict. Retour auto.

Conclusion : réplication + cohérence choisie selon besoin dispo/cohérence. RF=3 permet continuité (ONE/QUORUM) malgré cass3 down.

## 10) Q11 - Pourquoi la réplication permet la continuité ?

Chaque partition existe sur 3 nœuds. Si 1 tombe, d'autres réplicas restent disponibles. Selon CL requis, quorum peut être atteint → requêtes réussissent. Au retour, streaming/hints resynchronisent cass3.
