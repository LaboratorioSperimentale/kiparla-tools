import os
from kiparla_tools.serialize import units_from_conll
from kiparla_tools.utils import find_ngrams, feats2dict

def coconstructions(fobj, stopwords=["ehm", "eh", "mhmh", "mh", "sì", "no", "okay", "x"]):
    candidates = []
    for (id,block) in units_from_conll(fobj):
        i = 0
        candidate = False
        block = [x for x in block if x["form"] not in stopwords and x["speaker"] not in ["traduzione", "COMMENT"] and not x["form"].startswith("{")]
        for (unit1,unit2) in find_ngrams(block, 2):
            if unit1["speaker"] != unit2["speaker"]:
                unit1_jefferson = feats2dict(unit1["align"])
                unit2_jefferson = feats2dict(unit2["align"])
                if "End" in unit1_jefferson and "Begin" in unit2_jefferson: 
                    end = float(unit1_jefferson["End"])
                    begin = float(unit2_jefferson["Begin"])
                    if end >= begin:
                        candidate = True
        if candidate and block[0]["speaker"] == block[1]["speaker"]:                
            candidates.append(block[0]["tu_id"] + " - " + " ".join(x["form"] + ":" + x["speaker"]  for x in block))
    return candidates
        #if len(set(token["speaker"]  for token in unit_block)) > 1:
        #    print(unit_id)


if __name__ == "__main__":
    folder = "/home/harisont/Repos/harisont/innesti/segmented/"
    files = [os.path.join(folder, file) for file in os.listdir(folder)]
    for file in files:
        with open(file) as fobj:
            candidates = coconstructions(fobj)
            print()
            print(file)
            for candidate in candidates:
                print(candidate)
            print(len(candidates))

