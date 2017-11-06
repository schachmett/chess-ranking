#!/usr/bin/env python3
"""calculates chess tables"""

import sys
import datetime
import argparse

import matplotlib.pyplot as plt
import numpy as np

NAMEFILE = "names.txt"
GAMESFILE = "games.txt"

GLICKO = True                   # use glicko system or not, overwritten by
                                # cmd argument

STARTING_ELO = 1500
DEFAULT_K_FACTOR = 20           # only applies for non-glicko: K*E(s)=elodelta
ELO_DIFF = 400                  # rating diff of 2 people at which E(s)=1/11

STARTING_RD = 350
APPROX_RD = 60                  # mean RD of frequent players estimate
UNCERT_TIME = 10                # time perdiods after which RD -> STARTING_RD
MIN_RD = 50                     # minimum RD

PENALTY = 0.00                  # penalty per inactive day as fraction of
                                # (elo - PENALTY_CUTOFF)
EXP_PENALTY = 0.2               # effective penalty =
                                # PENALTY*exp(EXP_PENALTY*(inactive periods-1))
MAX_PENALTY = 20
PENALTY_CUTOFF = STARTING_ELO * 0.75
                                # below this, you don't get penalty
BONUS = 0                       # bonus for playing per period

#############################################################################

GLICKO_C = np.sqrt((STARTING_RD ** 2 - APPROX_RD ** 2) / UNCERT_TIME)
GLICKO_Q = np.log(10)/ELO_DIFF
__dates__ = []                  # list of playing dates for determining RD

def main():
    # pylint: disable=global-statement
    """main stuff"""
    global GLICKO
    GLICKO = parse_args(sys.argv[1:])
    print(GLICKO)
    names = read_playernames(NAMEFILE)
    players = []
    for name in names:
        player = Player(name)
        player.fullname = names[name]
        players.append(player)
    league = League(players)
    Game.league = league
    games = read_gamestxt(GAMESFILE)
    whitewin = 0
    blackwin = 0
    remis = 0
    for gameday, date in enumerate(__dates__):
        period_games = [game for game in games if game.date == date]
        for game in period_games:
            game.play()
            if game.winner_id == 0:
                whitewin += 1
            elif game.winner_id == 1:
                blackwin += 1
            else:
                remis += 1
        for player in league.players:
            player.calculate_period(date)
        for player in league.players:
            player.apply_period()
        print("\n" + "-"*51)
        datestring = date.strftime("%A, %d. %B %Y:")
        print("  Day {}, {:30} {} games\n"
              "".format(gameday, datestring, len(period_games)))
        if GLICKO:
            print("{:^12} {:>12} {:>12} {:>12}"
                  "".format("Player", "Elo", "RD", "Days"))
        else:
            print("{:^16} {:>12}     {:>16}"
                  "".format("Player", "Elo", "Days"))
        print("-"*51)
        league.show_table()
        print("-"*51)

    total = blackwin + whitewin + remis
    print("-"*51)
    print("{:.2f}% white winning \n{:.2f}% black winning \n{:.2f}% remis in\n"
          "{:d} games"
          "".format(whitewin / total * 100, blackwin / total * 100,
                    remis / total * 100, total))

    for player in league.players:
        plt.plot(player.elo,
                 label=("{:.0f} ({:+.0f}): {}"
                        "".format(player.elo[-1],
                                  player.elo[-1] - player.elo[-2],
                                  player.name)))

    #plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    plt.legend()
    plt.savefig("ratingsplot.png", bbox_inches="tight", dpi=200)
    # plt.show()


def parse_args(arglist):
    """Checks for command line argument GLICKO mode on or off."""
    parser = argparse.ArgumentParser(description="Schachtabelle")
    parser.add_argument("-g", "--glicko", action="store_true",
                        help="use glicko system")
    parser.add_argument("-p", "--plot", action="store_true",
                        help="plot results")
    args = parser.parse_args(arglist)
    for key, value in vars(args).items():
        if key == "glicko":
            return value
    return False

def read_gamestxt(fname):
    """read file with game results, format:
    date
    player1 player2 result1 result2
    p1      p2      r1      r2
    ...
    winner_id: 0=white, 1=black, else=remis"""
    games = []
    with open(fname) as file:
        dates = []
        date = (1970, 1, 1)
        for line in file:
            if line[0] == "#":
                continue
            elif line[0] == "2":
                date = (int(line[0:4]), int(line[4:6]), int(line[6:8]))
            elif len(line.split()) == 4:
                player1 = line.split()[0]
                player2 = line.split()[1]
                win2 = line.split()[3]
                winner_id = float(win2)
                game = Game(player1, player2, winner_id=winner_id, date=date)
                games.append(game)
                dates.append(datetime.date(*date))
        __dates__.clear()
        __dates__.extend(list(set(dates)))
        __dates__.sort()
    return games


def read_playernames(fname):
    """reads player names from a file in format:
    shortname   longname
    shortname2  longname2"""
    names = {}
    with open(fname) as file:
        for line in file:
            sname = line.split()[0]
            lname = line.split()[1]
            names[sname] = lname
    return names


def periods(now, games):
    """calculates game periods between two games, game2 being more recent"""
    last_game_date = games[-1].date
    for i, game in enumerate(games):
        if __dates__.index(now) <= __dates__.index(game.date):
            last_game_date = games[i-1].date
    return __dates__.index(now) - __dates__.index(last_game_date)


