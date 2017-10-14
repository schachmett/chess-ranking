#!/usr/bin/env python3
"""calculates chess tables"""
# pylint disable=C0103

import datetime

import matplotlib.pyplot as plt

NAMEFILE = "names.txt"
GAMESFILE = "games.txt"

def main():
    """main stuff"""
    names = read_playernames(NAMEFILE)
    players = []
    for name in names:
        player = Player(name)
        player.fullname = names[name]
        players.append(player)
    league = League(players)
    Game.league = league
    games = read_gamestxt(GAMESFILE)
    for game in games:
        game.play()
    print("\n" + "-"*38 + "\n")
    print("{:^12} {:>12} {:>12}".format("Player", "Elo", "Games"))
    print("-"*38)
    league.show_table()

    plt.plot((league.get_player("SF")).elohist)
    plt.plot((league.get_player("ME")).elohist)
    plt.plot((league.get_player("NB")).elohist)
    plt.plot((league.get_player("JIF")).elohist)
    plt.plot((league.get_player("LB")).elohist)
    plt.show()


def read_gamestxt(fname):
    """read file with game results, format:
    date
    player1 player2 result1 result2
    p1      p2      r1      r2
    ..."""
    games = []
    with open(fname) as file:
        date = (1970, 1, 1)
        for line in file:
            if len(line) == 8:
                date = (line[0:4], line[4:6], line[6:8])
            elif len(line.split()) == 4:
                player1 = line.split()[0]
                player2 = line.split()[1]
                # win1 = line.split()[2]
                win2 = line.split()[3]
                winner_id = float(win2)            # weiß: 0, schwarz: 1, remis != (0 or 1)
                game = Game(player1, player2, winner_id=winner_id, date=date)
                games.append(game)
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


class Player:
    """player class, identifiable by name"""
    def __init__(self, name, elo=1500):
        self.name = name
        self.elohist = [elo]
        self.elo = elo
        self.fullname = self.name
        self.k_factor = 20

    def expected(self, other):
        """expected result against other player"""
        ex_value = 1 / (1 + 10 ** ((other.elo - self.elo) / 400))
        return ex_value

    def addelo(self, elodiff):
        """add elo to own"""
        self.elo += elodiff
        self.elohist.append(self.elo)

    def show_stats(self):
        """show a string for the league table"""
        statstring = ("{:^12} {:>12.0f} {:>12d}"
                      "".format(self.fullname,
                                self.elo,
                                len(self.elohist) - 1))
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
        """play the game and adds it to the league"""
        if self.played:
            print("already played")
            return

        if self.winner_id == 0:
            diff_elo = (1 - self.white.expected(self.black))
            self.white.addelo(self.white.k_factor * diff_elo)
            self.black.addelo(self.black.k_factor * -diff_elo)
            winner = self.white
            loser = self.black
        elif self.winner_id == 1:
            diff_elo = (1 - self.black.expected(self.white))
            self.black.addelo(self.black.k_factor * diff_elo)
            self.white.addelo(self.white.k_factor * -diff_elo)
            winner = self.black
            loser = self.white
        else:
            diff_elo = (0.5 - self.white.expected(self.black))
            self.white.addelo(self.white.k_factor * diff_elo)
            self.black.addelo(self.black.k_factor * -diff_elo)
            if diff_elo > 0:
                winner = self.white
                loser = self.black
            else:
                winner = self.black
                loser = self.white

        if winner.k_factor == loser.k_factor:
            print("{:^12} {:>6.2f}   -> {:^12}"
                  "".format(loser.fullname,
                            abs(diff_elo * winner.k_factor),
                            winner.fullname))
        else:
            print("{:^12} {:>6.2f} | {:>6.2f}   -> {:^12}"
                  "".format(loser.fullname,
                            abs(diff_elo * loser.k_factor),
                            abs(diff_elo * winner.k_factor),
                            winner.fullname))
        self.played = True


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
            if player.name == name:
                return player
        print("player {} not found".format(name))

    def add_game(self, game):
        """add a game to the league and also play it"""
        game.play()
        self.games.append(game)

    def show_table(self):
        """show the ladder"""
        sorted_players = sorted(self.players, key=lambda x: x.elo, reverse=True)
        for player in sorted_players:
            print(player.show_stats())

if __name__ == "__main__":
    main()
