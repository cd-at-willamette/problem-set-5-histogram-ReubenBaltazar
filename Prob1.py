from pgl import *
# Collaborators: Anika Neu
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
    for i in range (len(hist)):
        print(f"{i}:{'*'* hist[i]}")
print_histogram(histogram)

#1c
def graph_histogram(hist:list[int], width:int, height:int) -> None:
    gw=GWindow(width,height)
    max_value=max(hist)
    bar_width=width/len(hist)


    for i, value in enumerate(hist):
        bar_height = (value / max_value) * height  
        bar = GRect(i * bar_width, height - bar_height, bar_width, bar_height)
        bar.set_filled(True)
        bar.set_color("red")
        gw.add(bar)

graph_histogram(create_histogram_array(PI_DIGITS), 400, 400)

# Some testing printouts for your use!
PI_DIGITS = [3,1,4,1,5,9,2,6,5,3,5,5,8,9,7,9]
hist = create_histogram_array(PI_DIGITS)
print(hist)
#print_histogram(hist) # uncomment to test
#graph_histogram(hist, 400, 400) # uncomment to test

