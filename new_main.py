
from datetime import date, timedelta
import argparse

from file_io import load_population_from_natural_file
from file_io import load_population_from_vp_file
from file_io import vp_to_natural

from new_pop_loader import Processor

def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Arguments: file path to write to, vp_format'
        )
    parser.add_argument(
        '--fp',
        type=str,
        help='filepath for input file'
        )
    parser.add_argument(
        '--vp',
        type=str,
        help='Whether to read in VP or native format',
        default='true'
        )
    parser.add_argument(
        '--m',
        type=str,
        help='Whether to process monthly (quarterly is default)',
        default='false'
        )
    args = parser.parse_args()
    return args

def main() -> int:
    args = get_args()
    print(f'{args.vp=}')
    vp = True if args.vp.lower()[0] == 't' else False
    filename = args.fp
    print(f'load {filename}')
    if vp:
        pop = load_population_from_vp_file(filename)
        nat_file = filename[:-4]
        nat_file += '_nat.csv'
        #print(f'{nat_file=}')
        #vp_to_natural(filename, nat_file)
    else:
        pop = load_population_from_natural_file(filename)

    monthly = args.m != 'false'

    substances = [
        {'drug': .25},
        {'alcohol': .1},
    ]
    process = Processor(pop, monthly, substances)
    r_predictions = process.process_substances_r(True)
    f_predictions = process.process_substances_f(True)

    for name in r_predictions:
        print(f'{name[0:4]} -> {r_predictions[name]=}')
    for name in r_predictions:
        print(f'{name[0:4]} -> {f_predictions[name]=}')

    process2 = Processor(pop, monthly, substances)
    process2.set_guesses_r(r_predictions)
    process2.set_guesses_f(f_predictions)

    #print('ROLL')
    #for s in process2.substances_r:
    #    print(f'->{s.predicted_tests=}')
    #print('FAA')
    #for s in process2.substances_f:
    #    print(f'->{s.predicted_tests=}')

    r_predictions_2 = process2.process_substances_r(True)
    f_predictions_2 = process2.process_substances_f(True)

    print('ROLL')
    for name in r_predictions_2:
        print(f'old: {name[0:4]} -> {r_predictions[name]} = {sum(r_predictions[name])}')
        print(f'new: {name[0:4]} -> {r_predictions_2[name]} = {sum(r_predictions_2[name])}')
    print('FAA')
    for name in f_predictions_2:
        print(f'old: {name[0:4]} -> {f_predictions[name]} = {sum(f_predictions[name])}')
        print(f'new: {name[0:4]} -> {f_predictions_2[name]} = {sum(f_predictions_2[name])}')

if __name__ == "__main__":
    main()
