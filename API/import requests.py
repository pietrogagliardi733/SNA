import requests
import pandas as pd
import time
import os

# --- INSERISCI LE TUE CREDENZIALI FUNZIONANTI ---
CLIENT_ID = "61a9s1rs82op20aovgbbllzr74m893"
CLIENT_SECRET = "3hzjktn9tlr84soz69be5k8okonha7"

# --- STEP 1: AUTENTICAZIONE OAUTH2 ---
auth_url = "https://id.twitch.tv/oauth2/token"
auth_params = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "client_credentials"}
auth_response = requests.post(auth_url, data=auth_params)
ACCESS_TOKEN = auth_response.json()["access_token"]

headers = {
    "Client-Id": CLIENT_ID,
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

# --- STEP 2: CARICAMENTO DEL DATASET ESISTENTE ---
input_path = "/Users/gagliardi_pietro/Desktop/SOCIAL NETWORK ANALYSIS/twitch_nodes_10k_enriched.csv"
df_nodes = pd.read_csv(input_path)

print(f"📊 Dataset caricato correttamente. Inizio recupero follower per {len(df_nodes)} nodi...")

# Se hai interrotto lo script e lo riavvii, questo dizionario evita di rifare chiamate già fatte
followers_dict = {}

# Se esiste già una colonna dei follower parziale, la carichiamo per non perdere il lavoro
if "Total_Followers" in df_nodes.columns:
    followers_dict = df_nodes.set_index("ID")["Total_Followers"].to_dict()

# --- STEP 3: LOOP DI RICHIESTA INDIVIDUALE ---
start_time = time.time()

for idx, row in df_nodes.iterrows():
    node_id = int(row["ID"])
    
    # Salta se lo abbiamo già scaricato in una sessione precedente
    if node_id in followers_dict and followers_dict[node_id] > 0:
        continue
        
    url = f"https://api.twitch.tv/helix/channels/followers?broadcaster_id={node_id}"
    
    while True:
        res = requests.get(url, headers=headers)
        
        if res.status_code == 200:
            # Estraiamo il campo 'total' dal JSON di Twitch
            total_followers = res.json().get("total", 0)
            followers_dict[node_id] = total_followers
            break
        elif res.status_code == 429:
            # Gestione dinamica dei limiti di Twitch
            wait_time = int(res.headers.get("Retry-After", 2))
            print(f"⏳ Rate limit raggiunto. Pausa di {wait_time} secondi... (Nodi fatti: {idx})")
            time.sleep(wait_time)
        else:
            print(f"⚠️ Impossibile recuperare dati per ID {node_id}. Status: {res.status_code}")
            followers_dict[node_id] = 0
            break

    # Stampa il progresso ogni 250 nodi per monitorare l'avanzamento
    if idx % 250 == 0 and idx > 0:
        elapsed = time.time() - start_time
        print(f"🔄 Sincronizzati {idx}/{len(df_nodes)} nodi... Tempo trascorso: {elapsed/60:.1f} minuti")
        
        # Salvataggio di backup intermedio ogni 250 record per sicurezza
        df_nodes["Total_Followers"] = df_nodes["ID"].map(followers_dict).fillna(0).astype(int)
        df_nodes.to_csv(input_path, index=False)

# --- STEP 4: MAPPATURA FINALE E PULIZIA ---
df_nodes["Total_Followers"] = df_nodes["ID"].map(followers_dict).fillna(0).astype(int)

# Rimuoviamo la vecchia colonna Total_Views inutile
if "Total_Views" in df_nodes.columns:
    df_nodes = df_nodes.drop(columns=["Total_Views"])

# Salvataggio definitivo del file sul Desktop
output_path = "/Users/gagliardi_pietro/Desktop/SOCIAL NETWORK ANALYSIS/twitch_nodes_10k_final.csv"
df_nodes.to_csv(output_path, index=False)

print(f"\n✅ Arricchimento completato! I follower storici sono pronti.")
print(f"💾 File finale salvato in: {output_path}")