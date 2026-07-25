




import random
import cmath 
class Chat :
    def __init__(self, name) :
        self.name = name
    def __str__(self) :
        return self.name



input_list_1 = []
input_list_2 = []

    



    
    
   
def check_img() :
    img = open("/workspaces/wwa/Website/images (1).jpg", "rb")
    print(img.read())

    img.close()
    

    
            
def main(you, me ) :
    global input_list_1, input_list_2
    chat = True 
    while chat :
        you_input = input(f"{you}: ")
        ecode_you_chat = you_input.encode("utf-8")
        ecode_you_list = list(ecode_you_chat)
        print(ecode_you_list)
        input_list_1.append(you_input)
        print(input_list_1)
        print(f'{me }:{bot}')
        bot = random.randint(1,255 )
        [bot]*3
        
        ecode_my_chat = my_input.encode("utf-8")
        ecode_my_list = list(ecode_my_chat)
        print(ecode_my_list)
        bot = random.randint(1,255)
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
        
    

