#!/usr/bin/python
##
# @file measures.py
# @date 05.08.2016
# @author Denise Ratasich
#
# @brief Provides measures of a timetable.
#

##
# Returns number of slots for a specific tutor.
##
def count_slots_of_tutor(timetable, tutor):
    slots = filter(lambda s: s.tutor == tutor, timetable._slots)
    return len(slots)

##
# Returns slots with same start time.
##
def get_concurrent_slots(timetable, start_time):
    rows = len(timetable._slot_matrix)
    cols = len(timetable._slot_matrix[0])
    slots = []
    # search for column of slots with start_time
    for c in range(cols):
        if timetable._slot_matrix[0][c] == None:
            continue
        if timetable._slot_matrix[0][c].start == start_time:
            # found right column, save column to slot array
            for r in range(rows):
                if timetable._slot_matrix[r][c] != None:
                    slots.append(timetable._slot_matrix[r][c])
            break
    return slots

##
# Returns number of overlapping slots of a tutor.
##
def count_overlaps_of_tutor(timetable, tutor):
    cnt = 0
    # go through slots of tutor
    slots = filter(lambda s: s.tutor == tutor, timetable._slots)
    for slot in slots:
        # check concurrent slots
        cc_slots = get_concurrent_slots(timetable, slot.start) # current slot including
        cc_slots = filter(lambda s: s.tutor == tutor, cc_slots)
        if len(cc_slots) > 1:
            cnt += 1
    return cnt

##
# Returns the number of possible overlaps.
##
def count_possible_overlaps(timetable):
    return len(timetable.get_slots()) * (len(timetable.rooms)-1)

##
# Returns total number of overlaps (overlap = tutor has two slots at the same
# time).
##
def count_overlaps(timetable):
    cnt = 0
    for tutor in timetable.tutors:
        cnt += count_overlaps_of_tutor(timetable, tutor)
    return cnt

##
# Returns the difference between last and first slot of a tutor (in number
# of slots), i.e., overall time in slots the tutor supervises the test.
##
def get_test_length_for_tutor(timetable, tutor):
    slots = filter(lambda s: s.tutor == tutor, timetable._slots)
    slots = sorted(slots, key=lambda s: s.start.hour*60+s.start.minute)
    # tutors has slots?
    if len(slots) == 0:
        return 0
    # get min/max start time
    min_slot = slots[0]
    max_slot = slots[len(slots)-1]
    return (max_slot.start - min_slot.start).seconds/60 / timetable.slotlen + 1

##
# Count how many times the tutor changes in a room.
##
def count_tutor_changes(timetable):
    rows = len(timetable._slot_matrix)
    cols = len(timetable._slot_matrix[0])
    changes = 0
    for r in range(rows):
        for c in range(cols-1):
            if timetable._slot_matrix[r][c] == None or timetable._slot_matrix[r][c+1] == None:
                continue
            if timetable._slot_matrix[r][c].tutor != timetable._slot_matrix[r][c+1].tutor:
                changes += 1
    return changes

##
# Count number of pauses in slots of a tutor.
##
def count_tutor_holes(timetable):
    holes = 0
    for t in timetable.tutors:
        slots = filter(lambda s: s.tutor == t, timetable._slots)
        slots = sorted(slots, key=lambda s: s.start.hour*60+s.start.minute)
        for i in range(len(slots)-1):
            # ignore overlapping slots
            if slots[i].start == slots[i+1].start:
                continue
            # count holes (calculate from time difference)
            holes += (slots[i+1].start - slots[i].start).seconds/60/timetable.slotlen - 1
    return holes
                
##
# Returns pause offset to center of overall test time of a tutor.
##
def pause_slots_of_tutor(timetable, tutor):
    slots = filter(lambda s: s.tutor == tutor, timetable._slots)
    starts = map(lambda s: s.start, slots)
    starts.sort()
    # TODO
    return []

##
# Returns pause offset to center of overall test time of a tutor.
##
def pause_offset_to_testcenter_of_tutor(timetable, tutor):
    # TODO
    return 0
