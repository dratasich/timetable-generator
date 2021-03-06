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
import numpy as np
import skfuzzy
import skfuzzy.control

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
    maximum = len(timetable.get_slots()) * (len(timetable.tutors))
    reached = maximum - measures.count_overlaps(timetable)
    log.debug('[ %2.1f ] non-overlapping slots: %d / %d' % (weight, reached, maximum))
    score += weight * reached/maximum
    log.debug('score: %.2f' %(score))

    # no tutor changes (tutors should have consecutive slots in the same room)
    weight = 0.8
    maximum = len(timetable.get_slots()) - len(timetable.rooms)*2
    reached = maximum - measures.count_room_changes(timetable)
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


#
# fuzzy logic
#

##
# Fuzzy control system.
# 
# For some reason the input and output variables including membership functions
# are not part of the control system (static/global variables?!). Only rules
# are part of the control system, variables are hided. So lets save everything
# needed into this table.
##
fs = {}

##
# Initialization function for fuzzy evaluation.
##
def fuzzy_init(timetable):
    global fs

    # universe variables (inputs and outputs)
    slotdiff_range = [0, (len(timetable.tutors)-1)*len(timetable.get_slots())] # min: equal number of slots; max: a tutor can have all slots
    slotdiff = skfuzzy.control.Antecedent(np.arange(slotdiff_range[0], slotdiff_range[1], 1), 'slotdiff')

    testdiff_range = [0, (len(timetable.tutors)-1)*len(timetable.get_slots())]
    testdiff = skfuzzy.control.Antecedent(np.arange(testdiff_range[0], testdiff_range[1], 1), 'testdiff')

    overlaps_range = [0, measures.count_possible_overlaps(timetable)]
    overlaps = skfuzzy.control.Antecedent(np.arange(overlaps_range[0], overlaps_range[1], 1), 'overlaps')

    rchanges_range = [0, len(timetable.get_slots()) - len(timetable.rooms)] # max: each slot has another tutor (start slots per room are excluded)
    rchanges = skfuzzy.control.Antecedent(np.arange(rchanges_range[0], rchanges_range[1], 1), 'rchanges')

    # TODO:
    # no holes

    score_range = [0, 100]
    score = skfuzzy.control.Consequent(np.arange(score_range[0], score_range[1], 1), 'score')

    # membership functions (mappings)
    overlaps['unacceptable'] = skfuzzy.trimf(overlaps.universe, [overlaps_range[0]+1, overlaps_range[1], overlaps_range[1]])
    overlaps['ok'] = skfuzzy.trimf(overlaps.universe, [overlaps_range[0], overlaps_range[0], overlaps_range[0]+1])

    slotdiff['poor'] = skfuzzy.trimf(slotdiff.universe, [slotdiff_range[1]*0.15, slotdiff_range[1], slotdiff_range[1]])
    slotdiff['average'] = skfuzzy.trimf(slotdiff.universe, [slotdiff_range[1]*0.03, slotdiff_range[1]*0.1, slotdiff_range[1]*0.17])
    slotdiff['good'] = skfuzzy.trimf(slotdiff.universe, [slotdiff_range[0], slotdiff_range[0], slotdiff_range[1]*0.05])

    testdiff['poor'] = skfuzzy.trimf(testdiff.universe, [testdiff_range[1]*0.3, testdiff_range[1], testdiff_range[1]])
    testdiff['average'] = skfuzzy.trimf(testdiff.universe, [testdiff_range[1]*0.05, testdiff_range[1]*0.2, testdiff_range[1]*0.35])
    testdiff['good'] = skfuzzy.trimf(testdiff.universe, [testdiff_range[0], testdiff_range[0], testdiff_range[1]*0.1])

    rchanges['poor'] = skfuzzy.trimf(rchanges.universe, [rchanges_range[1]*0.2, rchanges_range[1], rchanges_range[1]])
    rchanges['average'] = skfuzzy.trimf(rchanges.universe, [rchanges_range[1]*0.05, rchanges_range[1]*0.15, rchanges_range[1]*0.25])
    rchanges['good'] = skfuzzy.trimf(rchanges.universe, [rchanges_range[0], rchanges_range[0], rchanges_range[1]*0.1])

    score['unacceptable'] = skfuzzy.trapmf(score.universe, [score_range[0], score_range[0], score_range[0], score_range[1]*0.25])
    score['poor'] = skfuzzy.trimf(score.universe, [score_range[1]*0.25, score_range[1]*0.5, score_range[1]*0.5])
    score['average'] = skfuzzy.trimf(score.universe, [score_range[1]*0.5, score_range[1]*0.75, score_range[1]*0.75])
    score['good'] = skfuzzy.trimf(score.universe, [score_range[1]*0.75, score_range[1]*0.9, score_range[1]*0.9])
    score['superior'] = skfuzzy.trimf(score.universe, [score_range[1]*0.9, score_range[1], score_range[1]])

    # overlaps.view()
    # slotdiff.view()
    # testdiff.view()
    # rchanges.view()
    score.view()

    # fuzzy rules
    rules = []
    rules.append( skfuzzy.control.Rule(overlaps['unacceptable']
                                       & (slotdiff['poor'] | slotdiff['average'] | slotdiff['good'])
                                       & (testdiff['poor'] | testdiff['average'] | testdiff['good'])
                                       & (rchanges['poor'] | rchanges['average'] | rchanges['good']),
                                       score['unacceptable'],
                                       "Any overlaps are unacceptable.") )

    rules.append( skfuzzy.control.Rule(overlaps['ok']
                                       & slotdiff['good']
                                       & testdiff['good']
                                       & rchanges['good'],
                                       score['superior'],
                                       "All is fine.") )

    rules.append( skfuzzy.control.Rule(overlaps['ok']
                                       & (slotdiff['poor'] | rchanges['poor']),
                                       score['poor'],
                                       "Slot difference and room changes should not be bad.") )

    rules.append( skfuzzy.control.Rule(overlaps['ok']
                                       & (slotdiff['average'] | rchanges['average'])
                                       & testdiff['poor'],
                                       score['poor']) )

    rules.append( skfuzzy.control.Rule(overlaps['ok']
                                       & (slotdiff['average'] | rchanges['average'])
                                       & testdiff['average'],
                                       score['average']) )

    rules.append( skfuzzy.control.Rule(overlaps['ok']
                                       & slotdiff['good']
                                       & (rchanges['average'] | rchanges['good']),
                                       score['good']) )

    rules.append( skfuzzy.control.Rule(overlaps['ok']
                                       & slotdiff['good']
                                       & (rchanges['average'] | rchanges['good']),
                                       score['good']) )

    rules.append( skfuzzy.control.Rule(overlaps['ok']
                                       & slotdiff['good']
                                       & rchanges['good']
                                       & (testdiff['poor'] | testdiff['average']),
                                       score['good']) )

    rules.append( skfuzzy.control.Rule(overlaps['ok']
                                       & slotdiff['good']
                                       & rchanges['good']
                                       & (testdiff['average'] | testdiff['good']),
                                       score['superior']) )

    
    # create fuzzy control system
    fs['scoring_ctrl'] = skfuzzy.control.ControlSystem(rules)

    # for debugging
    fs['score'] = score

##
# Fuzzy evaluation function.
##
def fuzzy(timetable, loglevel=logging.INFO):
    # init logger for this function
    log = logging.getLogger("evaluation.fuzzy")
    log.setLevel(loglevel)

    # check if global variables are initialized
    assert fs['scoring_ctrl'] is not None, "Fuzzy control system not initialized."

    # compute score
    scoring = skfuzzy.control.ControlSystemSimulation(fs['scoring_ctrl'])

    scoring.input['overlaps'] = measures.count_overlaps(timetable)
    scoring.input['slotdiff'] = measures.sum_up_slot_differences(timetable)
    scoring.input['testdiff'] = measures.sum_up_testlength_differences(timetable)
    scoring.input['rchanges'] = measures.count_room_changes(timetable)

    scoring.compute()

    if loglevel == logging.DEBUG:
        fs['score'].view(sim=scoring)

    log.debug(measures.print_measures(timetable))
    log.debug('score: %.2f' %(scoring.output['score']))
    return scoring.output['score']
