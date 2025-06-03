import pandas as pd
from pathlib import Path
from kiparla_tools import data
from kiparla_tools import serialize
from kiparla_tools import dataflags as df 


# definisco cartella da cui prendere i file
DATA_DIR = Path("/Users/martinasimonotti/asr-assisted-transcription/asr-assisted-transcription/data/output")
# DESCRIPTION_PATH = Path("data/data_description.csv")

#desc = pd.read_csv(DESCRIPTION_PATH, sep="\t")
#desc = desc[desc["Tipo"].isin(["From-Scratch", "Whisper-Assisted"])] 
#file2tipo = dict(zip(desc["NomeFile"], desc["Tipo"]))

# definisco la funzione per estrarre annotazioni/fenomeni metalinguistici da .conll
def transcriber_behavior(file_path):
    transcript = serialize.transcript_from_csv(file_path)

    counts = {
        "File": file_path.stem,
        "Pauses": 0,
        "Prolongations": 0,
        "Intonation Patterns": 0,
        "Interruptions": 0,
        "Pace": 0,
        "Overlaps": 0,
        "Guesses": 0,
        "Unknown": 0,
        "Metalinguistic Total": 0,
    }
     
    #for token in df["span"]:
        # if pd.isna(token):
           #   continue
         
         #if token == "{P}":
            # counts["Pauses"] +=1 # aggiunge pause
        
        #if ":" in token:
         #    counts["Prolongations"] +=1 # aggiunge prolongamenti
        #
            #token in {",", ".", "?"}:
    #         counts["Intonation Patterns"] +=1 #aggiunge pattern intonativi
        
    #      if token.startswith("°") and token.endswith("°"):
    #          counts["Volume"] +=1 # aggiunge volume basso
    #      elif token.isupper():
    #          counts["Volume"] +=1  # aggiunge volume alto
        
    #      if token.endswith("-"):
    #         counts["Interruptions"] +=1 # aggiunge interruzioni
        
    #      if (token.startswith(">") and token.endswith("<")) or (token.startswith("<") and token.endswith(">")):
    #         counts["Pace"] += 1
         
    #      if token.startswith("[") and token.endswith("]"):
    #          counts["Overlaps"] += 1
        
    #      if token.startswith("(") and token.endswith(")"):
    #          counts["Hypotheses"] += 1
         
    #      if token == "x":
    #          counts["Incomprehensible"] += 1
             
    #      if token.startswith("{") and token.endswith("}") and not token=="{P}":
    #          counts["Metalinguistic"] += 1
             
    # transcriber = file_path.stem.split("_")[-1]
    # filetype = file2tipo.get(file_path.stem, "UNKNOWN")
    
    for tu in transcript.transcription_units:
        for token in tu.tokens.values():
            if df.tokentype.shortpause in token.token_type:
                counts["Pauses"] +=1
            if token.prolongations:
                counts["Prolongations"] +=1
            if token.intonation_pattern is not None:
                counts["Intonation Patterns"] +=1
            if token.interruption:
                counts["Interruptions"] += 1
            # if token.slow_pace or token.fast_pace:
            #     counts["Pace"] +=1
            #     print("Pace:", token.slow_pace, token.fast_pace)
            # if token.overlaps:
            #     counts["Overlaps"] +=1
            # if token.guesses:
            #     counts["Guesses"] +=1
            if df.tokentype.unknown in token.token_type:
                counts["Unknown"] +=1
            if df.tokentype.metalinguistic in df.tokentype:
                counts["Metalinguistic Total"] +=1
        
        # counting spans
        counts["Pace"] += len(tu.fast_pace_spans) + len(tu.slow_pace_spans)
        counts["Overlaps"] += len(tu.overlapping_spans)
        counts["Guesses"] += len(tu.guessing_spans)
    
    return counts
    
    
    # return {
    #     "Trascrittore": transcriber,
    #     "Tipo": filetype,
    #     **{k: v for k, v in counts.items() if k not in ["File"]}
    # }

# elaborare file

behavior_count = []

for file in DATA_DIR.glob("*.tus.csv"):
    if file.stem.startswith("03_"):
        continue # esclude revised
    behavior_count.append(transcriber_behavior(file))

df = pd.DataFrame(behavior_count)
df["Trascrittore"] = df["File"].apply(lambda x: x.replace(".tus", "").split("_")[-1])
df["Tipo"] = df["File"].apply(lambda x: "From-Scratch" if x.startswith("01") else "Whisper-Assisted")


aggregated_file = df.groupby(["Trascrittore", "Tipo"]).sum(numeric_only=True).reset_index()
aggregated_file.to_csv("data/transcribers_behavior.csv", index=False)

# # aggregare per trascrittore e tipo file   
# df = pd.DataFrame(behavior_count)  
# df_grouped = df.groupby(["Trascrittore", "Tipo"], as_index=False).sum
# #print(df_grouped)


# df_grouped.to_csv("data/transcribers_behavior.csv", index=False)