class Player:
    """player class, identifiable by name"""
    def __init__(self, name, elo=STARTING_ELO, rdev=STARTING_RD):
        self.name = name
        self.fullname = self.name
        self.games = []
        self.elo = [elo]
        self.rdev = [rdev]
        self.k_factor = DEFAULT_K_FACTOR
        self.buffer = [None, None]
        # self.rdev_buffer = None

    def expected(self, other):
        """expected result against other player"""
        ex_value = 1 / (1 + 10 ** (other.g_weight()
                                   * (other.elo[-1] - self.elo[-1])
                                   / ELO_DIFF))
        return ex_value

    def g_weight(self):
        """calculate g(RD) from glicko method"""
        if not GLICKO:
            return 1
        g_value = np.sqrt(1 + (3 * GLICKO_Q ** 2
                               * self.rdev[-1] ** 2
                               / np.pi ** 2)
                         ) ** -1
        return g_value

    def add_game(self, game):
        """adds game to history"""
        if game not in self.games:
            self.games.append(game)

    def calculate_period(self, now):
        """calculates new RD"""
        if not self.games:
            self.buffer[1] = self.rdev[-1]
            self.buffer[0] = (self.elo[-1]
                              - max(self.elo[-1] - PENALTY_CUTOFF, 0)
                              * PENALTY)
        elif not self.games[-1].date == now:
            non_played_periods = periods(now, self.games)
            rdev = min(np.sqrt(self.rdev[-1] ** 2
                               + GLICKO_C * non_played_periods),
                       STARTING_RD)
            if GLICKO:
                self.buffer[1] = rdev
            else:
                self.buffer[1] = 0
            self.buffer[0] = (self.elo[-1]
                              - max(self.elo[-1] - PENALTY_CUTOFF, 0)
                              * PENALTY
                              * np.exp(EXP_PENALTY
                                       * (non_played_periods - 1)))
        else:
            last_games = [game for game in self.games if game.date == now]
            d_comps = []
            r_comps = []
            for game in last_games:
                other = game.other_player(self)
                expected = self.expected(other)
                win_value = game.win_value(self)
                d_comps.append(other.g_weight() ** 2
                               * expected
                               * (1 - expected))
                r_comps.append(other.g_weight() * (win_value - expected))
            d2_weight = (GLICKO_Q ** 2 * sum(d_comps)) ** -1
            if GLICKO:
                self.buffer[1] = max(np.sqrt(1 / self.rdev[-1] ** 2
                                             + 1 / d2_weight
                                            ) ** -1,
                                     MIN_RD)
                self.buffer[0] = (self.elo[-1]
                                  + GLICKO_Q
                                  * self.buffer[1] ** 2
                                  * sum(r_comps)
                                  + BONUS)
            else:
                self.buffer[1] = 0
                self.buffer[0] = self.elo[-1] + sum(r_comps) * self.k_factor
            # if self.name == "ME":
            #     print(r_comps)
            #     print(GLICKO_Q * self.rdev_buffer ** 2)
            #     rdev_diff = self.rdev_buffer - self.rdev[-1]
            #     elo_diff = self.elo_buffer - self.elo[-1]
            #     print("{:^12}: elo {:+}, RD {:+}"
            #           "".format(self.fullname, elo_diff, rdev_diff))

    def apply_period(self):
        """stores new rdev and elo"""
        self.rdev.append(self.buffer[1])
        self.elo.append(self.buffer[0])

    def show_stats(self):
        """show a string for the league table"""
        gamedays = len(set([game.date for game in self.games]))
        elostring = " {:.0f} ({:+.0f})".format(self.elo[-1],
                                               self.elo[-1] - self.elo[-2])
        if GLICKO:
            statstring = ("{:^12} {:12} {:>12.0f} {:>12d}"
                          "".format(self.fullname,
                                    elostring,
                                    self.rdev[-1],
                                    gamedays))
        else:
            statstring = ("{:^16}      {:16} {:>11d}"
                          "".format(self.fullname,
                                    elostring,
                                    gamedays))
        return statstring


class Game:
    """game class"""
    league = None
    def __init__(self, white_name, black_name, winner_id=None, date=None):
        if isinstance(white_name, str):
            self.white = self.league.get_player(white_name)
        elif isinstance(white_name, Player):
            self.white = white_name
        if isinstance(black_name, str):
            self.black = self.league.get_player(black_name)
        elif isinstance(black_name, Player):
            self.black = black_name

        self.winner_id = winner_id
        if date is None:
            self.date = datetime.date.today()
        else:
            self.date = datetime.date(*date)
        self.played = False

    def play(self):
        """adds this game to the players' history"""
        self.black.add_game(self)
        self.white.add_game(self)

    def other_player(self, player):
        """gets other player of the game"""
        if self.white == player:
            return self.black
        return self.white

    def win_value(self, player):
        """gets s_j"""
        if self.winner_id == 0:
            if self.white == player:
                return 1
            return 0
        if self.winner_id == 1:
            if self.black == player:
                return 1
            return 0
        return 0.5


class League:
    """league class"""
    def __init__(self, players):
        namelist = [player.name for player in players]
        if len(set(namelist)) < len(namelist):
            raise TypeError("name taken doubly")
        self.players = players
        self.games = []

    def add_player(self, player):
        """add a player and tests if this player already exists"""
        namelist = [player.name for player in self.players]
        if player.name in namelist:
            print("name {} already taken".format(player.name))
            return
        self.players.append(player)

    def get_player(self, name):
        """get player by name"""
        for player in self.players:
            if player.name == name or player.fullname == name:
                return player
        print("player {} not found".format(name))

    def add_game(self, game):
        """add a game to the league and also play it"""
        self.games.append(game)

    def show_table(self):
        """show the ladder"""
        sorted_players = sorted(self.players,
                                key=lambda x: x.elo[-1],
                                reverse=True)
        for player in sorted_players:
            print(player.show_stats())

if __name__ == "__main__":
    main()
