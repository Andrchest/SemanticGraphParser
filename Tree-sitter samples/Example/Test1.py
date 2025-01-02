from math import sqrt

class Class_form_Test1:

    def __init__(self, a, b):
        self.a = a
        self.b = b

    def print1(self):
        print(1)

    def own_sqrt(self, val):
        return sqrt(2 * val)


def test1_func(a, b):
    return max(a, b)