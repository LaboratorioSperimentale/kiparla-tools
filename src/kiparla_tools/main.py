import kiparla_tools.data as data
import kiparla_tools.serialize as serialize
import kiparla_tools.alignment as alignment
import itertools
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import os

from kiparla_tools.logging_utils import setup_logging

logger = logging.getLogger(__name__)
setup_logging(logger)

def process_transcript(filename, annotations,
					duration_threshold = 0.1, tiers_to_ignore = ["Traduzione"]):
	"""
	The function `process_transcript` reads a CSV file containing transcript data, creates transcription
	units, tokenizes them, and adds token features before returning the processed transcript.

	:param filename: name of the file that contains the transcript data to be processed.
	It is expected to be a file path pointing to the transcript file
	:param duration_threshold: minimum duration threshold for identifying overlapping transcription units in
	the transcript. If the duration of overlap between two transcription units is greater than or equal
	to the `duration_threshold`, they are considered as overlapping.
	:return: processed transcript object.
	"""
	# print(annotations)
	relations_to_ignore = []
	if "ignore" in annotations:
		for element in annotations["ignore"]:
			relations_to_ignore.extend(itertools.combinations([int(x) for x in element.split()], 2))
	logger.debug("Relations that will be ignored: %s", relations_to_ignore)

	transcript_name = filename.stem
	logger.debug("Initializing transcript %s", transcript_name)
	transcript = data.Transcript(transcript_name)

	for tu_id, speaker, start, end, duration, annotation in serialize.read_csv(filename):
		if speaker not in tiers_to_ignore:
			logger.debug("Initializing TU %s", tu_id)
			new_tu = data.TranscriptionUnit(tu_id, speaker, start, end, duration, annotation)
			transcript.add(new_tu)
		else:
			logger.info("Ignoring TU %s because of speaker %s", tu_id, speaker)

	logger.debug("Sorting transcript")
	transcript.sort()

	logger.debug("Finding overlaps")
	transcript.find_overlaps(duration_threshold=duration_threshold)

	logger.debug("Starting tokenization")
	for tu in transcript:
		tu.tokenize()

	logger.debug("Checking overlaps")
	transcript.check_overlaps(duration_threshold, relations_to_ignore)

	logger.debug("Adding token features")
	for tu in transcript:
		tu.add_token_features()

	return transcript


def align_transcripts(transcripts_dict, output_folder):
	for i, t_a in enumerate(list(transcripts_dict.keys())[:-1]):
		t_a_name = t_a.split("_")[1]
		for t_b in list(transcripts_dict.keys())[i+1:]:
			t_b_name = t_b.split("_")[1]

			if t_a_name == t_b_name:
				tokens_a, tokens_b = alignment.align_transcripts(transcripts_dict[t_a],
																transcripts_dict[t_b])

				serialize.print_aligned(tokens_a, tokens_b, output_folder.joinpath(f"{t_a}_{t_b}.tsv"))


# Funzione che apre tutti i file transcript e genera un file di output per ognuno
def process_all_transcripts(input_dir="data/curr_csv", output_dir="data/output"):
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
			transcript.find_overlaps(duration_threshold=0.1)

			for tu in transcript:
				tu.tokenize()

			transcript.check_overlaps()

			for tu in transcript:
				tu.add_token_features()

			output_filename = os.path.join(output_dir,f"{transcript_name}.vert.tsv")
			serialize.conversation_to_conll(transcript, output_filename)
			serialize.conversation_to_linear(transcript, os.path.join(output_dir,f"{transcript_name}.tsv"))
			transcripts_dict[transcript_name] = transcript

	return transcripts_dict

if __name__ == "__main__":
	import pathlib

	# output_dir = 'data/alignments'
	output_dir = 'data/alignments'
	if not os.path.exists(output_dir):
		os.makedirs(output_dir)

	transcripts = process_all_transcripts("data/curr_csv", "data/output_sample")

	for i, t_a in enumerate(list(transcripts.keys())[:-1]):
		t_a_name = t_a.split("_")[1]
		for t_b in list(transcripts.keys())[i+1:]:
			t_b_name = t_b.split("_")[1]

			if t_a_name == t_b_name:
				tokens_a, tokens_b = alignment.align_transcripts(transcripts[t_a],
																transcripts[t_b])

				serialize.print_aligned(tokens_a, tokens_b, f"data/alignments/{t_a}_{t_b}.tsv")

	for file in pathlib.Path(f"data/output_sample").glob("*.tsv"):
		serialize.csv2eaf(file, f"data/audio/{file.stem}.wav", f"data/output_sample/{file.stem}.eaf")

	serialize.print_full_statistics(transcripts, "data/output_sample/statistics.csv")
