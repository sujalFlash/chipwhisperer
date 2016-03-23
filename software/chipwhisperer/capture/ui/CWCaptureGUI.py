#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2013-2014, NewAE Technology Inc
# All rights reserved.
#
# Find this and more at newae.com - this file is part of the chipwhisperer
# project, http://www.assembla.com/spaces/chipwhisperer
#
#    This file is part of chipwhisperer.
#
#    chipwhisperer is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    chipwhisperer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with chipwhisperer.  If not, see <http://www.gnu.org/licenses/>.
#=================================================

import os.path
import sys
from PySide.QtGui import *
from pyqtgraph.parametertree import Parameter, ParameterTree
from chipwhisperer.common.api.CWCoreAPI import CWCoreAPI
from chipwhisperer.capture.ui.CaptureProgressDialog import CaptureProgressDialog
from chipwhisperer.capture.ui.EncryptionStatusMonitor import EncryptionStatusMonitor
from chipwhisperer.capture.utils.GlitchExplorerDialog import GlitchExplorerDialog as GlitchExplorerDialog
from chipwhisperer.capture.utils.SerialTerminalDialog import SerialTerminalDialog as SerialTerminalDialog
from chipwhisperer.common.api.ExtendedParameter import ExtendedParameter
from chipwhisperer.common.ui.CWMainGUI import CWMainGUI
from chipwhisperer.common.ui.ValidationDialog import ValidationDialog
from chipwhisperer.common.api.config_parameter import ConfigParameter


