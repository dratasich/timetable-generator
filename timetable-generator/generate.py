#!/usr/bin/python
#
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

####################
# global variables #
####################

# number of tutors should be >= number of rooms (here: TILAB with 4 rooms); may
# be overwritten by a command line argument, the following assignment is the
# default value
tutors = ['Benedikt', 'Fabjan', 'Linus', 'Lukas', 'Mario', 'Neu']

log_formatter = logging.Formatter('[%(levelname)s][%(name)s] %(message)s')

OUTPUT_FILENAME = 'test_timetable_schedule.txt'

# length in minutes of Slots and Tests
SLOTLEN_TEST1 = 20
TESTLEN_TEST1 = 100 # must be a multiple of slotlen
SLOTLEN_TEST2 = 30
TESTLEN_TEST2 = 120

# number of generations of evolutionary algorithm
GENERATIONS = 100

###########
# classes #
###########

##
# Smallest unit of a timetable.
##
class Slot:
   ##
   # Constructor
   ##
   def __init__(self, start):
      self.start = start
      self.group = -1
      self.tutor = "<not yet set>"

   ##
   # Set tutor.
   ##
   def set_tutor(self, tutor):
      self.tutor = tutor

   ##
   # Set group.
   ##
   def set_group(self, group):
      self.group = group

   ##
   # Returns true if slots have the same start time, otherwise false.
   ##
   def is_concurrent(self, otherSlot):
      if self.start == otherSlot.start:
         return true
      return false

   ##
   # Returns string representation of a slot.
   ##
   def __repr__(self):
      return '%s: G%02d (%s)' % (self.start, self.group, self.tutor)

