"""Functions to handle sequence alignment"""
import collections
from sequence_align.pairwise import needleman_wunsch
#hirschberg
from typing import List
import csv

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


def align(seq_a, seq_b, match_score=1, mismatch_score=-1, indel_score=-0.5):

	aligned_seq_a, aligned_seq_b = needleman_wunsch(
		seq_a,
		seq_b,
		match_score=1.0,
		mismatch_score=-1.0,
		indel_score=-1.0,
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

	with open(f"data/output_{filename.rsplit('/', 1)[-1]}", "w") as fout:

		writer = csv.DictWriter(fout, fieldnames=["TOK_GOLD"]+ list(voc_trascrittore),
						restval=0)
		
		writer.writeheader()

		for tok_gold, substitutions in sorted_frequenze:
			substitutions["TOK_GOLD"] = tok_gold
			substitutions = dict(substitutions)


			writer.writerow(substitutions)

if __name__ == "__main__":
	count_mismatch("data/alignments/01_ParlaBOA_E_03_ParlaBOA.tsv")
	count_mismatch("data/alignments/03_ParlaBOA_01_ParlaBOA_M.tsv")