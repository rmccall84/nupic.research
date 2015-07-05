#!/usr/bin/env python
# ----------------------------------------------------------------------
# Numenta Platform for Intelligent Computing (NuPIC)
# Copyright (C) 2014-2015, Numenta, Inc.  Unless you have an agreement
# with Numenta, Inc., for a separate license for this software code, the
# following terms and conditions apply:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses.
#
# http://numenta.org/licenses/
# ----------------------------------------------------------------------
"""
This program tests the memorization capacity of L4+L3.

The independent variables (that we change) are:
    - # of distinct worlds (images)
    - # of unique elements (fixation points)

The dependent variables (that we monitor) are:
    - temporal pooler stability
    - temporal pooler distinctness

Each world will be composed of unique elements that are not shared between
worlds, to test the raw memorization capacity without generalization.

The output of this program is a data sheet (CSV) showing the relationship
between these variables.

Experiment setup and validation are specified here:
https://github.com/numenta/nupic.research/wiki/Capacity-experiment:-setup-and-validation
"""

import csv
import os
import sys
import time
import yaml
from optparse import OptionParser

import numpy
from pylab import rcParams

from nupic.research.monitor_mixin.monitor_mixin_base import MonitorMixinBase
from sensorimotor.exhaustive_one_d_agent import ExhaustiveOneDAgent
from sensorimotor.one_d_world import OneDWorld
from sensorimotor.one_d_universe import OneDUniverse
from sensorimotor.random_one_d_agent import RandomOneDAgent
from sensorimotor.sensorimotor_experiment_runner import (
  SensorimotorExperimentRunner
)

SHOW_PROGRESS_INTERVAL = 200
TWOPASS_TM_TRAINING_REPS = 2
TWOPASS_TP_TRAINING_REPS = 1
ONLINE_TRAINING_REPS = 3
NUM_TEST_SEQUENCES = 4
RANDOM_SEED = 42
PLOT_RESET_SHADING = 0.2
PLOT_HEIGHT = 15
PLOT_WIDTH = 21



def setupExperiment(n, w, numElements, numWorlds, tmParams, tpParams):
  print "Setting up experiment..."
  universe = OneDUniverse(nSensor=n, wSensor=w,
                          nMotor=n, wMotor=w)
  runner = SensorimotorExperimentRunner(tmOverrides=tmParams,
                                        tpOverrides=tpParams,
                                        seed=RANDOM_SEED)
  exhaustiveAgents = []
  randomAgents = []
  for world in xrange(numWorlds):
    elements = range(world * numElements, world * numElements + numElements)
    # agent = ExhaustiveOneDAgent(OneDWorld(universe, elements), 0)
    # exhaustiveAgents.append(agent)

    possibleMotorValues = range(-numElements, numElements + 1)
    possibleMotorValues.remove(0)
    agent = RandomOneDAgent(OneDWorld(universe, elements), numElements / 2,
                            possibleMotorValues=possibleMotorValues,
                            seed=RANDOM_SEED)
    randomAgents.append(agent)
  print "Done setting up experiment."
  print
  return runner, exhaustiveAgents, randomAgents



def trainTwoPass(runner, exhaustiveAgents, completeSequenceLength, verbosity):
  print "Training temporal memory..."
  sequences = runner.generateSequences(completeSequenceLength *
                                       TWOPASS_TM_TRAINING_REPS,
                                       exhaustiveAgents,
                                       verbosity=verbosity)
  runner.feedLayers(sequences, tmLearn=True, tpLearn=False,
                    verbosity=verbosity,
                    showProgressInterval=SHOW_PROGRESS_INTERVAL)
  print
  print MonitorMixinBase.mmPrettyPrintMetrics(runner.tp.mmGetDefaultMetrics() +
                                              runner.tm.mmGetDefaultMetrics())
  print
  print "Training temporal pooler..."

  runner.tm.mmClearHistory()
  runner.tp.mmClearHistory()
  sequences = runner.generateSequences(completeSequenceLength *
                                       TWOPASS_TP_TRAINING_REPS,
                                       exhaustiveAgents,
                                       verbosity=verbosity)
  runner.feedLayers(sequences, tmLearn=False, tpLearn=True,
                    verbosity=verbosity,
                    showProgressInterval=SHOW_PROGRESS_INTERVAL)
  print
  print MonitorMixinBase.mmPrettyPrintMetrics(runner.tp.mmGetDefaultMetrics() +
                                              runner.tm.mmGetDefaultMetrics())
  print



