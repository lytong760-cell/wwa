import random
import cmath 
class Chat :
    def __init__(self, name) :
        self.name = name
    def __str__(self) :
        return self.name

def chat() :
    
    global x1, x2, x3
    x1 = random.randint(0,189)
    x2 = random.randint(0,189)
    x3 = random.randint(0,819)
    complex_num = complex(x1,x2,)
    abs_complex = abs(complex_num)
    vector_num = abs_complex


    
    vector = [
        [
            "hello",
            [
                [vector_num]*9 + [x3]
            ]
        ],
        [   "Hanami Nikata",
            [
                ":)"
            ]
        ],
    ]
    print(vector,'\n')
    encode_vector = str(vector).encode("utf-8")
    encode_vector_list = list(encode_vector)
    print(encode_vector_list)
def check_img() :
    img = open("/workspaces/wwa/Website/images (1).jpg", "rb")
    print(img.read())
    img.close()
def main(you, me ) :
    input_list_1 = []
    input_list_2 = []
    chat = True 
    while chat :
        you_input = input(f"{you}: ")
        ecode_you_chat = you_input.encode("utf-8")
        ecode_you_list = list(ecode_you_chat)
        print(ecode_you_list)
        input_list_1.append(you_input)
        my_input = input(f"{me}: ")
        ecode_my_chat = my_input.encode("utf-8")
        ecode_my_list = list(ecode_my_chat)
        print(ecode_my_list)
        input_list_2.append(my_input)
        if you_input == "exit" or my_input == "exit" :
            chat = False
        if you_input == "check" or my_input == "check" :
            check_img()





you = Chat(input("Enter your name: "))
me = Chat(input("Enter your name: "))
if __name__ == "__main__":    
    main(you,me)
    while True :
        chat()