# arrichimento della edgeslist per andare a prendere gli spettatori 

# --- STEP 1: AUTENTICAZIONE OAUTH2 ---
auth_url = "https://id.twitch.tv/oauth2/token"
auth_params = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "client_credentials"}
auth_response = requests.post(auth_url, data=auth_params)
ACCESS_TOKEN = auth_response.json()["access_token"]

headers = {
    "Client-Id": CLIENT_ID,
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

# --- STEP 2: CARICAMENTO DEI DATI ESISTENTI ---
nodes_path = "/Users/gagliardi_pietro/Desktop/SOCIAL NETWORK ANALYSIS/twitch_nodes_10k.csv"
df_nodes = pd.read_csv(nodes_path)

print(f"📊 Dataset caricato. Ottimizzazione di {len(df_nodes)} nodi in corso...")

node_ids = df_nodes["ID"].tolist()
real_views = {}
broadcaster_types = {}

# --- STEP 3: RICHIESTE IN BATCH (100 ALLA VOLTA) ---
batch_size = 100
for i in range(0, len(node_ids), batch_size):
    batch = node_ids[i:i+batch_size]
    
    # Concateniamo i parametri ID: id=123&id=456&id=789...
    id_params = "&".join([f"id={node_id}" for node_id in batch])
    url = f"https://api.twitch.tv/helix/users?{id_params}"
    
    res = requests.get(url, headers=headers)
    
    # Gestione preventiva del Rate Limit
    if res.status_code == 429:
        wait_time = int(res.headers.get("Retry-After", 5))
        print(f"⏳ Rate limit raggiunto. Pausa di {wait_time} secondi...")
        time.sleep(wait_time)
        res = requests.get(url, headers=headers)
        
    if res.status_code == 200:
        data = res.json().get("data", [])
        for user in data:
            u_id = int(user["id"])
            real_views[u_id] = int(user["view_count"])
            # Catalogazione del tipo di canale
            b_type = user["broadcaster_type"]
            broadcaster_types[u_id] = b_type if b_type != "" else "normal"
    else:
        print(f"⚠️ Errore nel batch che inizia da indice {i}: {res.status_code}")
        
    if (i // batch_size) % 10 == 0 and i > 0:
        print(f"🔄 Aggiornati {i}/{len(node_ids)} nodi...")

# --- STEP 4: MAPPATURA E SALVATAGGIO ---
df_nodes["Total_Views"] = df_nodes["ID"].map(real_views).fillna(0).astype(int)
df_nodes["Broadcaster_Type"] = df_nodes["ID"].map(broadcaster_types).fillna("unknown")

# Salviamo il file definitivo arricchito
output_path = "/Users/gagliardi_pietro/Desktop/SOCIAL NETWORK ANALYSIS/twitch_nodes_10k_enriched.csv"
df_nodes.to_csv(output_path, index=False)

print(f"\n✅ Arricchimento completato con successo!")
print(f"💾 Il file corretto è stato salvato in: {output_path}")