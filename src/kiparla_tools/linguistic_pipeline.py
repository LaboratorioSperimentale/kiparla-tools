import csv

import kiparla_tools.serialize as serialize
import kiparla_tools.alignment as alignment

from kiparla_tools.config_parameters import (
	CONLL_FIELDNAMES
)

#TODO: move into data
def add_info(dict, spacy_tok):
	dict["id"] = spacy_tok.i
	dict["lemma"] = spacy_tok.lemma_
	dict["upos"] = spacy_tok.pos_
	dict["xpos"] = spacy_tok.tag_
	dict["feats"] = str(spacy_tok.morph)
	dict["deprel"] = f"{spacy_tok.dep_}:{spacy_tok.head.i}"
	# token.text, token.lemma_, token.pos_, token.dep_

def parse(model, filename, output_filename, ignore_meta):
	fieldnames = CONLL_FIELDNAMES
	final_list = []

	with open(filename, encoding="utf-8") as fin, open(output_filename, "w", encoding="utf-8") as fout:

		writer = csv.DictWriter(fout, delimiter="\t", fieldnames=fieldnames, restval="_")
		writer.writeheader()

		for unit in serialize.units_from_conll(fin):
			unit_text = []
			unit_full = []
			for token in unit:
				tok_type = token["type"]
				text = token["form"]

				if ignore_meta and not tok_type in ["error", "shortpause", "metalinguistic"]:
					unit_text.append(text) #TODO: handle spaceafter?
				unit_full.append(text)

			if len(unit_text):
				# print (" ".join(unit_text))
				doc = model(" ".join(unit_text))
				doc = [token for token in doc]

				doc_text = [token.text for token in doc]

				aligned_full, aligned_doc, _, _ = alignment.align(unit_full, doc_text)

				i=len(aligned_full)-1
				while i>1:
					element = aligned_full[i]
					j = i-1
					prev_element = aligned_full[j]
					if prev_element == "_":
						aligned_full[i], aligned_full[j] = aligned_full[j], aligned_full[i]

					i-=1

				idx_unit, idx_doc = 0, 0

				ids = []
				ptr = None


				for pos, (full_token, doc_token) in enumerate(zip(aligned_full, aligned_doc)):
					updatable = True
					if full_token == doc_token:
						add_info(unit[idx_unit], doc[idx_doc])
						final_list.append(unit[idx_unit])
						# writer.writerow()

						idx_unit += 1
						idx_doc += 1

					elif doc_token == "_":
						final_list.append(unit[idx_unit])
						# writer.writerow(unit[idx_unit])
						idx_unit += 1

					elif full_token == "_":
						updatable = False
						new_token = {"token_id":"_",
									"form": doc[idx_doc].text}
						ids.append(doc[idx_doc].i)
						add_info(new_token, doc[idx_doc])
						final_list.append(new_token)
						# writer.writerow(new_token)
						idx_doc += 1

					else:
						updatable = False
						new_token = {"token_id":"_",
									"form": doc[idx_doc].text}
						ids.append(doc[idx_doc].i)
						ptr = unit[idx_unit]
						add_info(new_token, doc[idx_doc])

						# unit[idx_unit] = "-".join(ids)
						final_list.append(unit[idx_unit])
						final_list.append(new_token)
						# writer.writerow(unit[idx_unit])
						# writer.writerow(new_token)

						idx_unit += 1
						idx_doc += 1

					if updatable and ptr:
						ptr["id"] = "-".join([str(x) for x in ids])
						ids = []
						ptr = None
			else:
				final_list.extend(unit)

		for token in final_list:
			writer.writerow(token)

def segment(model, filename, output_filename, ignore_meta):

	full_ids = []
	full_text = []
	fieldnames = CONLL_FIELDNAMES

	with open(filename, encoding="utf-8") as fin:
		reader = csv.DictReader(fin, delimiter="\t")
		for row in reader:
			token_id = row["token_id"]
			type = row["type"]
			text = row["form"]

			if ignore_meta and not type in ["error", "shortpause", "metalinguistic"]:
				full_text.append(text)
				full_ids.append(token_id)

	ret = model.split(" ".join(full_text))

	tokens = {}
	i=0
	for sent_id, sent in enumerate(ret):
		sent = sent.split()

		for tok in sent:
			tokens[full_ids[i]] = sent_id
			i += 1


	curr_token_id = 0
	with open(filename, encoding="utf-8") as fin, open(output_filename, "w", encoding="utf-8") as fout:
		reader = csv.DictReader(fin, delimiter="\t")
		writer = csv.DictWriter(fout, delimiter="\t", fieldnames=fieldnames)
		writer.writeheader()
		for row in reader:
			token_id = row["token_id"]

			if token_id in tokens:
				row["unit"] = tokens[token_id]
				curr_token_id = tokens[token_id]
			else:
				row["unit"] = curr_token_id

			writer.writerow(row)

# model = Model('english-ud-1.2-160523.udpipe')
#  sentences = model.tokenize("Hi there. How are you?")
#  for s in sentences:
#      model.tag(s)
#      model.parse(s)
#  conllu = model.write(sentences, "conllu")