from argparse import ArgumentParser  # pragma: no cover
from json import load, dump  # pragma: no cover
from traceback import print_exc  # pragma: no cover

from tqdm import tqdm  # pragma: no cover

try:  # pragma: no cover
    from common import set_response_data, get_response_data, GameMode
    from common import get_best_guess_updated, get_response_data_updated
    from common import PROGRESS, rec_build_best_tree
    from solver import solve_wordle, manual_guess, manual_response
    from solver import simulate, simulated_response, SessionInfo
    from data import load_all_data, save_all_data, clean_all_data
except ModuleNotFoundError:  # this is only here to help pytest find the module
    from wordle_autosolver_lite.common import set_response_data
    from wordle_autosolver_lite.common import get_best_guess_updated, GameMode
    from wordle_autosolver_lite.common import get_response_data_updated
    from wordle_autosolver_lite.common import get_response_data, PROGRESS
    from wordle_autosolver_lite.common import rec_build_best_tree
    from wordle_autosolver_lite.solver import solve_wordle, SessionInfo
    from wordle_autosolver_lite.solver import manual_guess, manual_response
    from wordle_autosolver_lite.solver import simulate, simulated_response


def parse_command_line_args() -> tuple[int, bool, bool, bool, str, int, bool,
                                       str, int, bool, bool, bool, bool]:
    """Parse all command line arguments using `argparse.ArgumentParser`."""
    parser = ArgumentParser(
        description=('Solve a Wordle game on one board or multiple by '
                     'calculating the best guesses at every step.'))
    parser.add_argument('--num', type=int, default=1,
                        help='number of simultaneous games (default: 1)')
    group1 = parser.add_mutually_exclusive_group()
    group1.add_argument('--nyt', action='store_true', default=False,
                        help=('only consider answers that are in the New York '
                              'Times official word list'))
    group1.add_argument('--hard', action='store_true', default=False,
                        help='use if playing on hard mode (default: False)')
    group1.add_argument('--master', action='store_true', default=False,
                        help=('only set this flag if the game does '
                              'not tell you which colors belong to '
                              'which letters (default: False)'))
    group1.add_argument('--liar', action='store_true', default=False,
                        help=('use if playing Fibble where one letter in each '
                              'response is always a lie (default: False)'))
    group2 = parser.add_mutually_exclusive_group()
    group2.add_argument('--play', action='store_true',
                        help=('set this flag to play a game of Wordle using '
                              'the command line'))
    group2.add_argument('--sim', type=int, default=0, metavar='MAX_SIMS',
                        help=('set this flag to simulate MAX_SIMS unique games'
                              ' and give resulting stats'))
    group3 = parser.add_mutually_exclusive_group()
    group3.add_argument('--continue', type=int, default=1,
                        metavar='LIMIT', dest='board_limit',
                        help=('set this flag to continue playing on multiple '
                              'boards up to the given number (max 500) '
                              '-- setting the limit to "-1" will test all '
                              'possible starting words to find the best one(s)'
                              ' (be aware that this process may be very slow)')
                        )
    group3.add_argument('--endless', action='store_true', dest='inf',
                        help='use to play the same game over and over')
    group3.add_argument('--challenge', action='store_true', dest='stro',
                        help=('play the daily wordle, dordle, quordle, and '
                              'octordle in order, using the answers from each '
                              'puzzle as the starting words for the next ('
                              'inspired by YouTube channel Scott Stro-solves)')
                        )
    parser.add_argument('--best', action='store_true',
                        help=('set this flag to generate a minimal guess tree '
                              '(be aware that this process may be very slow) '
                              'once completed, the program will continue as '
                              'normal using this generated tree to recommend '
                              'guesses'))
    parser.add_argument('--clean', action='store_true',
                        help=('empty the contents of "data/best_guess.json", '
                              '"data/responses.json", and each of their '
                              'variants to relieve some storage space (the '
                              'program will not execute any other commands '
                              'when this flag is set)'))
    parser.add_argument('--start', metavar='WORD', nargs='+', default=[],
                        help=('set this flag if there are certain words you '
                              'want to start with regardless of the response'))
    args = parser.parse_args()
    if args.clean:  # pragma: no cover
        clean_all_data()
        exit()
    lim = max(min(args.board_limit, 500), args.num)
    mode = GameMode()
    if args.hard:
        mode.hard = True
    elif args.master:
        mode.master = True
    elif args.liar:
        mode.liar = True
    if args.play:
        mode.play = True
    if args.inf:
        mode.endless = True
    return (args.num, lim, mode, args.nyt, args.start, args.sim,
            args.stro, args.best)


def main() -> None:  # pragma: no cover
    """Main entry point into the program."""
    # main variable initializations
    (n_games, lim, mode, nyt, start,
        sim, stro, best) = parse_command_line_args()
    (answers, guesses, _, freq,
        saved_best, resp_data) = load_all_data(mode.hard, mode.master,
                                               mode.liar, nyt)
    set_response_data(resp_data)
    auto_guess = manual_guess
    auto_response = simulated_response if mode.play else manual_response
    if mode.endless:
        lim = n_games + 1
    elif stro:
        n_games = 1
        lim = 8

    # main functions to call
    if best:
        tree = {}
        max_depth = 2
        while len(tree) == 0:
            tree = rec_build_best_tree(answers, guesses, start[0],
                                       mode, max_depth)
        with open('data/{}.json'.format(start[0]), 'w') as data:
            dump(tree, data, indent=2)
        saved_best = tree
    if sim > 0:
        session = SessionInfo(n_games, answers, guesses, saved_best, freq,
                              start, mode)
        simulate(session, sim, show=True)
    elif sim == -1:
        best_case = [-8, []]
        worst_case = {}
        with open('data/ordered_guesses.json', 'r') as ordered:
            worst_case = load(ordered)
        modified = sorted(answers, key=lambda x: worst_case[x])
        for starter in tqdm(modified, ascii=PROGRESS):
            session = SessionInfo(n_games, answers, guesses, saved_best, freq,
                                  [starter], mode)
            _, worst = simulate(session, len(answers), best_case[0], False)
            if worst == best_case[0]:
                best_case[1].append(starter)
            elif worst > best_case[0]:
                best_case[0] = worst
                best_case[1] = [starter]
        print(best_case)
    if sim != 0:
        save_all_data(session.hard, session.master, session.liar,
                      get_best_guess_updated(), saved_best,
                      get_response_data_updated(), get_response_data(), nyt)
        exit()
    while n_games <= lim:
        session = SessionInfo(n_games, answers, guesses, saved_best, freq,
                              start, mode)
        try:
            session = solve_wordle(session, auto_guess, auto_response, True)
        except Exception:
            print_exc()
            print()
            print(session)
            exit(1)
        if n_games == lim:
            break
        if stro:
            start = session.solved
    save_all_data(mode.hard, mode.master, mode.liar, get_best_guess_updated(),
                  saved_best, get_response_data_updated(), get_response_data(),
                  nyt)
