
class Scoring:
    imp = "IMPs"
    max = "MPs"
    ximp = "Cross-IMPs"
    match = "Team Match IMPs"

    @staticmethod
    def all():
        return [Scoring.max, Scoring.imp, Scoring.ximp, Scoring.match]

    @staticmethod
    def re():
        return "({})".format(")|(".join(Scoring.all()).replace("-", "\-"))
