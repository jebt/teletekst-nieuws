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

    # def test_trans_with_website_brutal(self):  # todo: too difficult? need to use lib to test if part of valid url?
    #     new = target("https://ww2.1337x.buzz/")
    #     self.assertEqual("https://ww2.1337x.buzz/", new)

    # def test_trans_with_website_hard(self):  # todo: make pass (if followed by lowercase letter?)
    #     new = target("old.reddit.com")
    #     self.assertEqual('old.reddit.com', new)
    #
    # def test_trans_with_website_medium(self):  # todo make pass (following "www"?) or more general: followed by lower
    #     new = target("www.reddit.com")
    #     self.assertEqual('www.reddit.com', new)

    def test_trans_with_website_easy(self):  # todo: suffix detection obsolete if generalized to followed by lowercase
        new = target("reddit.com")
        self.assertEqual('reddit.com', new)

    # todo: the two beneath combined may be a tough cookie to crack?
    # def test_trans_with_word_after_closing_single_quote(self):
    #     new = target("ze.'En dat is terecht.'Ze")
    #     self.assertEqual("ze. 'En dat is terecht.' Ze", new)

    def test_trans_with_apostrophe(self):
        new = target("hoe'ist nou?")
        self.assertEqual("hoe'ist nou?", new)

    # def test_trans_with_time_dot_notation(self):  # todo: make pass
    #     new = target("tot 15.00 uur.")
    #     self.assertEqual("tot 15.00 uur.", new)
    #
    # def test_trans_with_time_colon_notation(self):  # todo: make pass
    #     new = target("tot 15:00 uur.")
    #     self.assertEqual("tot 15:00 uur.", new)

