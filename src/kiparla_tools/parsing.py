from wtpsplit import SaT

# use our '-sm' models for general sentence segmentation tasks
sat_sm = SaT("sat-3l-sm", style_or_domain="ud", language="it")
# sat_sm.half().to("cuda") # optional, see above
ret = sat_sm.split("persone che magari puoi avere incontrato un po' si cioè è sempre pieno dipersone che fanno l' elemosina sotto i portici soprattutto su via indipendenza anche sotto i portici di via di viale masini anche cremonini dicono che si aspetti neanche io mai non l' ho ancora incontrato cremonin pero' in questi tre anni perché io sono dal duemiladiciotto  sì tre anni che sono lì non ho ancora incrociato cremonini vabbè magari dai quest' anno sarà l' anno buono")
# returns ["this is a test ", "this is another test"]
print("\n".join(ret))
