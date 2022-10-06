import math
IMPS_LEFT = [20, 50, 90, 130, 170, 220, 270, 320,
             370, 430, 500, 600, 750, 900, 1100, 1300,
             1500, 1750, 2000, 2250, 2500, 3000, 3500, 4000]


def imps(score):
    score_abs = abs(score)
    for index, left in enumerate(IMPS_LEFT):
        if score_abs < left:
            return index * (-1) ** (score < 0)


def vp(imps, boards):
    """https://www.bridgebase.com/forums/topic/55389-wbf-vp-scale-changes/page__p__667202#entry667202"""
    print(imps, boards)
    phi = (5 ** .5 - 1) / 2
    b = 15 * (boards ** .5)
    margin = abs(imps)
    vp_winner = 10 + 10 * ((1 - phi ** (3 * margin / b)) / (1 - phi ** 3))
    vp_winner = round(math.floor(vp_winner * 1000) / 1000, 2)
    vp_loser = 20 - vp_winner
    return vp_winner if imps > 0 else vp_loser
