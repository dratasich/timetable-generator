#!/usr/bin/python
##
# @file timetable.py
# @date 05.08.2016
# @author Denise Ratasich
#
# @brief Timetable and Slot classes.
#
# 
#

import logging
import datetime
import measures

####################
# global variables #
####################

# length in minutes of Slots and Tests
SLOTLEN_TEST1 = 20
TESTLEN_TEST1 = 100 # must be a multiple of slotlen
SLOTLEN_TEST2 = 30
TESTLEN_TEST2 = 120

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
# Stores slots of a schedule.
##
class Timetable:
    ##
    # Constructor
    #
    # The timetable is generated based on the number of rooms and groups of
    # students. Further it depends on the test number. The generation of an
    # initial schedule is very specific to the OSUE course.
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
            # shift start time to lab rooms, because seminar room is missing,
            # i.e., won't be part of the schedule
            start = start + datetime.timedelta(minutes = SLOTLEN_TEST1)
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
            ret += '  %3s  ' % (self.rooms[r])
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
            ret += '  %3s  ' % (self.rooms[r])
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
                                                    measures.count_slots_of_tutor(self, tutor),
                                                    measures.get_test_length_for_tutor(self, tutor),
                                                    measures.count_overlaps_of_tutor(self, tutor))

        # count tutors in a row
        ret += '\nNumber of tutor-changes: %d\n' % (measures.count_tutor_changes(self))

        return ret
