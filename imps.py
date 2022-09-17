IMPS_LEFT = [20, 50, 90, 130, 170, 220, 270, 320,
             370, 430, 500, 600, 750, 900, 1100, 1300,
             1500, 1750, 2000, 2250, 2500, 3000, 3500, 4000]


def imps(score):
    score_abs = abs(score)
    for index, left in enumerate(IMPS_LEFT):
        if score_abs < left:
            return index * (-1) ** (score < 0)
