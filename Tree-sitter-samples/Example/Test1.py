from math import sqrt, sin
from Test3 import *

class Class_form_Test1:

    def __init__(self, a, b):
        self.a = a
        self.b = b

    def print1(self):
        print(1)

    def own_sqrt(self, val):
        return abs(2 * val)


def test1_func(a, b):
    return max(a, b)