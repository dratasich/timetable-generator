#!/usr/bin/python
##
# @file evaluation.py
# @date 05.08.2016
# @author Denise Ratasich
#
# @brief Evaluates the performance of a timetable.
#
# Uses the measures of a timetable to evaluate the performance of a timetable.
#

import logging
import measures

##
# Piecewise linear evaluation function.
##
def piecewise_linear(timetable, loglevel=logging.INFO):
    # init logger for this function
    log = logging.getLogger("evaluation.piecewise_linear")
    log.setLevel(loglevel)

    # init score
    score = 0.0
    log.debug('score: %.2f' %(score))

    # equal number of slots for each tutor
    weight = 5.0
    maximum = len(timetable.get_slots()) * (len(timetable.tutors))
    reached = maximum
    tutor_cnt = []
    for tutor in timetable.tutors:
        c = measures.count_slots_of_tutor(timetable, tutor)
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
    maximum = len(timetable.get_slots()) * (len(timetable.tutors))
    reached = maximum
    tutor_cnt = []
    for tutor in timetable.tutors:
        c = measures.get_test_length_for_tutor(timetable, tutor)
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
    maximum = len(timetable.get_slots()) * (len(timetable.rooms)-1)
    reached = maximum
    for tutor in timetable.tutors:
        reached -= measures.count_overlaps_of_tutor(timetable, tutor)
    log.debug('[ %2.1f ] non-overlapping slots: %d / %d' % (weight, reached, maximum))
    score += weight * reached/maximum
    log.debug('score: %.2f' %(score))

    # no tutor changes (tutors should have consecutive slots in the same room)
    weight = 0.8
    maximum = len(timetable.get_slots()) - len(timetable.rooms)*2
    reached = maximum - measures.count_tutor_changes(timetable)
    log.debug('[ %2.1f ] no tutor changes: %d / %d' % (weight, reached, maximum))
    score += weight * reached/maximum
    log.debug('score: %.2f' %(score))

    # no holes for tutor (tutor prefers only few "holes" in his/hers schedule)
    weight = 0.5
    maximum = len(timetable.get_slots())
    reached = maximum - measures.count_tutor_holes(timetable)
    log.debug('[ %2.1f ] no holes for tutor: %d / %d' % (weight, reached, maximum))
    score += weight * reached/maximum
    log.debug('score: %.2f' %(score))

    # pause in the middle of the test (should have higher weight than overall
    # test time)
    weight = 0.0
    maximum = len(timetable.get_slots())
    reached = maximum
    for tutor in timetable.tutors:
        reached -= measures.pause_offset_to_testcenter_of_tutor(timetable, tutor)
    log.debug('[ %2.1f ] pause: %d / %d' % (weight, reached, maximum))
    score += weight * reached/maximum
    log.debug('score: %.2f' %(score))

    return score


##
# Fuzzy evaluation function.
##
def fuzzy(timetable, loglevel=logging.INFO):

    # fuzzy set = [unacceptable, fair, good, superior]
    # membership function

    # non-overlapping slots
    # equal number of slots for each tutor
    # equal overall time at test for each tutor
    # no tutor changes (tutors should have consecutive slots in the same room)

    # rules
    # IF overlaps = unacceptable THEN evaluation = unacceptable

    return 0.0
