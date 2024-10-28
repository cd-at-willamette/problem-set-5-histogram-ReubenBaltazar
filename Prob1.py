from pgl import *

#1a
def create_histogram_array(data:list[int])->list[int]:
    histogram=[0]*(max(data)+1)
    for digit in data:
        histogram[digit]+=1
    return histogram
PI_DIGITS=[3,1,4,1,5,9,2,6,5,3,5,5,8,9,7,9]
histogram=create_histogram_array(PI_DIGITS)
print(histogram)

#1b
def print_histogram(hist:list[int]) -> None:
    pass

#1c
def graph_histogram(hist:list[int], width:int, height:int) -> None:

    def my_rect(x,y,w,h,color):
        rect = GRect(x,y,w,h)
        rect.set_filled(True)
        rect.set_color(color)
        gw.add(rect)

    pass

# Some testing printouts for your use!
PI_DIGITS = [3,1,4,1,5,9,2,6,5,3,5,5,8,9,7,9]
hist = create_histogram_array(PI_DIGITS)
print(hist)
#print_histogram(hist) # uncomment to test
#graph_histogram(hist, 400, 400) # uncomment to test

