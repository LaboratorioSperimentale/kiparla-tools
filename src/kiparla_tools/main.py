import kiparla_tools.data as data
import kiparla_tools.serialize as serialize
import kiparla_tools.alignment as alignment
import pandas as pd
import os

# Funzione che apre tutti i file transcript e genera un file di output per ognuno
def process_all_transcripts(input_dir="data/csv_puliti", output_dir="data/output"):
	transcripts_dict = {}

	if not os.path.exists(output_dir): # non abbiamo cartella di output, quindi la creiamo
		os.makedirs(output_dir)

	# Iterare attraverso tutti i file .csv
	for filename in os.listdir(input_dir):
		if filename.endswith(".csv"):
			transcript_name = filename.replace(".csv", "") # rimuove .csv (prendendo come esempio 01_ParlaBOA_E)
			transcript = data.Transcript(transcript_name)

			file_path = os.path.join(input_dir, filename)
			print(f"Processing {filename}")

			for tu_id, speaker, start, end, duration, annotation in serialize.read_csv(file_path):
				new_tu = data.TranscriptionUnit(tu_id, speaker, start, end, duration, annotation)
				transcript.add(new_tu)

			transcript.sort()
			transcript.create_turns()
			transcript.find_overlaps(duration_threshold=0.1)

			for tu in transcript:
				tu.tokenize()

			transcript.check_overlaps()

			for tu in transcript:
				tu.add_token_features()

	# if not all(y for x, y in tu.errors.items()):
	# print(tu)
	# input()

#serialize.conversation_to_csv(transcript, "data/output/01_ParlaBOA_E.conll")

			output_filename = os.path.join(output_dir,f"{transcript_name}.conll")
			serialize.conversation_to_conll(transcript, output_filename)
			# serialize.conversation_to_csv(transcript, output_filename)
			serialize.conversation_to_linear(transcript, os.path.join(output_dir,f"{transcript_name}.tsv"))
			transcripts_dict[transcript_name] = transcript

	return transcripts_dict


# print(transcript)
# input()
# transcript.create_turns()

# print(len(transcript.turns))
# for turn in transcript.turns:
# 	print(turn.speaker, turn.start, turn.end, turn.transcription_units_ids)
# 	input()

# for tu in transcript:
# 	tu.strip_parentheses()
# 	tu.tokenize()
# 	# if not all(y for x, y in tu.errors.items()):
# 	print(tu)
# 	input()

#
# print(transcript)

# DONE: read transcript from csv
# DONE: remove spaces (see init function --- done)

###### PRELIMINAR CLEANING STEPS -- > AIM: get to tokenization with tagged information

# DONE: transform "pò" into "po'" (keep count)
# DONE: transform "perchè" into "perché" (keep count)
# DONE: remove initial and final pauses (keep count)
# DONE: remove symbols that are not part of jefferson (keep count)
# DONE: correct unbalanced parentheses (keep count)
# DONE: remove "=" symbol, transform into space (--manual??)
# TODO: check orphan symbols
# DONE: correzione spazi (keep count) ( es. sempre spazio prima di "{" e dopo"}" )
# DONE: tokenize




if __name__ == "__main__":
	import pathlib

	# for folder in ["KIP", "KIPasti", "ParlaBO", "ParlaTO"]:

	# 	for file in pathlib.Path(f"dati/{folder}_eaf").glob("*.eaf"):
	# 		basename = file.stem

	# 		serialize.eaf2csv(file, f"dati/{folder}_csv/{basename}.csv")


	# transcripts_list = process_all_transcripts("dati/sample_step1", "dati/output")
	# for file in pathlib.Path(f"dati/output").glob("*.tsv"):
	# 	serialize.csv2eaf(file, f"dati/output/{file.stem}.eaf")

	transcripts = process_all_transcripts("data/csv_puliti_demo", "data/output_sample")

	for i, t_a in enumerate(list(transcripts.keys())[:-1]):
		t_a_name = t_a.split("_")[1]
		for t_b in list(transcripts.keys())[i+1:]:
			t_b_name = t_b.split("_")[1]

			if t_a_name == t_b_name:
				tokens_a, tokens_b = alignment.align_transcripts(transcripts[t_a],
																transcripts[t_b])

				serialize.print_aligned(tokens_a, tokens_b, f"data/alignments/{t_a}_{t_b}.tsv")

	for file in pathlib.Path(f"data/output_sample").glob("*.tsv"):
		serialize.csv2eaf(file, f"data/output_sample/{file.stem}.eaf")

	# TODO: inserire dati trascrittori nelle statistiche

	serialize.print_full_statistics(transcripts, "data/output_sample/statistics.csv")
