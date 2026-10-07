#!/usr/bin/env python3
import os
from datetime import datetime
import requests
from cassandra.cluster import Cluster

# Connexion au cluster Cassandra
cluster = Cluster(['127.0.0.1'], port=9042)
session = cluster.connect('velib_cluster')

# API OpenData Paris - Disponibilité en temps réel
DATASET = "velib-disponibilite-en-temps-reel"
BASE_URL = "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/{}/records"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def fetch_all():
    results = []
    offset = 0
    limit = 100
    while True:
        response = requests.get(
            BASE_URL.format(DATASET), params={"limit": limit, "offset": offset}
        )
        response.raise_for_status()
        data = response.json()
        records = data.get("results", [])
        results.extend(records)
        if not records or len(results) >= data.get("total_count", 0):
            break
        offset += limit
    return results

def main():
    print("Récupération des données Vélib' depuis l'API OpenData Paris...")
    os.makedirs(DATA_DIR, exist_ok=True)
    
    records = fetch_all()
    print(f"Nombre total de stations récupérées: {len(records)}")
    
    # Sauvegarde pour référence
    import json
    path = os.path.join(DATA_DIR, "stations_disponibilite.json")
    with open(path, "w") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"Données sauvegardées dans {path}")
    
    print("Insertion dans Cassandra (velib_cluster.stations_velib)...")
    inserted = 0
    for record in records:
        station_id = str(record.get('stationcode'))
        nom_station = record.get('name')
        capacite = int(record.get('capacity', 0))
        vatiques_disponibles = int(record.get('numbikesavailable', 0))
        bornes_disponibles = int(record.get('numdocksavailable', 0))
        update_str = record.get('duedate')

        try:
            if update_str:
                # Gérer format ISO8601 avec Z
                if update_str.endswith('Z'):
                    update_str = update_str.replace('Z', '+00:00')
                derniere_mise_a_jour = datetime.fromisoformat(update_str)
            else:
                derniere_mise_a_jour = datetime.now()
        except Exception:
            derniere_mise_a_jour = datetime.now()

        query = """
            INSERT INTO stations_velib (station_id, nom_station, capacite, vatiques_disponibles, bornes_disponibles, derniere_mise_a_jour)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        session.execute(query, (
            station_id,
            nom_station,
            capacite,
            vatiques_disponibles,
            bornes_disponibles,
            derniere_mise_a_jour,
        ))
        inserted += 1

    print(f"Insertion terminée: {inserted} enregistrements insérés avec succès !")
    cluster.shutdown()

if __name__ == "__main__":
    main()