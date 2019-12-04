def frange(min, max, step):
    range = []
    i = min
    while i <= max:
        range.append(round(i, 2))
        i += step
    return range

def percentage_of(data, numerator_col, denominator_col):
    return (data[numerator_col] / data[denominator_col]) * 100
