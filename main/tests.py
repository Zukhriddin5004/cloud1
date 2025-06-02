# main/tests/test_smoke.py
from django.test import SimpleTestCase, Client


class MathSmokeTest(SimpleTestCase):
    """Django va Python muhiti to'g'ri ishlayotganini tekshiradi."""

    def test_basic_math(self):
        self.assertEqual(1 + 1, 2)