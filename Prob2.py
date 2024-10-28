##################################################
# Name:
# Collaborators:
# Estimate of time spent (hr):
##################################################

def is_magic_square(array:list[list[int]]) -> bool:
    n = len(array)
    for row in array:
        if len(row) != n:
            return False
    target_sum = sum(array[0])

    for row in array:
        if sum(row) != target_sum:
            return False

    for col in range(n):
        col_sum = sum(array[row][col] for row in range(n))
        if col_sum != target_sum:
            return False

    main_diag_sum = sum(array[i][i] for i in range(n))
    if main_diag_sum != target_sum:
        return False

    anti_diag_sum = sum(array[i][n - i - 1] for i in range(n))
    if anti_diag_sum != target_sum:
        return False

    return True

small = [[8,1,6],[3,5,7],[4,9,2]]
print(is_magic_square(small))

