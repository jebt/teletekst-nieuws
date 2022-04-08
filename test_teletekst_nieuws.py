from unittest import TestCase

target = __import__('teletekst_nieuws').transform_to_normal_format


class Test(TestCase):
    def test_transform_to_normal_format(self):
        new = target("blabla,enzo")
        self.assertEqual(new, "blabla, enzo")

        new = target("blabla:enzo;blabla")
        self.assertEqual(new, "blabla: enzo; blabla")

        new = target("""blabla:enzo;blabla,
        ditendat?enzo 
        nogmaar, 
        zus en zo, yes yes """)
        self.assertEqual(new, "blabla: enzo; blabla, ditendat? enzo nogmaar, zus en zo, yes yes")
