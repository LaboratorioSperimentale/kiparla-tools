import sys
import csv
from pathlib import Path
from pympi import Elan as EL

input_csv = Path(sys.argv[1])

basename: str = input_csv.stem
print(basename)

tiers = set()
tus = []
header: list[str] = ["speaker", "begin", "end", "duration", "text"]



with open(input_csv, encoding="utf-8") as csvfile:
    reader = csv.reader(csvfile, delimiter='\t', quotechar='"')
    for row in reader:
        d = dict(zip(header, row))
        tiers.add(d["speaker"])
        tus.append(d)
        # print(row)

doc = EL.Eaf(author="automatic_pipeline")

for tier_id in tiers:
	doc.add_tier(tier_id=tier_id)

for annotation in tus:

	doc.add_annotation(id_tier=annotation["speaker"],
					   start=int(float(annotation["begin"])*1000),
					   end=int(float(annotation["end"])*1000),
					   value=annotation["text"])


# doc.add_tier(tier_id="BO026")
# doc.add_annotation(id_tier="BO020",
# 				   start=int(13.006*1000),
# 				   end=int(14.390*1000),
# 				   value="mi ricorda il suo nome,")

output_fname: Path = Path("data/eaf_puliti").joinpath(f"{basename}.eaf")
# print(output_fname)
doc.to_file(output_fname)
# print(doc)
