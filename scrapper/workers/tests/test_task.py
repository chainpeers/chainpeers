from time import sleep
import random
test_array = 'qwertyuiopasdfghjklzxcvbnm'

def task():
    sleep(1)
    first = random.choice(test_array)
    second = random.choice(test_array)
    third = random.choice(test_array)
    return [first, second, third]

if __name__ == '__main__':
    print(task())
