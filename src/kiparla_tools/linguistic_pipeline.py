import csv

import kiparla_tools.serialize as serialize
import kiparla_tools.alignment as alignment

from kiparla_tools.config_parameters import (
	CONLL_FIELDNAMES
)

#TODO: move into data
def add_info(dict, spacy_tok):
	dict["id"] = spacy_tok.i + 1
	dict["lemma"] = spacy_tok.lemma_
	dict["upos"] = spacy_tok.pos_
	dict["xpos"] = spacy_tok.tag_
	dict["feats"] = str(spacy_tok.morph)
	dict["deprel"] = f"{spacy_tok.dep_}:{spacy_tok.head.i + 1}" if spacy_tok.dep_ != "ROOT" else "root:0"
	# token.text, token.lemma_, token.pos_, token.dep_


def parse(model, filename, output_filename, ignore_meta):
	fieldnames = CONLL_FIELDNAMES
	final_list = []

	with open(filename, encoding="utf-8") as fin, open(output_filename, "w", encoding="utf-8") as fout:

		writer = csv.DictWriter(fout, delimiter="\t", fieldnames=fieldnames, restval="_")
		writer.writeheader()

		for _, unit in serialize.units_from_conll(fin):
			unit_processed = []
			unit_text = []
			unit_full = []
			for idx, token in enumerate(unit):
				tok_type = token["type"]
				text = token["form"]

				if ignore_meta and not tok_type in ["shortpause", "metalinguistic"]:
					unit_text.append(text) #TODO: handle spaceafter?
				unit_full.append(text)

			if len(unit_text):
				doc = model(" ".join(unit_text))

				doc = [token for token in doc]
				doc_text = [token.text for token in doc]

				# unit_full = il gatto ((sbadiglio)) dorme sul divano
				# unit_text = il gatto dorme sul divano
				# doc_text = il gatto dorme su il divano

				# ---> il gatto ((sbadiglio)) dorme sul su il divano

				aligned_orig, aligned_proces, _, _ = alignment.align(unit_full, doc_text)


				i=len(aligned_orig)-1
				while i>0:
					j = i-1
					prev_element = aligned_orig[j]
					if prev_element == "_":
						aligned_orig[i], aligned_orig[j] = aligned_orig[j], aligned_orig[i]
					i-=1

				idx_unit, idx_doc = 0, 0
				ids = []
				ptr = None
				for _, (orig_token, proces_token) in enumerate(zip(aligned_orig, aligned_proces)):
					updatable = True
					if orig_token == proces_token:
						add_info(unit[idx_unit], doc[idx_doc])
						unit_processed.append(unit[idx_unit])

						idx_unit += 1
						idx_doc += 1

					elif proces_token == "_":
						unit_processed.append(unit[idx_unit])
						idx_unit += 1

					elif orig_token == "_":
						updatable = False
						new_token = {"token_id":"_",
									"form": doc[idx_doc].text}
						ids.append(doc[idx_doc].i+1)
						add_info(new_token, doc[idx_doc])
						unit_processed.append(new_token)
						idx_doc += 1

					else:
						updatable = False
						ids.append(doc[idx_doc].i+1)
						new_token = {"token_id":"_",
									"form": doc[idx_doc].text}
						add_info(new_token, doc[idx_doc])

						if orig_token.startswith("{"):
							unit_processed.append(new_token)
							unit_processed.append(unit[idx_unit])
						else:
							# updatable = False
							ptr = unit[idx_unit]
							unit_processed.append(unit[idx_unit])
							unit_processed.append(new_token)

						idx_unit += 1
						idx_doc += 1

					if updatable and ptr:
						ptr["id"] = "-".join([str(x) for x in ids])
						ids = []
						ptr = None

				if updatable and ptr:
					ptr["id"] = "-".join([str(x) for x in ids])
					ids = []
					ptr = None

				root_id = -1
				ids_map = {}
				new_id = 1
				for token in unit_processed:
					token["id"] = str(token["id"])
					if not "-" in token["id"]:
						if token["id"] != "_":
							ids_map[token["id"]] = str(new_id)
						token["id"] = str(new_id)
						if token["deprel"] == "root:0":
							root_id = new_id
						new_id += 1

				# print(ids_map)
				for token in unit_processed:
					if not token["deprel"] == "root:0":
						if token["deprel"] == "_":
							token["deprel"] = "dep:" + str(root_id)
						else:
							token["deprel"] = ":".join([token["deprel"].rsplit(":", 1)[0], str(ids_map[token["deprel"].rsplit(":", 1)[1]])])
					if "-" in token["id"]:
						token["id"] = "-".join([str(ids_map[x]) for x in token["id"].split("-")])
						token["deprel"] = "_"
						# token["deprel"] = token["deprel"].split(":")[0] + ":" + str(root_id)
					# print(token["id"], token["form"], token["deprel"])
				# input()
				final_list.extend(unit_processed)

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