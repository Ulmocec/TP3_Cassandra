# Livrable TP3 - Cluster Cassandra : réplication et tolérance aux pannes

## Q1 - Après démarrage des 3 nœuds

- Nœuds présents : 3 (cass1, cass2, cass3)
- États : cass1 UN, cass2 UN, cass3 DN (Down/Normal) au moment de la vérification (puis UN après redémarrage)
- Datacenter : dc1
- Racks : cass1→rack1, cass2→rack2, cass3→rack3

Vérif : `nodetool status` → 3 nœuds dans dc1, répartis sur 3 racks distincts.

## Q2 - Architecture

Cluster : tp2-cluster (ensemble logique des nœuds Cassandra).  
Datacenter (dc1) : groupe logique de nœuds (tolérance aux pannes/failover par DC).  
Rack : sous-groupe dans un DC (contrôle placement réplication/anti-affinity).  
Node : instance Cassandra (cass1/cass2/cass3).

Architecture obtenue : cluster tp2-cluster, dc1, racks rack1/rack2/rack3, 3 nœuds opérationnels (UN) après redémarrage complet.

## Q3 - Table métier (TP2 réutilisée)

- Keyspace : velib_cluster
- Table : stations_velib
- Colonnes principales : station_id (text), nom_station (text), capacite (int), vatiques_disponibles (int), bornes_disponibles (int), derniere_mise_a_jour (timestamp)
- Partition key : station_id (PRIMARY KEY = (station_id))
- Clustering key : aucune

Données : 1519 récupérées, 1240 lignes présentes (upsert sur PK).

## Q4 - RF = 3

RF = 3 signifie : pour chaque partition de la table, Cassandra réplique les données sur **3 nœuds distincts** dans le datacenter dc1.

Diff :  
- Partitionnement = distribue les partitions (PK → hash → token) sur les nœuds responsables (placement).  
- Réplication = crée des **copies** (réplicas) de chaque partition sur d'autres nœuds pour tolérance aux pannes.

## Q5 - Chemin d'une donnée

PK → hash (Murmur3Partitioner) → token → nœud(s) responsable(s) (coordinator/token range owner) → réplicas déterminés par NetworkTopologyStrategy(dc1:3) (choisis sur différents nœuds/racks selon stratégie) pour assurer redondance.

## Q6 - Niveaux de cohérence (RF=3)

Lecture sur station_id='3004' :

| Niveau | Réplicas requis (RF=3) | Résultat (3 nœuds UN) | Garantie | Dispo |
|---|---:|---|---|---|
| ONE | 1 | OK | Lecture depuis au moins 1 réplica (peut être ancienne si réparation différée) | Max |
| QUORUM | 2 (floor(3/2)+1) | OK | Lecture cohérente entre majorité (2) → équilibre | Moyenne |
| ALL | 3 | OK | Lecture depuis **tous** les réplicas → cohérence forte | Min (sensible aux pannes) |

## Q7 - Panne de cass3

Après `docker stop cass3` :  
- cass3 → DN (Down/Normal), Unreachable  
- cass1 → UN, cass2 → UN  
- Nœuds disponibles : **2** sur 3

## Q8 - Lectures pendant la panne

Même station ('3004'), RF=3, 2 nœuds dispo :

| Niveau | Requis | Résultat | Explication |
|---|---:|---|---|
| ONE | 1 | OK | Suffisant (≥1 réplica vivante atteignable) |
| QUORUM | 2 | OK | 2 nœuds UN disponibles → quorum atteint (majorité des réplicas requis atteinte) |
| ALL | 3 | **Échec (NoHostAvailable / Cannot achieve consistency level ALL)** | Nécessite 3 réplicas vivants, seulement 2 dispo → impossible d'atteindre ALL

Lien : **réplicas requis (CL) + nœuds vivants (disponibles)**. Avec RF=3, QUORUM=2 tolère 1 panne (reste ≥2), ALL tolère 0. ONE tolère 2.

## Q9 - Redémarrage de cass3

Après `docker start cass3` + ~60s : cass3 repasse à **UN (Up/Normal)**. Les 3 nœuds sont à nouveau opérationnels (dc1 complet). Cassandra le réintègre au cluster (join/streaming) automatiquement.

## Q10 - Après redémarrage

Lectures à nouveau possibles à **ALL** (retour OK).  
Scénario : données répliquées sur 3 nœuds (RF=3). Panne de cass3 → 2 dispo (lecture toujours accessible selon CL). Retour de cass3 → réintégration + réplication/équilibrage (données déjà présentes sur réplicas vivants, streaming/hints selon besoin) → cluster stable, données accessibles à tous les CL testés.