def trainOnline(runner, exhaustiveAgents, completeSequenceLength, reps,
                verbosity):
  print "Training temporal memory and temporal pooler..."
  sequences = runner.generateSequences(completeSequenceLength *
                                       reps,
                                       exhaustiveAgents,
                                       verbosity=verbosity)
  runner.feedLayers(sequences, tmLearn=True, tpLearn=True,
                    verbosity=verbosity,
                    showProgressInterval=SHOW_PROGRESS_INTERVAL)
  print
  print MonitorMixinBase.mmPrettyPrintMetrics(runner.tp.mmGetDefaultMetrics() +
                                              runner.tm.mmGetDefaultMetrics())
  print



def runTestPhase(runner, randomAgents, numWorlds, numElements,
                 completeSequenceLength, verbosity):
  print "Testing (worlds: {0}, elements: {1})...".format(numWorlds, numElements)
  runner.tm.mmClearHistory()
  runner.tp.mmClearHistory()
  sequences = runner.generateSequences(completeSequenceLength /
                                       NUM_TEST_SEQUENCES,
                                       randomAgents, verbosity=verbosity,
                                       numSequences=NUM_TEST_SEQUENCES)
  runner.feedLayers(sequences, tmLearn=False, tpLearn=False,
                    verbosity=verbosity,
                    showProgressInterval=SHOW_PROGRESS_INTERVAL)
  print "Done testing.\n"
  if verbosity >= 2:
    print "Overlap:"
    print
    print runner.tp.mmPrettyPrintDataOverlap()
    print
  print MonitorMixinBase.mmPrettyPrintMetrics(
    runner.tp.mmGetDefaultMetrics() + runner.tm.mmGetDefaultMetrics())
  print



def plotExperimentState(runner, plotVerbosity, numWorlds, numElems, isOnline,
                        experimentPhase):
  if plotVerbosity >= 1:
    rcParams['figure.figsize'] = PLOT_WIDTH, PLOT_HEIGHT
    rcParams.update({'font.size': 14})
    title = "worlds: {0}, elements: {1}, online: {2}, phase: {3}".format(
            numWorlds, numElems, isOnline, experimentPhase)
    # runner.tp.mmGetPlotConnectionsPerColumn(title=title)
    if plotVerbosity >= 2:
      # runner.tm.mmGetCellActivityPlot(title=title, activityType="activeCells",
      #                                 showReset=True,
      #                                 resetShading=PLOT_RESET_SHADING)
      # runner.tm.mmGetCellActivityPlot(title=title,
      #                                 activityType="predictedActiveCells",
      #                                 showReset=True,
      #                                 resetShading=PLOT_RESET_SHADING)
      runner.tp.mmGetCellActivityPlot(title=title, showReset=True,
                                      resetShading=PLOT_RESET_SHADING)
      writeToCsv(runner)



def writeToCsv(runner):
  showReset = True
  resetShading = PLOT_RESET_SHADING
  directoryPath = "output/"
  outputFileName = "2x6-online-TP-output_50xseqLength.csv"


  # Create csv output writer
  # os.chdir(directoryPath)
  # with open(outputFileName, "wb") as outputFile:
  #   csvWriter = csv.writer(outputFile)

  resetTrace = runner.tp.mmGetTraceResets().data
  activeCellTrace = runner.tp._mmTraces["activeCells"].data
  numColumns = runner.tp._numColumns
  data = numpy.zeros((numColumns, 1))
  for i in xrange(len(activeCellTrace)):
    if showReset and resetTrace[i]:
      activity = numpy.ones((numColumns, 1)) * resetShading
    else:
      activity = numpy.zeros((numColumns, 1))

    activeSet = activeCellTrace[i]
    activity[list(activeSet)] = 1
    data = numpy.concatenate((data, activity), 1)
    # csvWriter.writerow(activity)

    numpy.savetxt(directoryPath+outputFileName, data, delimiter=",")



