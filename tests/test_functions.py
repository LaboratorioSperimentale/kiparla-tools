"""Test functions"""
import kiparla_tools.process_text as pt

def test_removespaces():
    """
    The function `test_removespaces` tests the `remove_spaces` function.
    """
    assert pt.remove_spaces("  ciao") == (1, "ciao")
    assert pt.remove_spaces("ciao  ") == (1, "ciao")
    assert pt.remove_spaces("ciao   ") == (1, "ciao")
    assert pt.remove_spaces("ci  si  ") == (2, "ci si")


def test_meta_tag():
    """
    The `test_meta_tag` function tests the `meta_tag` function.
    """
    assert pt.meta_tag("(.) ciao") == "{P} ciao"
    assert pt.meta_tag("ciao ((bla bla)) ciao") == "ciao {bla_bla} ciao"


def test_replace_po():
    """
    The function `test_replace_po` tests the `replace_po` function.
    """
    assert pt.replace_po("pò") == (1, "po'")
    assert pt.replace_po("p:ò") == (1, "p:o'")


def test_replace_che():
    """
    The function `test_replace_che` tests the `replace_che` function.
    """
    assert pt.replace_che("perchè") == (1, "perché")
    assert pt.replace_che("finchè") == (1, "finché")


def test_pauses():
    """
    The function `test_pauses` tests the `remove_pauses` function.
    """
    assert pt.remove_pauses("{P} ciao") == (1, "ciao")
    assert pt.remove_pauses("ciao {P}") == (1, "ciao")
    assert pt.remove_pauses("{P} ciao {P}") == (2, "ciao")
    assert pt.remove_pauses("ciao {P} ciao") == (0, "ciao {P} ciao")
    assert pt.remove_pauses("(a) casa") == (0, "(a) casa")
    assert pt.remove_pauses("[{P} casa") == (1, "[casa")
    assert pt.remove_pauses("casa {P} >") == (1, "casa>")


def test_check_even_dots():
    """
    The function `test_check_even_dots` tests the `check_even_dots` function.
    """
    assert pt.check_even_dots("°ciao°") is True
    assert pt.check_even_dots("°ciao") is False


def test_check_normal_parentheses():
    """
    The function `test_check_normal_parentheses` tests the `check_normal_parentheses` function.
    """
    assert pt.check_normal_parentheses("(ciao)", "(", ")") is True
    assert pt.check_normal_parentheses("(ciao", "(", ")") is False
    assert pt.check_normal_parentheses("[ciao]", "[", "]") is True
    assert pt.check_normal_parentheses("ciao]", "[", "]") is False


def test_check_angular_parentheses():
    """
    The function `test_check_angular_parentheses` tests the `check_angular_parentheses` function.
    """
    assert pt.check_angular_parentheses("<ciao>") is True
    assert pt.check_angular_parentheses(">ciao<") is True
    assert pt.check_angular_parentheses("<ciao") is False
    assert pt.check_angular_parentheses("ciao>") is False
    assert pt.check_angular_parentheses("<<ciao>>") is False
    assert pt.check_angular_parentheses("bla <slow> followed by >fast<") is True
    assert pt.check_angular_parentheses("bla >fast< followed by <slow>") is True


def test_check_spaces_dots():
    """
    The function `test_check_spaces_dots` tests the `check_spaces_dots` function.
    """
    assert pt.check_spaces_dots("° ciao°") == (1, "°ciao°")
    assert pt.check_spaces_dots("°ciao °") == (1, "°ciao°")
    assert pt.check_spaces_dots("bla °bla bla ° bla ° bla bla°") == \
                                (2, "bla °bla bla° bla °bla bla°")


def test_check_spaces_angular():
    """
    The function `test_check_spaces_angular` tests the `check_spaces_angular` function.
    """
    assert pt.check_spaces_angular("< ciao>") == (1, "<ciao>")
    assert pt.check_spaces_angular(">ciao <") == (1, ">ciao<")
    assert pt.check_spaces_angular("bla >bla bla < bla < bla bla> bla") == \
                                    (2, "bla >bla bla< bla <bla bla> bla")


def test_overlap_prolongations():
    """
    The function `test_overlap_prolongations` tests the `overlap_prolongations` function.
    """
    assert pt.overlap_prolongations("questo:[::") == (1, "quest[o:::")
    assert pt.overlap_prolongations("quest[o::") == (0, "quest[o::")
