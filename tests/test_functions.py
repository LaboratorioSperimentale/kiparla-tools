import kiparla_tools.process_text as pt

def test_removespaces():
    assert pt.remove_spaces("  ciao") == (1, "ciao")
    assert pt.remove_spaces("ciao  ") == (1, "ciao")
    assert pt.remove_spaces("ciao   ") == (1, "ciao")
    assert pt.remove_spaces("ci  ao  ") == (2, "ci ao")

def test_meta_tag():
    assert pt.meta_tag("(.) ciao") == "{P} ciao"
    assert pt.meta_tag("ciao ((bla bla)) ciao") == "ciao {bla_bla} ciao"

def test_replace_po():
    assert pt.replace_po("pò") == (1, "po'")
    assert pt.replace_po("p:ò") == (1, "p:o'")

def test_replace_che():
    assert pt.replace_che("perchè") == (1, "perché")
    assert pt.replace_che("finchè") == (1, "finché")

def test_pauses():
    assert pt.remove_pauses("{P} ciao") == (1, "ciao")
    assert pt.remove_pauses("ciao {P}") == (1, "ciao")
    assert pt.remove_pauses("{P} ciao {P}") == (2, "ciao")
    assert pt.remove_pauses("ciao {P} ciao") == (0, "ciao {P} ciao")
    assert pt.remove_pauses("(a) casa") == (0, "(a) casa")
    assert pt.remove_pauses("[{P} casa") == (1, "[casa")
    assert pt.remove_pauses("casa {P} >") == (1, "casa>")

def test_check_even_dots():
    assert pt.check_even_dots("°ciao°") == True
    assert pt.check_even_dots("°ciao") == False

def test_check_normal_parentheses():
    assert pt.check_normal_parentheses("(ciao)", "(", ")") == True
    assert pt.check_normal_parentheses("(ciao", "(", ")") == False
    assert pt.check_normal_parentheses("[ciao]", "[", "]") == True
    assert pt.check_normal_parentheses("ciao]", "[", "]") == False

def test_check_angular_parentheses():
    assert pt.check_angular_parentheses("<ciao>") == True
    assert pt.check_angular_parentheses(">ciao<") == True
    assert pt.check_angular_parentheses("<ciao") == False
    assert pt.check_angular_parentheses("ciao>") == False
    assert pt.check_angular_parentheses("<<ciao>>") == False
    assert pt.check_angular_parentheses("bla <slow> followed by >fast<") == True
    assert pt.check_angular_parentheses("bla >fast< followed by <slow>") == True


def test_check_spaces_dots():
    assert pt.check_spaces_dots("° ciao°") == (1, "°ciao°")
    assert pt.check_spaces_dots("°ciao °") == (1, "°ciao°")
    assert pt.check_spaces_dots("bla °bla bla ° bla ° bla bla°") == (2, "bla °bla bla° bla °bla bla°")

def test_check_spaces_angular():
    assert pt.check_spaces_angular("< ciao>") == (1, "<ciao>")
    assert pt.check_spaces_angular(">ciao <") == (1, ">ciao<")
    assert pt.check_spaces_angular("bla >bla bla < bla < bla bla> bla") == (2, "bla >bla bla< bla <bla bla> bla")


# def test_check_intonation_patterns(): # TODO
#     assert pt.check_intonation_patterns("ciao.") == ("discendente")
#     assert pt.check_intonation_patterns("ciao,") == ("debolmente_ascendente")
#     assert pt.check_intonation_patterns("ciao?") == ("ascendente")
#     assert pt.check_intonation_patterns("ciao:") == ("suono_prolungato")
#     assert pt.check_intonation_patterns("cia-") == ("parola_interrotta")

def test_check_number_sign():
    assert pt.check_number_sign("#") == ("dialect")

def test_check_x():
    assert pt.check_x("x") == ("unkown")