##
# Stores slots and provides quality measures of the schedule.
##
class Timetable:
   ##
   # Constructor
   ##
   def __init__(self, start, test, rooms, tutors, num_groups):
      # init logger for this class
      self._log = logging.getLogger("Timetable")
      self._log.setLevel(logging.DEBUG)

      self._log.info('Initialize timetable.')
      self.test = test
      self.rooms = rooms
      self.tutors = tutors
      self.num_groups = num_groups

      if test == 1:
         self.testlen = TESTLEN_TEST1
         self.slotlen = SLOTLEN_TEST1
         # preparation room is missing so decrease testlen by 1 slot
         num_slots_total = self.num_groups * (self.testlen-self.slotlen) / self.slotlen
         # index of first lab room in 'rooms'
         lab_rooms_first = 0
         # number of lab rooms
         lab_rooms = len(rooms)
      elif test == 2:
         self.testlen = TESTLEN_TEST2
         self.slotlen = SLOTLEN_TEST2
         num_slots_total = self.num_groups * self.testlen / self.slotlen
         # index of first lab room in 'rooms' (first room is preparation / mc test)
         lab_rooms_first = 1
         # remaining rooms are lab rooms
         lab_rooms = len(rooms)-1
      else:
         raise RuntimeError('Wrong test number [1,2].')    


      self._log.debug('Generate slots for timetable.')

      # calculate number of slots per room
      num_slots_per_room = {}
      if test == 2:
         # first room is for preparation of all groups, preparation time is 1 slot
         num_slots_per_room[rooms[0]] = num_groups
      # lab rooms: groups are distributed among rooms
      min_groups_per_room = int(num_groups / lab_rooms)
      residual_groups = num_groups % lab_rooms
      slots_per_group = (self.testlen-self.slotlen) / self.slotlen
      self._log.debug('min groups per room: ' + str(min_groups_per_room))
      self._log.debug('residual groups: ' + str(residual_groups))
      self._log.debug('slots per group in lab room: ' + str(slots_per_group))
      for r in range(lab_rooms_first, len(rooms)):
         groups_per_room = min_groups_per_room
         if r-lab_rooms_first < residual_groups:
            groups_per_room = groups_per_room + 1
         num_slots_per_room[rooms[r]] = groups_per_room * slots_per_group
         self._log.debug(rooms[r] + ' holds ' + str(groups_per_room) + ' groups.')

      # initialize slot matrix (with None)
      max_slots_per_room = max(num_slots_per_room.values()) + lab_rooms
      self._log.debug('max slots per room: ' + str(max_slots_per_room))
      self._slot_matrix = [[None for x in range(max_slots_per_room)] for x in range(len(rooms))]

      # create slots
      self._slots = []
      slot_offset = 0
      for r in range(len(rooms)):
         # calculate time of first slot in room
         r_start = start + datetime.timedelta(minutes = (self.slotlen*slot_offset))
         room = rooms[r]
         for s in range(0, num_slots_per_room[room]):
            s_start = r_start + datetime.timedelta(minutes = (self.slotlen * s))
            slot = Slot(s_start)
            # add slot to slot list
            self._slots.append(slot)
            # add slot to slot matrix too
            self._slot_matrix[r][s+slot_offset] = slot
         # shift start time for next room
         slot_offset += 1

      # initialize slots with groups
      rows = len(self._slot_matrix)
      cols = len(self._slot_matrix[0])
      # preparation room for test 2
      if test == 2:
         for c in range(cols):
            if self._slot_matrix[0][c] == None:
               continue
            self._slot_matrix[0][c].set_group(c)
      # lab rooms
      for r in range(lab_rooms_first, rows):
         group = r-lab_rooms_first # set group which starts in this room
         cnt_slots = 0
         for c in range(cols):
            if self._slot_matrix[r][c] == None:
               continue
            self._slot_matrix[r][c].set_group(group)
            cnt_slots += 1
            if cnt_slots == slots_per_group:
               group += lab_rooms
               cnt_slots = 0
      
      self._log.debug('Initial timetable:\n' + str(self))

   ##
   # Returns slots as list.
   ##
   def get_slots(self):
      return self._slots

   ##
   # Apply genome (set tutors in slot).
   ##
   def apply_genome(self, genome):
      # check if genome has equal size as total number of slots
      if len(genome) != len(self._slots):
         msg = 'Wrong length of genome (%d), must match total number of slots (%d).' % (len(genome), len(self._slots))
         raise RuntimeError(msg)
      # put tutors into slots
      for s in range(len(self._slots)):
         self._slots[s].set_tutor(self.tutors[genome[s]])

   ##
   # Prints the schedule to a file.
   ##
   def print_timetable(self, filename):
      rows = len(self._slot_matrix)
      cols = len(self._slot_matrix[0])
      a_file = open(filename, 'w')

      # print schedule sorted by room
      for r in range(rows):
         s_last = None
         for c in range(cols):
            if self._slot_matrix[r][c] == None:
               continue
            # current slot
            s = self._slot_matrix[r][c]
            if s_last == None:
               s_last = s # set s_last to the first slot in the row
            # new line when tutor changes
            if s.tutor != s_last.tutor:
               line = self.rooms[r] + ',' + \
                      s_last.tutor + ',' + \
                      s_last.start.strftime('%H:%M') + ',' + \
                      s.start.strftime('%H:%M') + '\n'
               a_file.write(line)
               s_last = s
         # finalize room
         end = s.start + datetime.timedelta(minutes = (self.slotlen))
         line = self.rooms[r] + ',' + \
                s_last.tutor + ',' + \
                s_last.start.strftime('%H:%M') + ',' + \
                end.strftime('%H:%M') + '\n\n'
         a_file.write(line)

      a_file.close()

   ##
   # Returns a string representation of the timetable.
   ##
   def __repr__(self):
      ret = ''

      # # timetable as list
      # ret += '\nSlots:\n'
      # for slot in self._slots:
      #    ret += '%s\n' % (slot)
      # ret += '\n'

      # timetable as matrix (overlap of slots visible)
      ret += '\nTimetable (groups):\n'
      rows = len(self._slot_matrix)
      cols = len(self._slot_matrix[0])
      for r in range(rows):
         ret += '       '
         for s in range(cols):
            ret += '+----'
         ret += '+\n'
         ret += '  %3s  ' % (rooms[r])
         for s in range(cols):
            group = '  '
            if self._slot_matrix[r][s] != None:
               group = '%2d' % (self._slot_matrix[r][s].group)
            ret += '| %s ' % (group)
         ret += '|\n'
         ret += '       '
         for s in range(cols):
            ret += '+----';
         ret += '+\n'
      
      ret += '\nTimetable (tutors):\n'
      rows = len(self._slot_matrix)
      cols = len(self._slot_matrix[0])
      for r in range(rows):
         ret += '       '
         for s in range(cols):
            ret += '+----'
         ret += '+\n'
         ret += '  %3s  ' % (rooms[r])
         for s in range(cols):
            tutor = '  '
            if self._slot_matrix[r][s] != None:
               tutor = self._slot_matrix[r][s].tutor
            ret += '| %.2s ' % (tutor)
         ret += '|\n'
         ret += '       '
         for s in range(cols):
            ret += '+----';
         ret += '+\n'

      # number of slots per tutor
      ret += '\n tutor     | #slots | testlen | #overlaps'
      ret += '\n-----------+--------+---------+-----------\n'
      for tutor in self.tutors:
         ret += '%10.10s | %6d | %7d | %9d\n' % (tutor, 
                                           self.count_slots_of_tutor(tutor),
                                           self.get_test_length_for_tutor(tutor),
                                           self.count_overlaps_of_tutor(tutor))

      # count tutors in a row
      ret += '\nNumber of tutor-changes: %d\n' % (self.count_tutor_changes())

      return ret

   #
   # quality measures of this timetable start here ...
   #

   ##
   # Returns number of slots for a specific tutor.
   ##
   def count_slots_of_tutor(self, tutor):
      cnt = 0
      for slot in self._slots:
         if slot.tutor == tutor:
            cnt += 1
      return cnt

   ##
   # Returns slots with same start time.
   ##
   def get_concurrent_slots(self, start_time):
      rows = len(self._slot_matrix)
      cols = len(self._slot_matrix[0])
      slots = []
      # search for column of slots with start_time
      for c in range(cols):
         if self._slot_matrix[0][c] == None:
            continue
         if self._slot_matrix[0][c].start == start_time:
            # found right column, save column to slot array
            for r in range(rows):
               if self._slot_matrix[r][c] != None:
                  slots.append(self._slot_matrix[r][c])
            break
      return slots

   ##
   # Returns number of overlapping slots of a tutor.
   ##
   def count_overlaps_of_tutor(self, tutor):
      cnt = 0
      # go through slots of tutor
      slots = filter(lambda s: s.tutor == tutor, self._slots)
      for slot in slots:
         # check concurrent slots
         cc_slots = self.get_concurrent_slots(slot.start) # current slot including
         cc_slots = filter(lambda s: s.tutor == tutor, cc_slots)
         if len(cc_slots) > 1:
            cnt += 1
      return cnt

   ##
   # Returns the difference between last and first slot of a tutor (in number
   # of slots), i.e., overall time in slots the tutor supervises the test.
   ##
   def get_test_length_for_tutor(self, tutor):
      slots = filter(lambda s: s.tutor == tutor, self._slots)
      slots = sorted(slots, key=lambda s: s.start.hour*60+s.start.minute)
      # tutors has slots?
      if len(slots) == 0:
         return 0
      # get min/max start time
      min_slot = slots[0]
      max_slot = slots[len(slots)-1]
      return (max_slot.start - min_slot.start).seconds/60 / self.slotlen + 1

   ##
   # Count how many times the tutor changes in a room.
   ##
   def count_tutor_changes(self):
      rows = len(self._slot_matrix)
      cols = len(self._slot_matrix[0])
      changes = 0
      for r in range(rows):
         for c in range(cols-1):
            if self._slot_matrix[r][c] == None or self._slot_matrix[r][c+1] == None:
               continue
            if self._slot_matrix[r][c].tutor != self._slot_matrix[r][c+1].tutor:
               changes += 1
      return changes

   ##
   # Count number of pauses in slots of a tutor.
   ##
   def count_tutor_holes(self):
      holes = 0
      for t in self.tutors:
         slots = filter(lambda s: s.tutor == t, self._slots)
         slots = sorted(slots, key=lambda s: s.start.hour*60+s.start.minute)
         for i in range(len(slots)-1):
            # ignore overlapping slots
            if slots[i].start == slots[i+1].start:
               continue
            # count holes (calculate from time difference)
            holes += (slots[i+1].start - slots[i].start).seconds/60/self.slotlen - 1
      return holes
               
   ##
   # Returns pause offset to center of overall test time of a tutor.
   ##
   def pause_slots_of_tutor(self, tutor):
      slots = filter(lambda s: s.tutor == tutor, self._slots)
      starts = map(lambda s: s.start, slots)
      starts.sort()
      # TODO
      return []

   ##
   # Returns pause offset to center of overall test time of a tutor.
   ##
   def pause_offset_to_testcenter_of_tutor(self, tutor):
      # TODO
      return 0



