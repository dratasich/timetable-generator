#!/usr/bin/python
##
# @date 22.01.2016
# @author Denise Ratasich
#
# @brief Generates a schedule for the OSUE test.
#
# This script makes following assumptions:
#
# - Tutors supervise only the lab rooms. For the first test, the schedule for
#   the seminar room won't be generated.
# - Test length is a multiple of slot length.
# - Preparation time, i.e., time in the first room at 2nd test, is 1 slot
#   length.
# - 1:1 matching of tutor and room (e.g., a tutor cannot supervise two rooms).
#
# You will have to install pyevolve (http://pyevolve.sourceforge.net/) to use
# this script. The schedule is optimized by genetic algorithms.
#

import argparse
import logging
import datetime
import random
import math
import re
from pyevolve import G1DList, GSimpleGA

from timetable import Slot, Timetable
import evaluation


####################
# global variables #
####################

# number of tutors should be >= number of rooms (here: TILAB with 4 rooms); may
# be overwritten by a command line argument, the following assignment is the
# default value
tutors = ['Benedikt', 'Fabjan', 'Linus', 'Lukas', 'Mario', 'Neu']

# pool of evaluation functions for optimization
eval_func_dict = {
   'piecewise_linear': evaluation.piecewise_linear,
   'fuzzy': evaluation.fuzzy,
}
eval_func_str = 'fuzzy' # default evaluation function

log_formatter = logging.Formatter('[%(levelname)s][%(name)s] %(message)s')

OUTPUT_FILENAME = 'test_timetable_schedule.txt'

# number of generations of evolutionary algorithm
GENERATIONS = 100


##########
# Script #
##########

# logging initialization
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


#
# Read configuration
#
desc = 'Generates test timetable.\n\n'
desc += 'This script uses the pyevolve module from http://pyevolve.sourceforge.net/' \
        ' implementing optimization with genetic algorithms. pyevolve needs Python' \
        '2.5+. For this script pyevolve 0.6rc has been installed via easy_install.'
parser = argparse.ArgumentParser(description=desc)
parser.add_argument('-t', '--test', type=int, choices=[1,2], default=1, 
                    help='Test number, default: 1st test.')
parser.add_argument('-g', '--groups', type=int, required=True,
                    help='Number of student groups for the test.')
parser.add_argument('start', type=str,
                    help='Start time and date of the test. Specify in format d.m.Y H:M, e.g., 22.01.2016 08:00.')
parser.add_argument('tutors', type=str, nargs='*', metavar='tutor', default=tutors,
                    help='Names of the tutors. Default tutors: ' + str(tutors))
parser.add_argument('-O', '--optimize', type=str, 
                    choices=['piecewise_linear', 'fuzzy'], default=eval_func_str,
                    help='Evaluation function of optimization, default: ' + eval_func_str)
args = parser.parse_args()

start = datetime.datetime.strptime(args.start, '%d.%m.%Y %H:%M')

# only lab rooms, i.e., rooms supervised by tutors
# (seminar room of test 1 is therefore missing)
# first room in test 2 is assumed to be for all groups (preparation room)
# first room in test 2 is occupied for 1 slot per group
# there must be at least 2 rooms in this list!
# rooms depend on the test number
if args.test == 1:
   rooms = ['R1', 'R2', 'R3', 'R4']
else:
   rooms = ['R4', 'R1', 'R2', 'R3']

if len(args.tutors) < len(rooms):
   raise Exception('Too few tutors specified. Number of tutors must be greater or equal number of rooms (4).')

tutors = args.tutors

eval_func_str = args.optimize

log.debug('config: %d. Test (in lab rooms) starts at %s.' % (args.test, start.strftime('%H:%M')))
log.debug('config: %d groups of students, %d rooms for computertest.' % (args.groups, len(rooms)))
log.debug('config: evaluation function of genetic optimization = %s' % (eval_func_str))


#
# Genetic algorithm
#

# Collects data about timetable.
t = Timetable(start, args.test, rooms, tutors, args.groups)

# Initialize evaluation functions if necessary.
if eval_func_str == 'fuzzy':
   evaluation.fuzzy_init(t)

##
# Apply genome (map tutor to slot).
##
def apply_genome(genome):
   # check if genome has equal size as total number of slots
   if len(genome) != len(t._slots):
      msg = 'Wrong length of genome (%d), must match total number of slots (%d).' % (len(genome), len(slots))
      raise RuntimeError(msg)
   # put tutors into slots
   for s in range(len(t._slots)):
      t._slots[s].set_tutor(t.tutors[genome[s]])

##
# Evaluation function.
#
# We want to give high score to timetables which satisfy the
# constraints. Global variable t is a timetable object and is used for
# chromosome evaluation.
##
def eval_func(chromosome):
   # map chromosome (a generated schedule) to the timetable
   apply_genome(chromosome)
   # evaluate score of the timetable
   score = eval_func_dict[eval_func_str](t, log.getEffectiveLevel())
   return score


# genome instance (first one)
genome = G1DList.G1DList(len(t.get_slots()))
genome.evaluator.set(eval_func)
genome.setParams(rangemin=0, rangemax=len(tutors)-1)

# create GA engine
ga = GSimpleGA.GSimpleGA(genome)
ga.initialize()
ga.setGenerations(GENERATIONS)

# do the evolution, with stats dump frequency of 10 generations
log.setLevel(logging.INFO)
ga.evolve(freq_stats=10)
log.setLevel(logging.DEBUG)

# # just test eval function
# genome = ga.getPopulation()[0]
# apply_genome(genome)


#
# Print results
#
best = ga.bestIndividual()
apply_genome(best)
print t
eval_func(best)

t.print_timetable(OUTPUT_FILENAME)

# print info for next steps
print '**********************************************************'
print 'Complete ' + OUTPUT_FILENAME + ' if necessary.'
print 'Print PDF of schedule with:'
if args.test == 1:
   room_nr = re.findall(r'\d+', rooms[0])[0]
elif args.test == 2:
   room_nr = re.findall(r'\d+', rooms[1])[0]
print './test_timetable.sh ' + str(args.test) + ' "' + \
   start.strftime('%H:%M') + '" ' + \
   str(args.groups) + ' ' + \
   room_nr + ' ' + OUTPUT_FILENAME
print '**********************************************************'
