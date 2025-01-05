from Test1 import Class_form_Test1
import math

class Class_form_Test2(Class_form_Test1):

    def __init__(self, a, b, c):
        super().__init__(a, b)
        self.c = c

    def function_call_Test2(self):
        print(Class_form_Test1.print1(self))


def func_form_test2():
    a = Class_form_Test1(1, 2)
    return a.own_sqrt(a.b)