class CWCaptureGUI(CWMainGUI):
    def __init__(self, rootdir):
        super(CWCaptureGUI, self).__init__(CWCoreAPI(rootdir), name=("ChipWhisperer" + u"\u2122" + " Capture " + CWCoreAPI.__version__), icon="cwiconC")

        self.esm = EncryptionStatusMonitor(self)
        self.serialTerminal = SerialTerminalDialog(self, self.cwAPI)
        self.glitchMonitor = GlitchExplorerDialog(self)
        self.cwAPI.paramTrees.append(self.glitchMonitor.paramTree)
        self.setupParameters()
        self.newProject()

        self.addToolbar()
        self.addToolMenu()
        self.addSettingsDocks()
        self.addTraceDock("Capture Waveform (Channel 1)")
        self.reloadParamList()
        self.restoreSettings()

        # Observers (callback methods)
        self.cwAPI.signals.paramListUpdated.connect(self.reloadTargetParamList)
        self.cwAPI.signals.newInputData.connect(self.newTargetData)
        self.cwAPI.signals.connectStatus.connect(self.targetStatusChanged)
        self.cwAPI.signals.newTextResponse.connect(self.esm.newData)
        self.cwAPI.signals.traceDone.connect(self.glitchMonitor.traceDone)
        self.cwAPI.signals.campaignStart.connect(self.glitchMonitor.campaignStart)
        self.cwAPI.signals.campaignDone.connect(self.glitchMonitor.campaignDone)
        self.cwAPI.signals.connectStatus.connect(self.targetStatusChanged)
        self.cwAPI.signals.scopeChanged.connect(self.scopeChanged)
        self.cwAPI.signals.targetChanged.connect(self.targetChanged)
        self.cwAPI.signals.traceChanged.connect(self.traceChanged)
        self.cwAPI.signals.auxChanged.connect(self.auxChanged)
        self.cwAPI.signals.acqPatternChanged.connect(self.reloadParamList)

    def setupParameters(self):
        valid_scopes = CWCoreAPI.getScopeModules(self.cwAPI.getRootDir() + "/scopes")
        valid_targets =  CWCoreAPI.getTargetModules(self.cwAPI.getRootDir() + "/targets")
        valid_traces = CWCoreAPI.getTraceFormats(self.cwAPI.getRootDir() + "/../common/traces")
        valid_aux = CWCoreAPI.getAuxiliaryModules(self.cwAPI.getRootDir() + "/auxiliary")
        valid_acqPatterns = CWCoreAPI.getAcqPatternModules()
        
        if len(valid_scopes) == 0:
            raise IOError("Failed to load scope modules, either modules missing, import error, " +
                          "or running main file from unusual directory without passing location " +
                          "of install.")

        self.cwAPI.setScope(valid_scopes["None"])
        self.cwAPI.setTarget(valid_targets["None"])
        self.cwAPI.setTraceClass(valid_traces["None"])
        self.cwAPI.setAux(valid_aux["None"])
        self.cwAPI.setAcqPattern(valid_acqPatterns['Basic'])

        self.cwParams = [
                {'name':'Scope Module', 'type':'list', 'values':valid_scopes, 'value':self.cwAPI.getScope(), 'set':self.cwAPI.setScope},
                {'name':'Target Module', 'type':'list', 'values':valid_targets, 'value':self.cwAPI.getTarget(), 'set':self.cwAPI.setTarget},
                {'name':'Trace Format', 'type':'list', 'values':valid_traces, 'value':self.cwAPI.getTraceClass(), 'set':self.cwAPI.setTraceClass},
                {'name':'Auxiliary Module', 'type':'list', 'values':valid_aux, 'value':self.cwAPI.auxList[0], 'set':self.cwAPI.setAux},

                # {'name':'Key Settings', 'type':'group', 'children':[
                #        {'name':'Encryption Key', 'type':'str', 'value':self.textkey, 'set':self.setKey},
                #        {'name':'Send Key to Target', 'type':'bool', 'value':True},
                #        {'name':'New Encryption Key/Trace', 'key':'newKeyAlways', 'type':'bool', 'value':False},
                #    ]},

                {'name':'Acquisition Settings', 'type':'group', 'children':[
                        {'name':'Number of Traces', 'type':'int', 'limits':(1, 1E9), 'value':100, 'set':self.cwAPI.setNumTraces, 'get':self.cwAPI.getNumTraces},
                        {'name':'Capture Segments', 'type':'int', 'limits':(1, 1E6), 'value':1, 'set':self.cwAPI.setNumSegments, 'get':self.cwAPI.getNumSegments, 'tip':'Break capture into N segments, '
                         'which may cause data to be saved more frequently. The default capture driver requires that NTraces/NSegments is small enough to avoid running out of system memory '
                         'as each segment is buffered into RAM before being written to disk.'},
                        # {'name':'Open Monitor', 'type':'action', 'action':self.esm.show},
                        {'name':'Key/Text Pattern', 'type':'list', 'values':valid_acqPatterns, 'value':self.cwAPI.acqPattern, 'set':self.cwAPI.setAcqPattern},
                    ]},
                ]

    def scopeChanged(self):
        if self.cwAPI.hasScope():
            self.cwAPI.getScope().paramListUpdated.connect(self.reloadScopeParamList)
            self.cwAPI.getScope().dataUpdated.connect(self.newScopeData)
            self.cwAPI.getScope().connectStatus.connect(self.scopeStatusChanged)
            self.reloadScopeParamList()

    def targetChanged(self):
        if self.cwAPI.hasTarget():
            self.cwAPI.getTarget().connectStatus.connect(self.targetStatusChanged)
            self.reloadTargetParamList()

    def traceChanged(self):
        self.reloadTraceParamList()

    def auxChanged(self):
        self.reloadAuxParamList()

    def masterStatusChanged(self):
        # Deals with multiple
        if self.scopeStatus.defaultAction() == self.scopeStatusActionCon or self.targetStatus.defaultAction() == self.targetStatusActionCon:
            self.captureStatus.setDefaultAction(self.captureStatusActionCon)
        else:
            self.captureStatus.setDefaultAction(self.captureStatusActionDis)

    def scopeStatusChanged(self):
        """Callback when scope connection successful"""
        if self.cwAPI.getScope().getStatus():
            self.scopeStatus.setDefaultAction(self.scopeStatusActionCon)
        else:
            self.scopeStatus.setDefaultAction(self.scopeStatusActionDis)

        self.masterStatusChanged()

    def targetStatusChanged(self):
        """Callback when target connection successful"""
        if self.cwAPI.getTarget().getStatus():
            self.targetStatus.setDefaultAction(self.targetStatusActionCon)
        else:
            self.targetStatus.setDefaultAction(self.targetStatusActionDis)

        self.masterStatusChanged()

    def newTargetData(self, data):
        self.glitchMonitor.addResponse(data)

    def addToolMenu(self):
        self.TerminalAct = QAction('Open Terminal', self,
                                   statusTip='Open Simple Serial Terminal',
                                   triggered=self.serialTerminal.show)

        self.toolMenu.addAction(self.TerminalAct)
        self.GlitchMonitorAct = QAction('Open Glitch Monitor', self,
                                     statusTip='Open Glitch Monitor Table',
                                     triggered=self.glitchMonitor.show)
        self.toolMenu.addAction(self.GlitchMonitorAct)

        # Keep track of add-ins
        self._scopeToolMenuItems = []

    def addSettingsDocks(self):
        self.setupParametersTree()
        self.settingsGeneralDock = self.addSettings(self.generalParamTree, "General Settings")
        self.settingsScopeDock = self.addSettings(self.scopeParamTree, "Scope Settings")
        self.settingsTargetDock = self.addSettings(self.targetParamTree, "Target Settings")
        self.settingsTraceDock = self.addSettings(self.traceParamTree, "Trace Settings")
        self.settingsAuxDock = self.addSettings(self.auxParamTree, "Aux Settings")
        self.tabifyDocks([self.settingsGeneralDock, self.settingsScopeDock, self.settingsTargetDock,
                          self.settingsTraceDock, self.settingsAuxDock])

    def setupParametersTree(self):
        self.generalParamTree = ParameterTree()
        self.scopeParamTree = ParameterTree()
        self.targetParamTree = ParameterTree()
        self.traceParamTree = ParameterTree()
        self.auxParamTree = ParameterTree()

        self.params = ConfigParameter.create_extended(self, name='Generic Settings', type='group', children=self.cwParams)
        self.generalParamTree.setParameters(self.params, showTop=False)

    def reloadScopeParamList(self):
        # Remove all old scope actions that don't apply for new selection
        for act in self._scopeToolMenuItems:
            self.toolMenu.removeAction(act)

        self._scopeToolMenuItems = []

        if self.cwAPI.hasScope():
            ExtendedParameter.reloadParams(self.cwAPI.getScope().paramList(), self.scopeParamTree, help_window=self.helpbrowser.helpwnd)

            # Check for any tools to add too
            if hasattr(self.cwAPI.getScope(), "guiActions"):
                self._scopeToolMenuItems.append(self.toolMenu.addSeparator())
                for act in self.cwAPI.getScope().guiActions(self):
                    self._scopeToolMenuItems.append(QAction(act[0], self, statusTip=act[1], triggered=act[2]))

        for act in self._scopeToolMenuItems:
            self.toolMenu.addAction(act)

    def reloadTargetParamList(self):
        ExtendedParameter.reloadParams(self.cwAPI.getTarget().paramList(), self.targetParamTree, help_window=self.helpbrowser.helpwnd)

    def reloadTraceParamList(self):
        ExtendedParameter.reloadParams(self.cwAPI.getTraceClass().getParams.paramList(), self.traceParamTree, help_window=self.helpbrowser.helpwnd)

    def reloadAuxParamList(self):
        ExtendedParameter.reloadParams(self.cwAPI.getAuxiliaryModules()[0].paramList(), self.auxParamTree, help_window=self.helpbrowser.helpwnd)

    def reloadParamList(self):
        ExtendedParameter.reloadParams(self.paramList(), self.generalParamTree, help_window=self.helpbrowser.helpwnd)

    def paramList(self):
        p = []
        p.append(self.params)

        if self.cwAPI.acqPattern is not None:
            for par in self.cwAPI.acqPattern.paramList():
                p.append(par)
        return p

    def newScopeData(self, data=None, offset=0):
        self.waveformDock.widget().passTrace(data, offset)

    def setConfigWidget(self, widget):
        self.configdock.setWidget(widget)

    def addToolbar(self):
        # Capture
        self.capture1Act = QAction(QIcon(':/images/play1.png'), 'Capture 1', self)
        self.capture1Act.triggered.connect(lambda: self.doCapture(self.capture1))
        self.captureMAct = QAction(QIcon(':/images/playM.png'), 'Capture Multi', self)
        self.captureMAct.triggered.connect(lambda: self.doCapture(self.captureM))

        self.captureStatus = QToolButton()
        self.captureStatusActionDis = QAction(QIcon(':/images/status_disconnected.png'), 'Master: Disconnected', self)
        self.captureStatusActionDis.triggered.connect(self.doConDis)
        self.captureStatusActionCon = QAction(QIcon(':/images/status_connected.png'), 'Master: Connected', self)
        self.captureStatusActionCon.triggered.connect(self.doConDis)
        self.captureStatus.setDefaultAction(self.captureStatusActionDis)

        # Scope
        self.scopeStatus = QToolButton()
        self.scopeStatusActionDis = QAction(QIcon(':/images/status_disconnected.png'), 'Scope: Disconnected', self)
        self.scopeStatusActionDis.triggered.connect(self.doConDisScope)
        self.scopeStatusActionCon = QAction(QIcon(':/images/status_connected.png'), 'Scope: Connected', self)
        self.scopeStatusActionCon.triggered.connect(self.doConDisScope)
        self.scopeStatus.setDefaultAction(self.scopeStatusActionDis)

        # Target
        self.targetStatus = QToolButton()
        self.targetStatusActionDis = QAction(QIcon(':/images/status_disconnected.png'), 'Target: Disconnected', self)
        self.targetStatusActionDis.triggered.connect(self.doConDisTarget)
        self.targetStatusActionCon = QAction(QIcon(':/images/status_connected.png'), 'Target: Connected', self)
        self.targetStatusActionCon.triggered.connect(self.doConDisTarget)
        self.targetStatus.setDefaultAction(self.targetStatusActionDis)

        # Other Stuff
        self.miscValidateAction = QAction(QIcon(':/images/validate.png'), 'Validate', self)
        self.miscValidateAction.triggered.connect(self.validateSettings)

        self.toolBar = self.addToolBar('Tools')
        self.toolBar.setObjectName('Tools')
        self.toolBar.addAction(self.capture1Act)
        self.toolBar.addAction(self.captureMAct)
        self.toolBar.addSeparator()
        self.toolBar.addWidget(QLabel('Master:'))
        self.toolBar.addWidget(self.captureStatus)
        self.toolBar.addWidget(QLabel('Scope:'))
        self.toolBar.addWidget(self.scopeStatus)
        self.toolBar.addWidget(QLabel('Target:'))
        self.toolBar.addWidget(self.targetStatus)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.miscValidateAction)
        self.toolBar.show()

    def doConDisScope(self):
        if self.scopeStatus.defaultAction() == self.scopeStatusActionDis:
            self.cwAPI.connectScope()
            self.updateStatusBar("Scope Connected")
        else:
            self.cwAPI.disconnectScope()
            self.updateStatusBar("Scope Disconnected")

    def doConDisTarget(self):
        if self.targetStatus.defaultAction() == self.targetStatusActionDis:
            self.cwAPI.connectTarget()
            self.updateStatusBar("Target Connected")
        else:
            self.cwAPI.disconnectTarget()
            self.updateStatusBar("Target Disconnected")

    def doConDis(self):
        """Toggle connect button pushed (master): attempts both target & scope connection"""
        if self.captureStatus.defaultAction() == self.captureStatusActionDis:
            self.cwAPI.connect()
            self.updateStatusBar("Target and Scope Connected")
        else:
            self.cwAPI.disconnect()
            self.updateStatusBar("Target and Scope Disconnected")

    def validateSettings(self, warnOnly=False):
        # Validate settings from all modules before starting multi-capture
        vw = ValidationDialog(onlyOkButton=not warnOnly)

        ret = []
        try:
            ret.extend(self.cwAPI.getTarget().validateSettings())
        except AttributeError:
            ret.append(("info", "Target Module", "Target has no validateSettings()", "Internal Error", "73b08424-3865-4274-8fd7-dd213ede2c46"))
        except Exception as e:
            ret.append(("warn", "General Settings", e.message, "Specify Target Module", "2351e3b0-e5fe-11e3-ac10-0800200c9a66"))

        try:
            ret.extend(self.cwAPI.getScope().validateSettings())
        except AttributeError:
            ret.append(("info", "Scope Module", "Scope has no validateSettings()", "Internal Error", "d19be31d-ad1a-4533-80dc-9423dfa92753"))
        except Exception as e:
            ret.append(("warn", "General Settings", e.message, "Specify Scope Module", "325de1cf-0d47-4ed8-8e9f-77d8f9cf2d5f"))

        try:
            ret.extend(self.cwAPI.getTraceClass()().validateSettings())
        except AttributeError:
            ret.append(("info", "Writer Module", "Writer has no validateSettings()", "Internal Error", "d7b3a9a1-83f0-4b4d-92b9-3d7dcf6304ae"))
        except Exception as e:
            ret.append(("warn", "General Settings", e.message, "Specify Trace Writer Module", "57a3924d-3794-4ca6-9693-46a7b5243727"))

        tracesPerRun = int(self.cwAPI.numTraces / self.cwAPI.numSegments)
        if tracesPerRun > 10E3:
            ret.append(("warn", "General Settings", "Very Long Capture (%d traces)" % tracesPerRun, "Set 'Capture Segments' to '%d'" % (self.numTraces / 10E3), "1432bf95-9026-4d8c-b15d-9e49147840eb"))

        for i in ret:
            vw.addMessage(*i)

        if self.cwAPI.project().isUntitled():
             vw.addMessage("info", "File Menu", "Project not saved, using default-data-dir", "Save project file before capture", "8c9101ff-7553-4686-875d-b6a8a3b1d2ce")

        if vw.numWarnings() > 0 or warnOnly == False:
            return vw.exec_()
        else:
            return True

    def doCapture(self, callback):
        try:
            self.capture1Act.setEnabled(False)
            self.captureMAct.setEnabled(False)
            self.updateStatusBar(callback())
        finally:
            self.capture1Act.setEnabled(True)
            self.captureMAct.setEnabled(True)
            self.capture1Act.setChecked(False)
            self.captureMAct.setChecked(False)

    def capture1(self):
        self.cwAPI.capture1()
        return "Capture-One Completed"

    def captureM(self):
        cprog = CaptureProgressDialog(ntraces=self.cwAPI.getNumTraces(), nsegs=self.cwAPI.getNumSegments())
        cprog.startCapture()
        self.cwAPI.signals.traceDone.connect(cprog.traceDoneSlot)
        self.cwAPI.signals.campaignDone.connect(cprog.incSeg)
        cprog.abortCapture.connect(self.cwAPI.signals.abortCapture.emit)
        self.cwAPI.captureM()
        self.cwAPI.signals.campaignDone.disconnect(cprog.incSeg)
        self.cwAPI.signals.traceDone.disconnect(cprog.traceDoneSlot)
        return "Capture-M Completed"


def makeApplication():
    # Create the Qt Application
    app = QApplication(sys.argv)
    app.setOrganizationName(CWCoreAPI.__organization__)
    app.setApplicationName(CWCoreAPI.__name__ + " - Capture ")
    return app

def main(cwdir):
    app = makeApplication()

    #print os.getcwd()   
    #TODO - should we prompt user for cwdir if not found?

    # Create and show the form
    window = CWCaptureGUI(cwdir)
    window.show()

    # Run the main Qt loop
    sys.exit(app.exec_())

if __name__ == '__main__':
    main(cwdir = "../")