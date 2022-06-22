from argparse import ArgumentParser
from json import load, dump

from tqdm import tqdm


try:
    from common import *
    from solver import *
    from data import *
except ImportError as e:
    from .common import *
    from .solver import *
    from .data import *


def parse_command_line_args() -> tuple[int, bool, bool, bool, str, int, str,
                                       int, bool, bool, bool, bool]:
    """Parse all command line arguments using `argparse.ArgumentParser`."""
    parser = ArgumentParser(
        description=('Solve a Wordle game on one board or multiple by '
                     'calculating the best guesses at every step.'))
    parser.add_argument('-n', type=int, default=1,
                        help='number of simultaneous games (default: 1)')
    group1 = parser.add_mutually_exclusive_group()
    group1.add_argument('-nyt', action='store_true', default=False,
                        help=('only consider answers that are in the New York '
                              'Times official word list'))
    group1.add_argument('-hard', action='store_true', default=False,
                        help='use if playing on hard mode (default: False)')
    group1.add_argument('-master', action='store_true', default=False,
                        help=('only set this flag if the game does '
                              'not tell you which colors belong to '
                              'which letters (default: False)'))
    group1.add_argument('-liar', action='store_true', default=False,
                        help=('use if playing Fibble where one letter in each '
                              'response is always a lie (default: False)'))
    parser.add_argument('-sim', type=int, default=0, metavar='MAX_SIMS',
                        help=('set this flag to simulate MAX_SIMS unique games'
                              ' and give resulting stats'))
    group3 = parser.add_mutually_exclusive_group()
    group3.add_argument('-continue', type=int, default=1,
                        metavar='LIMIT', dest='board_limit',
                        help=('set this flag to continue playing on multiple '
                              'boards up to the given number (max 500) '
                              '-- setting the limit to "-1" will test all '
                              'possible starting words to find the best one(s)'
                              ' (be aware that this process may be very slow)')
                        )
    group3.add_argument('-endless', action='store_true', dest='inf',
                        help='use to play the same game over and over')
    group3.add_argument('-challenge', action='store_true', dest='stro',
                        help=('play the daily wordle, dordle, quordle, and '
                              'octordle in order, using the answers from each '
                              'puzzle as the starting words for the next ('
                              'inspired by YouTube channel Scott Stro-solves)')
                        )
    parser.add_argument('-best', action='store_true',
                        help=('set this flag to generate a minimal guess tree '
                              '(be aware that this process may be very slow) '
                              'once completed, the program will continue as '
                              'normal using the '))
    parser.add_argument('-clean', action='store_true',
                        help=('empty the contents of "data/best_guess.json", '
                              '"data/responses.json", and each of their '
                              'variants to relieve some storage space (the '
                              'program will not execute any other commands '
                              'when this flag is set)'))
    parser.add_argument('-start', metavar='WORD', nargs='+', default=[],
                        help=('set this flag if there are certain words you '
                              'want to start with regardless of the response'))
    args = parser.parse_args()
    if args.clean:
        clean_all_data()
        exit()
    lim = max(min(args.board_limit, 500), args.n)
    ret = (args.n, args.hard, args.master, args.liar, lim, args.nyt,
           args.start, args.sim, args.inf, args.stro, args.best)
    return ret


# main variable initializations
(n_games, hard, master, liar, lim, nyt,
    start, sim, inf, stro, best) = parse_command_line_args()
(answers, guesses, n_guesses, freq,
    saved_best, resp_data) = load_all_data(hard, master, liar, nyt)
if len(resp_data) == 0:
    precalculate_responses(guesses, answers, master)
set_response_data(resp_data)
if best:
    tree = {}
    max_depth = 2
    while len(tree) == 0:
        tree = rec_build_best_tree(answers, guesses, start[0], master,
                                   liar, max_depth)
    with open('data/{}.json'.format(start[0]), 'w') as data:
        dump(tree, data, indent=2)
    saved_best = tree
if inf:
    lim = n_games + 1
elif stro:
    n_games = 1
    lim = 8

# main functions to call
if sim > 0:
    simulate(saved_best, freq, answers, guesses, start, n_games, hard,
             master, liar, sim)
    exit()
elif sim == -1:
    best_case = [-8, []]
    worst_case = {}
    with open('data/ordered_guesses.json', 'r') as ordered:
        worst_case = load(ordered)
    modified = sorted(answers, key=lambda x: worst_case[x])
    for starter in tqdm(modified, ascii=progress):
        _, worst = simulate(saved_best, freq, answers, guesses,
                            [starter], n_games, hard, master, liar,
                            len(answers), best_case[0], False)
        if worst == best_case[0]:
            best_case[1].append(starter)
        elif worst > best_case[0]:
            best_case[0] = worst
            best_case[1] = [starter]
    print(best_case)
    exit()
solution = [], []
while n_games <= lim:
    solution = solve_wordle(saved_best, freq, answers, guesses, start,
                            n_games, hard, master, liar, inf,
                            manual_guess, manual_response, True)
    if n_games == lim:
        break
    if stro:
        start = solution[0]
save_all_data(hard, master, liar, get_best_guess_updated(), saved_best,
              get_response_data_updated(), get_response_data(), nyt)
