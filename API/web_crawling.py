""" Questo script implementa la Strategia A (BFS). Parte da una lista di "semi" (seed) e continua a esplorare i nodi vicini finché non raggiunge 
la soglia psicologica dei 10.000 nodi unici, salvando nodi e archi man mano che li scopre.
⚠️ Gestione dei Limiti API: Per raccogliere 10.000 nodi e i relativi archi, lo script dovrà fare migliaia di chiamate. 
Twitch consente circa 800 richieste al minuto. 
Il codice include un sistema automatico che rileva il blocco 429 (Too Many Requests) 
e mette in pausa lo script per i secondi necessari prima di ripartire, evitando il crash.""" 


import requests
import pandas as pd
import time

CLIENT_ID = "61a9s1rs82op20aovgbbllzr74m893"
CLIENT_SECRET = "3hzjktn9tlr84soz69be5k8okonha7"

# --- AUTENTICAZIONE ---
auth_url = "https://id.twitch.tv/oauth2/token"
auth_params = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "client_credentials"}
auth_response = requests.post(auth_url, data=auth_params)
ACCESS_TOKEN = auth_response.json()["access_token"]

headers = {
    "Client-Id": CLIENT_ID,
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

# --- IMPOSTAZIONI CRAWLER ---
TARGET_NODES = 10000  # Soglia obiettivo
# Usiamo i top streamer come "Semi" da cui far partire la ragnatela
queue = ["tumblurr", "pow3r", "grenbaud", "homyatol", "zanesecondo", "ilrossopiace"]
visited_logins = set()
discovered_nodes = {}  # ID -> {Label, Views}
edges_set = set()      # Insieme di tuple (Source, Target) togliendo i duplicati

print(f"🕸️ Avvio Crawler SNA su Twitch. Obiettivo: {TARGET_NODES} nodi.")

def safe_request(url):
    """Gestisce in automatico il Rate Limiting di Twitch"""
    while True:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return res.json()
        elif res.status_code == 429:
            # Legge l'header di Twitch per capire quanti secondi aspettare, default a 5
            wait_time = int(res.headers.get("Retry-After", 5))
            print(f"⏳ Rate limit raggiunto. Pausa forzata di {wait_time} secondi...")
            time.sleep(wait_time)
        else:
            return None

# --- LOOP DI ESPLORAZIONE GRAFO ---
while queue and len(discovered_nodes) < TARGET_NODES:
    current_login = queue.pop(0)
    if current_login in visited_logins:
        continue
    visited_logins.add(current_login)
    
    # 1. Recupera info sul nodo corrente
    user_data = safe_request(f"https://api.twitch.tv/helix/users?login={current_login}")
    if not user_data or not user_data.get("data"):
        continue
        
    user_info = user_data["data"][0]
    source_id = user_info["id"]
    source_label = user_info["display_name"]
    view_count = int(user_info["view_count"])
    
    # Registra il nodo se non esiste
    if source_id not in discovered_nodes:
        discovered_nodes[source_id] = {"ID": source_id, "Label": source_label, "Total_Views": view_count}
        
    # Mostra l'avanzamento ogni 100 nodi per non intasare il terminale
    if len(discovered_nodes) % 100 == 0:
        print(f"📊 Nodi raccolti: {len(discovered_nodes)}/{TARGET_NODES} | Archi: {len(edges_set)}")

    # 2. Espansione: Trova i vicini tramite i Team
    teams_data = safe_request(f"https://api.twitch.tv/helix/teams/channel?broadcaster_id={source_id}")
    if teams_data and "data" in teams_data:
        for team in teams_data["data"]:
            team_id = team["id"]
            
            # Ottieni i dettagli del team per estrarre i membri
            team_details = safe_request(f"https://api.twitch.tv/helix/teams?id={team_id}")
            if team_details and "data" in team_details and len(team_details["data"]) > 0:
                users_in_team = team_details["data"][0]["users"]
                
                for member in users_in_team:
                    target_id = member["user_id"]
                    target_login = member["user_login"]
                    target_name = member["user_name"]
                    
                    # Se non lo abbiamo mai analizzato, lo aggiungiamo alla coda di esplorazione
                    if target_login not in visited_logins and target_login not in queue:
                        queue.append(target_login)
                    
                    # Crea l'arco (evitando loop su se stessi)
                    if target_id != source_id:
                        edges_set.add((source_id, target_id))
                        # Inseriamo preventivamente il nodo target nel dizionario per non perdere le label
                        if target_id not in discovered_nodes:
                            discovered_nodes[target_id] = {"ID": target_id, "Label": target_name, "Total_Views": 0}

# --- SALVATAGGIO DEI DATI MASSIVI ---
print("\n💾 Raggiunto il target o esaurita la coda. Salvataggio in corso...")

df_nodes = pd.DataFrame(discovered_nodes.values())
df_edges = pd.DataFrame(list(edges_set), columns=["Source", "Target"])
df_edges["Type"] = "Directed"
df_edges["Weight"] = 1

# Filtro di sicurezza: tiene solo gli archi i cui nodi sono effettivamente censiti
df_edges = df_edges[df_edges["Source"].isin(df_nodes["ID"]) & df_edges["Target"].isin(df_nodes["ID"])]

df_nodes.to_csv("/Users/gagliardi_pietro/Desktop/SOCIAL NETWORK ANALYSIS/twitch_nodes_10k.csv", index=False)
df_edges.to_csv("/Users/gagliardi_pietro/Desktop/SOCIAL NETWORK ANALYSIS/twitch_edgelist_10k.csv", index=False)

print(f"✅ Processo terminato con successo!")
print(f"Nodi totali esportati: {len(df_nodes)}")
print(f"Archi totali esportati: {len(df_edges)}")