##
# Generating the timetable really starts ...
##

# logging initialization
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

# read config
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
   # seminar room is missing, so shift start time for lab rooms
   lab_start = start + datetime.timedelta(minutes = SLOTLEN_TEST1)
else:
   rooms = ['R4', 'R1', 'R2', 'R3']
   lab_start = start

if len(args.tutors) < len(rooms):
   raise Exception('Too few tutors specified. Number of tutors must be greater or equal number of rooms (4).')

tutors = args.tutors

log.debug('config: %d. Test (in lab rooms) starts at %s.' % (args.test, start.strftime('%H:%M')))
log.debug('config: %d groups of students, %d rooms for computertest.' % (args.groups, len(rooms)))

# Collects data about timetable.
t = Timetable(lab_start, args.test, rooms, tutors, args.groups)

# Evaluation function, we want to give high score to timetables which satisfy
# the constraints. Global variable t is a timetable object and is used for
# chromosome evaluation.
def eval_func(chromosome):
   score = 0.0
   log.debug('score: %.2f' %(score))

   # map chromosome (a generated schedule) to the timetable
   t.apply_genome(chromosome)

   # equal number of slots for each tutor
   weight = 5.0
   maximum = len(t.get_slots()) * (len(t.tutors))
   reached = maximum
   tutor_cnt = []
   for tutor in t.tutors:
      c = t.count_slots_of_tutor(tutor)
      tutor_cnt.append(c)
   for i in range(0, len(tutor_cnt)):
      for j in range(0, len(tutor_cnt)):
         if i != j:
            reached -= abs(tutor_cnt[i]-tutor_cnt[j])
   log.debug('[ %2.1f ] equal number of slots for each tutor: %d / %d' % (weight, reached, maximum))
   score += weight * reached/maximum
   log.debug('score: %.2f' %(score))

   # equal overall time at test for each tutor
   weight = 4.0
   maximum = len(t.get_slots()) * (len(t.tutors))
   reached = maximum
   tutor_cnt = []
   for tutor in t.tutors:
      c = t.get_test_length_for_tutor(tutor)
      tutor_cnt.append(c)
   for i in range(0, len(tutor_cnt)):
      for j in range(0, len(tutor_cnt)):
         if i != j:
            reached -= abs(tutor_cnt[i]-tutor_cnt[j])
   log.debug('[ %2.1f ] equal overall time: %d / %d' % (weight, reached, maximum))
   score += weight * reached/maximum
   log.debug('score: %.2f' %(score))

   # non-overlapping slots
   weight = 10.0
   maximum = len(t.get_slots()) * (len(t.rooms)-1)
   reached = maximum
   for tutor in t.tutors:
      reached -= t.count_overlaps_of_tutor(tutor)
   log.debug('[ %2.1f ] non-overlapping slots: %d / %d' % (weight, reached, maximum))
   score += weight * reached/maximum
   log.debug('score: %.2f' %(score))

   # no tutor changes (tutors should have consecutive slots in the same room)
   weight = 0.8
   maximum = len(t.get_slots()) - len(t.rooms)*2
   reached = maximum - t.count_tutor_changes()
   log.debug('[ %2.1f ] no tutor changes: %d / %d' % (weight, reached, maximum))
   score += weight * reached/maximum
   log.debug('score: %.2f' %(score))

   # no holes for tutor (tutor prefers only few "holes" in his/hers schedule)
   weight = 0.5
   maximum = len(t.get_slots())
   reached = maximum - t.count_tutor_holes()
   log.debug('[ %2.1f ] no holes for tutor: %d / %d' % (weight, reached, maximum))
   score += weight * reached/maximum
   log.debug('score: %.2f' %(score))

   # pause in the middle of the test (should have higher weight than overall
   # test time)
   weight = 0.0
   maximum = len(t.get_slots())
   reached = maximum
   for tutor in t.tutors:
      reached -= t.pause_offset_to_testcenter_of_tutor(tutor)
   log.debug('[ %2.1f ] pause: %d / %d' % (weight, reached, maximum))
   score += weight * reached/maximum
   log.debug('score: %.2f' %(score))
   
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
# t.apply_genome(genome)

# print result
best = ga.bestIndividual()
t.apply_genome(best)
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