def writeOutput(outputDir, runner, numElems, numWorlds, elapsedTime):
  if not os.path.exists(outputDir):
    os.makedirs(outputDir)
  fileName = "{0:0>3}x{1:0>3}.csv".format(numWorlds, numElems)
  filePath = os.path.join(outputDir, fileName)
  with open(filePath, "wb") as outputFile:
    csvWriter = csv.writer(outputFile)
    header = ["# worlds", "# elements", "duration"]
    row = [numWorlds, numElems, elapsedTime]
    for metric in (runner.tp.mmGetDefaultMetrics() +
                   runner.tm.mmGetDefaultMetrics()):
      header += ["{0} ({1})".format(metric.prettyPrintTitle(), x) for x in
                ["min", "max", "sum", "mean", "stddev"]]
      row += [metric.min, metric.max, metric.sum, metric.mean,
              metric.standardDeviation]
    csvWriter.writerow(header)
    csvWriter.writerow(row)
    outputFile.flush()



def run(numWorlds, numElems, paramsPath, outputDir, plotVerbosity,
        consoleVerbosity, params=None):
  if params is None:
    with open(paramsPath) as paramsFile:
      params = yaml.safe_load(paramsFile)

  # Setup params
  n = params["n"]
  w = params["w"]
  tmParams = params["tmParams"]
  tpParams = params["tpParams"]
  isOnline = params["isOnline"]
  onlineTrainingReps = params["onlineTrainingReps"] if isOnline else "N/A"
  completeSequenceLength = numElems ** 2
  print ("Experiment parameters: "
         "(# worlds = {0}, # elements = {1}, n = {2}, w = {3}, "
         "online = {4}, onlineReps = {5})".format(
         numWorlds, numElems, n, w, isOnline, onlineTrainingReps))
  print "Temporal memory parameters: {0}".format(tmParams)
  print "Temporal pooler parameters: {0}".format(tpParams)
  print

  # Setup experiment
  start = time.time()
  runner, exhaustiveAgents, randomAgents = setupExperiment(n, w, numElems,
                                                           numWorlds, tmParams,
                                                           tpParams)

  # Training phase
  # print "Training: (worlds: {0}, elements: {1})...".format(numWorlds, numElems)
  # print
  # if isOnline:
  #   trainOnline(runner, exhaustiveAgents, completeSequenceLength,
  #               onlineTrainingReps, consoleVerbosity)
  # else:
  #   trainTwoPass(runner, exhaustiveAgents, completeSequenceLength, consoleVerbosity)
  # print "Done training."
  # print

  # Custom Cosyne training
  print "Training temporal memory and temporal pooler..."
  numSequences = 3
  sequenceLength = 50 * (completeSequenceLength / numSequences)
  sequences = runner.generateSequences(sequenceLength,
                                       randomAgents,
                                       verbosity=consoleVerbosity,
                                       numSequences=numSequences)
  runner.feedLayers(sequences, tmLearn=True, tpLearn=True,
                    verbosity=consoleVerbosity,
                    showProgressInterval=SHOW_PROGRESS_INTERVAL)
  plotExperimentState(runner, plotVerbosity, numWorlds, numElems, isOnline, "Training")

  # Test TM and TP on randomly moving agents
  # runTestPhase(runner, randomAgents, numWorlds, numElems,
  #              completeSequenceLength, consoleVerbosity)
  # plotExperimentState(runner, plotVerbosity, numWorlds, numElems, isOnline, "Testing")
  elapsed = int(time.time() - start)
  print "Total time: {0:2} seconds.".format(elapsed)

  # Write results to output file
  writeOutput(outputDir, runner, numElems, numWorlds, elapsed)
  if plotVerbosity >= 1:
    raw_input("Press any key to exit...")



parser = OptionParser(usage="%prog NUM_WORLDS NUM_ELEMENTS PARAMS_DIR "
                            "OUTPUT_DIR [options]"
                            "\n\nRun sensorimotor experiment with specified "
                            "worlds and elements using params in PARAMS_DIR "
                            "and outputting results to OUTPUT_DIR.")
parser.add_option("-p",
                  "--plot",
                  type=int,
                  default=0,
                  dest="plotVerbosity",
                  help="Plotting verbosity: 0 => none, 1 => summary plots, "
                       "2 => detailed plots")
parser.add_option("-c",
                  "--console",
                  type=int,
                  default=0,
                  dest="consoleVerbosity",
                  help="Console message verbosity: 0 => none")



if __name__ == "__main__":
  (options, args) = parser.parse_args(sys.argv[1:])
  if len(args) < 4:
    parser.print_help(sys.stderr)
    sys.exit()

  plot = options.plotVerbosity
  console = options.consoleVerbosity
  run(int(args[0]), int(args[1]), args[2], args[3], plot, console)
