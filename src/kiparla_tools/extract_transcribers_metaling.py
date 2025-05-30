import pandas as pd
from pathlib import Path


# definisco cartella da cui prendere i file
DATA_DIR = Path("/Users/martinasimonotti/asr-assisted-transcription/asr-assisted-transcription/data/output")
DESCRIPTION_PATH = Path("data/data_description.csv")

desc = pd.read_csv(DESCRIPTION_PATH, sep="\t")
desc = desc[desc["Tipo"].isin(["From-Scratch", "Whisper-Assisted"])] 
file2tipo = dict(zip(desc["NomeFile"], desc["Tipo"]))

# definisco la funzione per estrarre annotazioni/fenomeni metalinguistici da .conll
def transcriber_behavior(file_path):
    df = pd.read_csv(file_path, sep="\t")

    counts = {
        "File": file_path.stem,
        "Pauses": 0,
        "Prolongations": 0,
        "Intonation Patterns": 0,
        "Volume": 0,
        "Interruptions": 0,
        "Pace": 0,
        "Overlaps": 0,
        "Hypotheses": 0,
        "Incomprehensible": 0,
        "Metalinguistic": 0,
    }
     
    for token in df["span"]:
         if pd.isna(token):
              continue
         
         if token == "{P}":
             counts["Pauses"] +=1 # aggiunge pause
        
         if ":" in token:
             counts["Prolongations"] +=1 # aggiunge prolongamenti
        
         if token in {",", ".", "?"}:
            counts["Intonation Patterns"] +=1 #aggiunge pattern intonativi
        
         if token.startswith("°") and token.endswith("°"):
             counts["Volume"] +=1 # aggiunge volume basso
         elif token.isupper():
             counts["Volume"] +=1  # aggiunge volume alto
        
         if token.endswith("-"):
            counts["Interruptions"] +=1 # aggiunge interruzioni
        
         if (token.startswith(">") and token.endswith("<")) or (token.startswith("<") and token.endswith(">")):
            counts["Pace"] += 1
         
         if token.startswith("[") and token.endswith("]"):
             counts["Overlaps"] += 1
        
         if token.startswith("(") and token.endswith(")"):
             counts["Hypotheses"] += 1
         
         if token == "x":
             counts["Incomprehensible"] += 1
             
         if token.startswith("{") and token.endswith("}") and not token=="{P}":
             counts["Metalinguistic"] += 1
             
    transcriber = file_path.stem.split("_")[-1]
    filetype = file2tipo.get(file_path.stem, "UNKNOWN")
    
    return {
        "Trascrittore": transcriber,
        "Tipo": filetype,
        **{k: v for k, v in counts.items() if k not in ["File"]}
    }

# elaborare file

behavior_count = []

for file in DATA_DIR.glob("*.conll"):
    filename = file.stem
    if filename.startswith("03_"):
        continue # esclude revised
    behavior_count.append(transcriber_behavior(file))

# aggregare per trascrittore e tipo file   
df = pd.DataFrame(behavior_count)  
df_grouped = df.groupby(["Trascrittore", "Tipo"], as_index=False).sum()
#print(df_grouped)


df_grouped.to_csv("data/transcribers_behavior.csv", index=False)