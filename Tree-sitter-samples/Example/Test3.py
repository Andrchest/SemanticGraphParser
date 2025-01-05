import Test2 as T
from Test4 import global_function, outer_function
from Test1 import Class_form_Test1, test1_func as C
from Folder1.Test6 import *

class Class_from_Test3:

    def __init__(self, a):
        self.a = a

    def func_in_Class3(self):

        return T.func_form_test2()
