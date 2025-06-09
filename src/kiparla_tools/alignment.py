"""Functions to handle sequence alignment"""
import collections
from sequence_align.pairwise import needleman_wunsch
#hirschberg
from typing import List
import csv
import re
import pathlib


from kiparla_tools import data

def align_transcripts(transcript_a:List[data.Token], transcript_b:List[data.Token]):
	"""
	The function `align_transcripts` aligns two transcripts by their tokens based on a minimum length
	and returns the aligned tokens for each transcript.

	:param transcript_a: List of Tokens from transcript A
	:type transcript_a: List[data.Token]
	:param transcript_b: List of Tokens from transcript B
	:type transcript_b: List[data.Token]
	:return: The function `align_transcripts` returns two lists: `aligned_tokens_a` and
	`aligned_tokens_b`, which contain aligned tokens from the input transcripts `transcript_a` and
	`transcript_b`, respectively.
	"""

	min_length = min(transcript_a.tot_length, transcript_b.tot_length)

	tokens_a = []
	tokens_b = []

	for tu_id, tu in transcript_a.transcription_units_dict.items():
		if tu.end <= min_length:
			for token_id, token in tu.tokens.items():
				tokens_a.append(token)

	for tu_id, tu in transcript_b.transcription_units_dict.items():
		if tu.end <= min_length:
			for token_id, token in tu.tokens.items():
				tokens_b.append(token)

	aligned_seq_a, aligned_seq_b, score_seq, tot_score = align([x.text for x in tokens_a],
																[x.text for x in tokens_b])

	aligned_tokens_a = []

	i = 0
	for token in aligned_seq_a:
		if token == "_":
			aligned_tokens_a.append(None)
		else:
			aligned_tokens_a.append(tokens_a[i])
			i+=1

	aligned_tokens_b = []

	i = 0
	for token in aligned_seq_b:
		if token == "_":
			aligned_tokens_b.append(None)
		else:
			aligned_tokens_b.append(tokens_b[i])
			i+=1

	return aligned_tokens_a, aligned_tokens_b


def align(seq_a, seq_b, match_score=1, mismatch_score=-1, indel_score=-1.0):

	aligned_seq_a, aligned_seq_b = needleman_wunsch(
		seq_a,
		seq_b,
		match_score=1.0,
		mismatch_score=-1.0,
		indel_score=-1.0, # @Ludo siccome qui è -1.0 l'ho cambiato anche tra i parametri sopra
		gap="_",
	)

	score_seq = []
	for x, y in zip(aligned_seq_a, aligned_seq_b):
		if x == y:
			score_seq.append(0)
		elif x == "_" or y == "_":
			score_seq.append(0.5)
		else:
			score_seq.append(1)

	tot_score = sum(score_seq)/len(score_seq)

	return aligned_seq_a, aligned_seq_b, score_seq, tot_score


def count_mismatch(filenames):
	voc_gold = set()
	voc_trascrittore = set()

	frequenze = collections.defaultdict(lambda: collections.defaultdict(int))

	for filename in filenames:
		with open(filename) as fin:
			fin.readline()

			for line in fin:
				linesplit = line.strip().split("\t")

				match, _, tok_trascrittore, _, tok_gold = linesplit

				if not match == "0":
					frequenze[tok_gold][tok_trascrittore] += 1
					voc_gold.add(tok_gold)
					voc_trascrittore.add(tok_trascrittore)

	sorted_frequenze = sorted(frequenze.items())

	with open(f"data/output_{filename.name.rsplit('/', 1)[-1]}", "w") as fout:

		writer = csv.DictWriter(fout, fieldnames=["TOK_GOLD"]+ list(voc_trascrittore),
						restval=0)

		writer.writeheader()

		for tok_gold, substitutions in sorted_frequenze:
			substitutions["TOK_GOLD"] = tok_gold
			substitutions = dict(substitutions)


			writer.writerow(substitutions)

def compute_wer(file_path): # computes wer from alignment
	substitutions = insertions = deletions = 0
	N = 0 # wer denominator

	with open(file_path, encoding="utf-8") as f:
		next(f) #to skip header
		for line in f:
			match, _, token_A, _, token_B = line.strip().split("\t") #match indicates type of alignment (0, 1, 2), token_A = token from reference file (Gold), token_B = token from hypothesis (FS, WHI)
			if match == "0":
				N +=1 # no error, so number of reference words increases
			elif match == "1":
				if token_A == "_": # that token is not present in the reference Gold
					insertions +=1
				elif token_B == "_":
					deletions +=1 # that token is not present in the hypothesis
			elif match == "2":
				substitutions += 1 #different but aligned tokens
				N += 1

	wer = (substitutions + deletions + insertions) / N if N > 0 else 0.0
	return wer


#TODO creare una sola tabella finale (una per fs e una per gold)
if __name__ == "__main__":
	import sys
    # fs_files_list = list(p for p in pathlib.Path("data/alignments").iterdir() if re.match(r"01.*03",p.name))
    # whi_files_list = list(p for p in pathlib.Path("data/alignments").iterdir() if re.match(r"02.*03",p.name))
    # count_mismatch(fs_files_list)
    # count_mismatch(whi_files_list)


	alignment_dir = pathlib.Path(sys.argv[1])
	for file in alignment_dir.glob("*.tsv"):
		wer = compute_wer(file)
		print(f"{file.name}: WER = {wer:.2%}")


