import csv

import kiparla_tools.serialize as serialize
import kiparla_tools.alignment as alignment

from kiparla_tools.config_parameters import (
	CONLL_FIELDNAMES,
	MULTIWORDS
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
		# print("FILENAME", filename)
		for unit_id, unit in serialize.units_from_conll(fin):
			unit_processed = []
			unit_text = []
			unit_full = []
			for idx, token in enumerate(unit):
				tok_type = token["type"]
				text = token["form"]

				if ignore_meta and not tok_type in ["shortpause", "nonverbalbehavior"]:
					unit_text.append(text) #TODO: handle spaceafter?
				unit_full.append(text)

			if len(unit_text):
				doc = model(" ".join(unit_text))
				print()
				print()
				# print(doc)

				doc = [token for token in doc]
				doc_text = [token.text for token in doc]

				# unit_full = il gatto ((sbadiglio)) dorme sul divano
				# unit_text = il gatto dorme sul divano
				# doc_text = il gatto dorme su il divano

				# ---> il gatto ((sbadiglio)) dorme sul su il divano

				aligned_orig, aligned_proces, _, _ = alignment.align(unit_full, doc_text)

				subparts = []
				i=0
				part = []
				while i<len(aligned_orig):
					while i<len(aligned_orig) and aligned_orig[i] == aligned_proces[i]:
						part.append(i)
						i+=1

					if len(part)>0:
						subparts.append(["ALIGNED", part])
						part = []

					while i<len(aligned_orig) and aligned_orig[i] != aligned_proces[i]:
						part.append(i)
						i+=1

					if len(part)>0:
						subparts.append(["MISMATCH", part])
						part = []
					# i+=1

				# print(subparts)
				aligned_sequence = []

				for element in subparts:
					label, element_ids = element
					print(label, [aligned_orig[i] for i in element_ids])
					print(label, [aligned_proces[i] for i in element_ids])

					if label == "ALIGNED":
						for i in element_ids:
							aligned_sequence.append(("original", aligned_orig[i]))

					elif label == "MISMATCH":
						# print("HERE")

						orig_elements = [aligned_orig[i] for i in element_ids if not aligned_orig[i] == "_"]
						proces_elements = [aligned_proces[i] for i in element_ids if not aligned_proces[i] == "_"]

						# if "-" in proces_elements:
						# 	aligned_sequence.append(("original", "".join(orig_elements)))
						# 	continue

						# print(orig_elements)
						# print(proces_elements)

						if len(orig_elements) == 0:
							aligned_sequence.append(("error", " ".join(proces_elements)))

						else:
							# print(orig_elements, proces_elements)
							# print("HERE")
							i=0
							j=0

							while i<len(orig_elements):
								tok = orig_elements[i]
								# print(tok)
								if tok.startswith("{"):
									aligned_sequence.append(("nvb", tok))
								else:
									# TODO: turn into dynamic programming algorithm
									# print(tok in MULTIWORDS, len(proces_elements), j)
									if tok in MULTIWORDS:
										if j+MULTIWORDS[tok]<len(proces_elements)+1:
											aligned_sequence.append(("multiword-B", tok))
											aligned_sequence.append(("multiword-I", proces_elements[j]))
											# print("multi", proces_elements[j])
											# print(tok, proces_elements[j])
											for _ in range(MULTIWORDS[tok]-1):
												j+=1
												aligned_sequence.append(("multiword-I", proces_elements[j]))
												# print("_", proces_elements[j])
											j+=1
										else:
											aligned_sequence.append(("original", proces_elements[j]))
											j+=1
									else:
										if tok.endswith("-") or tok.endswith("~") or tok.startswith("-") or tok.startswith("~"):
											aligned_sequence.append(("multiword-B", tok))
											aligned_sequence.append(("multiword-I", proces_elements[j]))
											aligned_sequence.append(("multiword-I", proces_elements[j+1]))
											j+=2

										elif "-" in tok or "~" in tok:
											prova = "".join(proces_elements[j:])
											if prova == tok:
												aligned_sequence.append(("multiword-B", tok))
												while j<len(proces_elements):
													aligned_sequence.append(("multiword-I", proces_elements[j]))
													j+=1

												# print(tok, prova)
												# input()
												# aligned_sequence.append(("original", tok))
												# j+=len(proces_elements)-j+1
											# aligned_sequence.append(("multiword-I", proces_elements[j]))
											# aligned_sequence.append(("multiword-I", proces_elements[j+1]))
											# aligned_sequence.append(("multiword-I", proces_elements[j+2]))
											# j+=1

										elif tok.endswith("gliene"):
											aligned_sequence.append(("multiword-B", tok))
											aligned_sequence.append(("multiword-I", proces_elements[j]))
											aligned_sequence.append(("multiword-I", proces_elements[j+1]))
											aligned_sequence.append(("multiword-I", proces_elements[j+2]))
											j+=3

										else:
											aligned_sequence.append(("multiword-B", tok))
											aligned_sequence.append(("multiword-I", proces_elements[j]))
											aligned_sequence.append(("multiword-I", proces_elements[j+1]))
											j+=2

										# print("############# TOK ##############")
										# print(tok)
										# #TODO
										# aligned_sequence.append(("original", proces_elements[j]))

										# aligned_sequence.append(("ignore", proces_elements[j+1]))
										# j+=2
								i+=1

				# print("ALIGNED SEQUENCE:")
				# print(aligned_sequence)
				# input()

				# OLD VERSION, REMOVE
						# orig_elements_len = []
						# for el in orig_elements:
						# 	if el.startswith("{"):
						# 		orig_elements_len.append((el, 1))
						# 	elif el in _

				# i=len(aligned_orig)-1
				# while i>0:
				# 	j = i-1
				# 	prev_element = aligned_orig[j]
				# 	if prev_element == "_":
				# 		aligned_orig[i], aligned_orig[j] = aligned_orig[j], aligned_orig[i]
				# 	i-=1

				# OLD VERSION, REMOVE
				idx_unit, idx_doc = 0, 0
				last_mw_id = ""
				last_mv_idx = 0
				mw_suffix = ["a", "b", "c", "d"]
				ptr = None

				for alignment_type, token in aligned_sequence:
					# print(alignment_type, token)

					if alignment_type == "nvb":
						# print("adding", unit[idx_unit])
						unit_processed.append(unit[idx_unit])
						idx_unit += 1

					if alignment_type == "ignore":
						# print("adding nothing")
						new_token = {"token_id": f"{unit_id}-X",
									"unit": unit_id,
									"form": "_"}
						add_info(new_token, doc[idx_doc])
						unit_processed.append(new_token)
						# idx_unit += 1
						idx_doc += 1

					if alignment_type == "original":
						add_info(unit[idx_unit], doc[idx_doc])
						# print("adding", unit[idx_unit])
						unit_processed.append(unit[idx_unit])
						idx_unit += 1
						idx_doc += 1

					if alignment_type == "error":
						new_token = {"token_id": unit[idx_unit]["token_id"],
									"unit": unit_id,
									"form": doc[idx_doc].text}
						add_info(new_token, doc[idx_doc])
						unit_processed.append(new_token)
						# print(token)
						idx_doc += 1

					if alignment_type == "multiword-B":
						last_mw_id = unit[idx_unit]["token_id"]
						last_mv_idx = 0
						unit[idx_unit]["id"] = "100-0"
						ptr = unit[idx_unit]
						# print("adding", unit[idx_unit])
						unit_processed.append(unit[idx_unit])
						idx_unit += 1

					if alignment_type == "multiword-I":
						new_token = {"token_id": f"{last_mw_id}{mw_suffix[last_mv_idx]}",
									"unit": unit_id,
									"form": doc[idx_doc].text}
						last_mv_idx +=1
						add_info(new_token, doc[idx_doc])
						# print("adding", new_token)
						unit_processed.append(new_token)
						idx_doc += 1

						old_ids = ptr["id"].split("-")
						id_min, id_max = int(old_ids[0]), int(old_ids[1])
						curr_id = int(new_token["id"])
						if curr_id < id_min:
							id_min = curr_id
						if curr_id > id_max:
							id_max = curr_id
						ptr["id"] = f"{id_min}-{id_max}"

				# for token in unit_processed:
					# print(token["token_id"], token["id"], token["form"], token["deprel"])
					# input()
				# print(unit_processed)
				# input("END")

				# OLD VERSION, REMOVE
				# idx_unit, idx_doc = 0, 0
				# ids = []
				# ptr = None
				# for _, (orig_token, proces_token) in enumerate(zip(aligned_orig, aligned_proces)):
				# 	updatable = True
				# 	if orig_token == proces_token:
				# 		add_info(unit[idx_unit], doc[idx_doc])
				# 		unit_processed.append(unit[idx_unit])

				# 		idx_unit += 1
				# 		idx_doc += 1

				# 	elif proces_token == "_":
				# 		unit_processed.append(unit[idx_unit])
				# 		idx_unit += 1

				# 	elif orig_token == "_":
				# 		updatable = False
				# 		new_token = {"token_id":"_",
				# 					"unit": unit_id,
				# 					"form": doc[idx_doc].text}
				# 		ids.append(doc[idx_doc].i+1)
				# 		add_info(new_token, doc[idx_doc])
				# 		unit_processed.append(new_token)
				# 		idx_doc += 1

				# 	else:
				# 		updatable = False
				# 		#TODO: aiutooooooo
				# 		ids.append(doc[idx_doc].i+1)
				# 		new_token = {"token_id":"_",
				# 					"unit": unit_id,
				# 					"form": doc[idx_doc].text}
				# 		add_info(new_token, doc[idx_doc])

				# 		if orig_token.startswith("{"):
				# 			unit_processed.append(new_token)
				# 			unit_processed.append(unit[idx_unit])
				# 		else:
				# 			# updatable = False
				# 			ptr = unit[idx_unit]
				# 			unit_processed.append(unit[idx_unit])
				# 			unit_processed.append(new_token)

				# 		idx_unit += 1
				# 		idx_doc += 1

				# 	if updatable and ptr:
				# 		ptr["id"] = "-".join([str(x) for x in ids])
				# 		ids = []
				# 		ptr = None

				# if updatable and ptr:
				# 	ptr["id"] = "-".join([str(x) for x in ids])
				# 	ids = []
				# 	ptr = None

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

				for token in unit_processed:
					if not token["deprel"] == "root:0":
						if token["deprel"] == "_":
							token["deprel"] = "dep:" + str(root_id)
						else:
				# 			# print(token)
							token["deprel"] = ":".join([token["deprel"].rsplit(":", 1)[0], str(ids_map[token["deprel"].rsplit(":", 1)[1]])])
					if "-" in token["id"]:
						token["id"] = "-".join([str(ids_map[x]) for x in token["id"].split("-")])
						token["deprel"] = "_"

				# for token in unit_processed:
					# print(token["token_id"], token["id"], token["form"], token["deprel"])
					# input()
				# print(unit_processed)
				# input("END")

				final_list.extend(unit_processed)

			else:
				final_list.extend(unit)

		for token in final_list:
			# print(token)
			# input()
			if "type" in token and token["type"] == "nonverbalbehavior":
				if token["id"] == "_":
					token["id"] = token["token_id"].split("-")[1]
					token["upos"] = "X"
					token["deprel"] = "root:0"

			# if not token["token_id"] == "_":
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

			if ignore_meta and not type in ["error", "shortpause", "nonverbalbehavior"]:
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