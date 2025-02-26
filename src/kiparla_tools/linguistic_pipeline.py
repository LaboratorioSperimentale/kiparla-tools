import csv


def segment(model, nlp, filename, output_filename, ignore_meta):

	full_ids = []
	full_text = []
	fieldnames = []

	with open(filename, encoding="utf-8") as fin:
		reader = csv.DictReader(fin, delimiter="\t")
		for row in reader:
			token_id = row["token_id"]
			type = row["type"]
			text = row["token"]
			fieldnames = list(row.keys())

			if not type in ["error", "shortpause", "metalinguistic"]:
				full_text.append(text)
				full_ids.append(token_id)

	ret = model.split(" ".join(full_text))

	tokens = {}
	i=0
	for sent_id, sent in enumerate(ret):
		doc = nlp(sent)
		sent = sent.split()

		n=0
		for token in doc:
			print(token.text, token.lemma_, token.pos_, token.dep_)
			n+=1



		print(len(sent), n)
		input()

		for tok in sent:
			tokens[full_ids[i]] = sent_id
			i += 1



	with open(filename, encoding="utf-8") as fin, open(output_filename, "w", encoding="utf-8") as fout:
		reader = csv.DictReader(fin, delimiter="\t")
		writer = csv.DictWriter(fout, delimiter="\t", fieldnames=fieldnames+["unit"])
		writer.writeheader()
		for row in reader:
			token_id = row["token_id"]

			if token_id in tokens:
				row["unit"] = tokens[token_id]

			writer.writerow(row)

			# if curr_tok_id == len(curr_sent):
			# 	sent_id += 1
			# 	curr_sent = ret[sent_id]
			# 	curr_tok_id = 0

			# curr_tok = curr_sent[curr_tok_id]

			# if full_ids[i] == token_id:

			# else:
			# 	row["unit"] = sent_id

			# curr_tok_id += 1

# # use our '-sm' models for general sentence segmentation tasks


# text = open(sys.argv[1]).read()


# sat_sm = SaT("sat-12l-sm")
# ret = sat_sm.split(text)
# print("\n".join(ret))


# model = Model('english-ud-1.2-160523.udpipe')
#  sentences = model.tokenize("Hi there. How are you?")
#  for s in sentences:
#      model.tag(s)
#      model.parse(s)
#  conllu = model.write(sentences, "conllu")