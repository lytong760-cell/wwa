def data_types():
    string = "String "
    Int = 10
    floating = 10.5
    byte = b"Byte"
    booling = True
    complex_ = 10 + 5j
    list_ = [1, 2, 3, 4, 5]
    tuple_ = (1, 2, 3, 4, 5)
    set_ = {1, 2, 3, 4, 5}
    dict_ = {"name": "John", "age": 30, "city": "New York"}
    frozen_set = frozenset([1, 2, 3, 4, 5])
    byte_array = bytearray(b"Byte Array")
    memory_view = memoryview(byte_array)
    return string, Int, floating, byte, booling, complex_, list_, tuple_, set_, dict_, frozen_set, byte_array, memory_view


def print_values():
    string, Int, floating, byte, booling, complex_, list_, tuple_, set_, dict_, frozen_set, byte_array, memory_view = data_types()
    print("String:", string)
    print("Integer:", Int)
    print("Floating:", floating)
    print("Byte:", byte)
    print("Boolean:", booling)
    print("Complex:", complex_)
    print("List:", list_)
    print("Tuple:", tuple_)
    print("Set:", set_)
    print("Dictionary:", dict_)
    print("Frozen Set:", frozen_set)
    print("Byte Array:", byte_array)
    print("Memory View:", memory_view)
def type_in_data_type():
    string, Int, floating, byte, booling, complex_, list_, tuple_, set_, dict_, frozen_set, byte_array, memory_view = data_types()
    print("Type of String:", type(string))
    print("Type of Integer:", type(Int))
    print("Type of Floating:", type(floating))
    print("Type of Byte:", type(byte))
    print("Type of Boolean:", type(booling))
    print("Type of Complex:", type(complex_))
    print("Type of List:", type(list_))
    print("Type of Tuple:", type(tuple_))
    print("Type of Set:", type(set_))
    print("Type of Dictionary:", type(dict_))
    print("Type of Frozen Set:", type(frozen_set))
    print("Type of Byte Array:", type(byte_array))
    print("Type of Memory View:", type(memory_view))
def global_variable():
    global global_var
    global_var = "I am a global variable"
    print(global_var)
def return_now(): 
    return "This is a return statement"

def len_string():
    string = "Hello, World!"
    length = len(string)
    print("Length of the string:", length)
def in_string():
    string = "Hello, World!"
    substring = "World"
    in_bool = bool(substring in string)
    print(f"Is '{substring}' in the string? {in_bool}")
def not_in_string():
    string = "Hello, World!"
    substring = "Python"
    not_in_bool = bool(substring not in string)
    print(f"Is '{substring}' not in the string? {not_in_bool}")
def format_string():
    #We can use `format()` to insert other data types into a string.
    age = 10 
    txt_1 = "My name is John, and I am {}"
    print(txt_1.format(age))
    #We can use `format()` to insert various other data types.
    my_age = 10
    father_age = 50
    txt_2 = "My name is John, and I am {}, my father is {}"
    print(txt_2.format(my_age, father_age))
    ### We can arrange the location Start from 0, not 1
    txt_3 = "My father is {1}, and I am {0}"
    print(txt_3.format(my_age, father_age))

if __name__ == "__main__":    
    print_values()
    type_in_data_type()
    global_variable()
    print("Return value:", return_now())
    len_string()
    in_string()
    not_in_string()
    format_string()