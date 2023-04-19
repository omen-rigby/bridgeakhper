import ctypes
from ctypes import POINTER, Structure, c_char, c_int


class dealPBN(Structure):
    _fields_ = [("trump", c_int), ("first", c_int), ("currentTrickSuit", c_int * 3), ("currentTrickRank", c_int * 3),
                ("remainCards", c_char * 80)]


class playTracePBN(Structure):
    _fields_ = [("number", c_int), ("cards", c_char * 106)]


class solvedPlay(Structure):
    _fields_ = [("number", c_int), ("tricks", c_int * 53)]
