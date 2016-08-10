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
# Returns the sum of difference between the number of slots of all tutors.
#
# Worst case: When 1 tutor has all slots (the others have none), the difference
# is (number of tutors - 1) * (number of slots). Best case: All tutors have the
# same amount of slots, then the difference is 0.
##
def sum_up_slot_differences(timetable):
    sumslots = 0
    tutor_slot_cnt = []
    # count slots of each tutor
    for tutor in timetable.tutors:
        c = count_slots_of_tutor(timetable, tutor)
        tutor_slot_cnt.append(c)
    # compare number of slots and sum up
    for i in range(0, len(tutor_slot_cnt)):
        for j in range(i, len(tutor_slot_cnt)):
            sumslots += abs(tutor_slot_cnt[i]-tutor_slot_cnt[j])
    return sumslots

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
# Returns overall test length in number of slots.
##
def get_test_length(timetable):
    testlen = 0
    for r in range(0, len(timetable.rooms)-1):
        testlen = max(testlen, len(timetable._slot_matrix[r]))
    return testlen

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
# Returns the sum of difference between the test length (i.e., duration from
# first slot to last slot) of all tutors.
#
# Worst case: When 1 tutor has all slots (the others have none), the difference
# is (number of tutors - 1) * (number of slots). Best case: All tutors have the
# same amount of slots, then the difference is 0.
##
def sum_up_testlength_differences(timetable):
    sumtestlen = 0
    tutor_testlen = []
    # test length of each tutor
    for tutor in timetable.tutors:
        c = get_test_length_for_tutor(timetable, tutor)
        tutor_testlen.append(c)
    # compare test length and sum up
    for i in range(0, len(tutor_testlen)):
        for j in range(i, len(tutor_testlen)):
            sumtestlen += abs(tutor_testlen[i]-tutor_testlen[j])
    return sumtestlen

##
# Count how many times the tutor changes in a room.
##
def count_room_changes(timetable):
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

def print_measures(timetable):
    ret = ''

    # tutor specific output
    ret += '\n tutor     | #slots | testlen | #overlaps'
    ret += '\n-----------+--------+---------+-----------\n'
    for tutor in timetable.tutors:
        ret += '%10.10s | %6d | %7d | %9d\n' % (tutor, 
                                                count_slots_of_tutor(timetable, tutor),
                                                get_test_length_for_tutor(timetable, tutor),
                                                count_overlaps_of_tutor(timetable, tutor))
    # sum up
    ret += '-----------+--------+---------+-----------\n'
    ret += '           | %6d | %7d | %9d\n' % (len(timetable.get_slots()), 
                                               get_test_length(timetable),
                                               count_overlaps(timetable))

    # count tutors in a row
    ret += '\n'
    ret += 'slot difference: %d / %d\n' % (sum_up_slot_differences(timetable),
                                           (len(timetable.tutors)-1)*len(timetable.get_slots()) )
    ret += 'test length difference: %d / %d\n' % (sum_up_testlength_differences(timetable),
                                                  (len(timetable.tutors)-1)*len(timetable.get_slots()))
    ret += 'number of room changes: %d / %d\n' % (count_room_changes(timetable),
                                                  len(timetable.get_slots())-len(timetable.rooms))

    return ret
