import transformers

# pipe = transformers.pipeline(model="dbmdz/bert-base-italian-cased")
pipe = transformers.pipeline("ner",
							model="sachaarbonel/bert-italian-cased-finetuned-pos")

res = pipe("ah beh se avessi la possibilità di far venire dei negozi e i negozianti e quant' altro così chiuderei questa strada e la farei solamente per noi")

for tok in res:
	print(f"{tok['word']}\t{tok['entity']}")