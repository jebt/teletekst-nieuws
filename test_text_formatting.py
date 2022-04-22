from unittest import TestCase

target = __import__('text_formatting').transform_to_normal_format


class Test(TestCase):
    def test_transform_to_normal_format(self):
        new = target("blabla,enzo")
        self.assertEqual("blabla, enzo", new)

        new = target("blabla:enzo;blabla")
        self.assertEqual("blabla: enzo; blabla", new)

        new = target("""blabla:enzo;blabla,
        ditendat?enzo 
        nogmaar, 
        zus en zo, yes yes """)
        self.assertEqual("blabla: enzo; blabla, ditendat? enzo nogmaar, zus en zo, yes yes", new)

    def test_transform_to_normal_format_with_empty_string(self):
        new = target("")
        self.assertEqual("", new)

    def test_transform_to_normal_format_with_big_numbers(self):
        new = target("jip.janneke 100.000 piet,456.040 paulus.")
        self.assertEqual("jip. janneke 100.000 piet, 456.040 paulus.", new)

    def test_transform_to_normal_format_with_decimal_numbers(self):
        new = target("jip.janneke 1,2 piet,paulus. en.dit;is 0,738495 ofzo.doie")
        self.assertEqual("jip. janneke 1,2 piet, paulus. en. dit; is 0,738495 ofzo. doie", new)

    def test_transform_to_normal_format_with_stuff_at_beginning(self):
        new = target(".blabla,enzo")
        self.assertEqual(".blabla, enzo", new)

    def test_transform_to_normal_format_with_stuff_at_end(self):
        new = target("blabla,enzo.")
        self.assertEqual("blabla, enzo.", new)

    def test_trans_with_dotdotdot(self):
        new = target("blabla,enzo....")
        self.assertEqual("blabla, enzo....", new)

    def test_trans_with_quote(self):
        new = target("en toen zei ze \"het is mooi geweest!\"")
        self.assertEqual("en toen zei ze \"het is mooi geweest!\"", new)

    def test_trans_with_paragraphs(self):
        new = target("""ggerg egerge ergegew

faweefweafwef w faew aw""")
        self.assertEqual("""ggerg egerge ergegew

faweefweafwef w faew aw""", new)

    def test_trans_with_quote_after_colon(self):
        new = target("tabak:\"Het")
        self.assertEqual("tabak: \"Het", new)

    # differentiate between opening- and closing quotes
    def test_trans_with_opening_and_closing_quotes(self):
        new = target("hij zegt:\"Hallo!\".'Hallo!' zei hij")
        self.assertEqual("hij zegt: \"Hallo!\". 'Hallo!' zei hij", new)

    def test_trans_with_word_after_closing_quote(self):
        new = target("ze.\"En dat is terecht.\"Ze")
        self.assertEqual('ze. "En dat is terecht." Ze', new)

    # todo: the two beneath combined may be a tough cookie to crack
    # def test_trans_with_word_after_closing_single_quote(self):
    #     new = target("ze.'En dat is terecht.'Ze")
    #     self.assertEqual("ze. 'En dat is terecht.' Ze", new)

    def test_trans_with_apostrophe(self):
        new = "hoe'ist nou?"
        self.assertEqual("hoe'ist nou?", new)
