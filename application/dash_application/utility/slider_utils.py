from gsiqcetl.column import BamQcColumn

BAMQC_COL = BamQcColumn

def frange(min, max, step):
    range = []
    i = min
    while i <= max:
        range.append(round(i, 2))
        i += step
    return range

def percentageOf(data, bamqc_column):
    return (data[bamqc_column] / data[BAMQC_COL.TotalReads]) * 100