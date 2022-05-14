# from unittest import TestCase

target = __import__('utilities').split_short_stories_text


# class Test(TestCase):
#     def test_split(self):
#         short_story_page_text = """                      NOS Teletekst 190
#         
#             Kort nieuws binnenland
#
#         
#          De voorzitter van de politievakbond
#          ACP,Gerrit van de Kamp,legt na 18 jaar
#          zijn functie neer met een beroep op
#          zijn gezondheid.Van de Kamp werd eerder
#          dit jaar van grensoverschrijdend gedrag
#          beschuldigd.Omdat er geen bewijs voor
#          was,ging hij weer aan de slag.Maar die
#          periode heeft hem fysiek en psychisch
#          zwaar aangepakt,meldt de vakbond.Van de
#          Kamp blijft wel actief voor de ACP.
#
#          Op Nederlandse scholen staan nu zeker
#          7300 Oekraïense kinderen ingeschreven,
#          meldt Nu.nl op basis van het ministerie
#          van Onderwijs.65 procent gaat naar de
#          basisschool,de rest naar de middelbare
#          school.Vermoedelijk lopen de cijfers
#          achter bij de werkelijke situatie.
#         
#          nieuws   sport   financieel   voetbal  """
#         desired_result = ["""NOS Teletekst 190 \n        \uf020\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c
#         \uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c
#         \uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\n            Kort nieuws binnenland
#                     \n\n        \uf020\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c
#                     \uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c
#                     \uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\n        \uf020 De voorzitter van de
#                     politievakbond  \n         ACP,Gerrit van de Kamp,legt na 18 jaar \n         zijn functie neer
#                     met een beroep op    \n         zijn gezondheid.Van de Kamp werd eerder\n         dit jaar van
#                     grensoverschrijdend gedrag\n         beschuldigd.Omdat er geen bewijs voor  \n         was,
#                     ging hij weer aan de slag.Maar die \n         periode heeft hem fysiek en psychisch  \n
#                     zwaar aangepakt,meldt de vakbond.Van de\n         Kamp blijft wel actief voor de ACP.    \n\n
#                        \uf020\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c
#                        \uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c
#                        \uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c', '                      NOS
#                        Teletekst 190 \n
#                        \uf020\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c
#                        \uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c
#                        \uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\n            Kort nieuws
#                        binnenland              \n\n
#                        \uf020\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c
#                        \uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c
#                        \uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\n        \uf020 Op Nederlandse
#                        scholen staan nu zeker\n         7300 Oekraïense kinderen ingeschreven, \n         meldt Nu.nl
#                        op basis van het ministerie\n         van Onderwijs.65 procent gaat naar de  \n
#                        basisschool,de rest naar de middelbare \n         school.Vermoedelijk lopen de cijfers   \n
#                             achter bij de werkelijke situatie.     \n
#                             \uf020\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c
#                             \uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c
#                             \uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\n         nieuws
#                               sport   financieel   voetbal
#                               \uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c
#                               \uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c
#                               \uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c\uf02c"""]
#         actual_result = target(short_story_page_text)
#         self.assertEqual(desired_result, actual_result)
