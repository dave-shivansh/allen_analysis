# -*- coding: utf-8 -*-
"""
GUI for laser control

@author: samg
"""

import sip
sip.setapi('QString', 2)
import time
import numpy as np
from PyQt4 import QtGui,QtCore
import serial
import nidaq


def start():
    app = QtGui.QApplication.instance()
    if app is None:
        app = QtGui.QApplication([])
    w = LaserControlGUI(app)
    app.exec_()


class LaserControlGUI():
    
    def __init__(self,app):
        self.app = app
        
        winWidth = 600
        winHeight = 300
        self.mainWin = QtGui.QMainWindow()
        self.mainWin.setWindowTitle('LaserControl')
        self.mainWin.closeEvent = self.mainWinCloseEvent
        self.mainWin.resize(winWidth,winHeight)
        screenCenter = QtGui.QDesktopWidget().availableGeometry().center()
        mainWinRect = self.mainWin.frameGeometry()
        mainWinRect.moveCenter(screenCenter)
        self.mainWin.move(mainWinRect.topLeft())
        
        self.nidaqDigitalOut = nidaq.DigitalOutputs(device='Dev1',port=1,initialState='high')
        self.nidaqDigitalOut.StartTask()
        self.nidaqDigitalOut.Write(self.nidaqDigitalOut.lastOut)
        
        self.blueLaser = LaserControlObj(app,'Blue Laser','COM4')
        
        self.orangeLaser = LaserControlObj(app,'Orange Laser','COM5',shutterControlMode='digital',nidaqDigitalOut=self.nidaqDigitalOut,ch=1)
        
        setLayoutGridSpacing(self.blueLaser.layout,winHeight/2,winWidth,5,3)
        setLayoutGridSpacing(self.orangeLaser.layout,winHeight/2,winWidth,5,3)
        
        self.mainWidget = QtGui.QWidget()
        self.mainWin.setCentralWidget(self.mainWidget)
        self.mainLayout = QtGui.QGridLayout()
        self.mainWidget.setLayout(self.mainLayout)
        setLayoutGridSpacing(self.mainLayout,winHeight,winWidth,9,1)
        self.mainLayout.addLayout(self.blueLaser.layout,0,0,4,1)
        self.mainLayout.addLayout(self.orangeLaser.layout,5,0,4,1)
        self.mainWin.show()
        
    def mainWinCloseEvent(self,event):
        self.blueLaser.serialPort.close()
        self.blueLaser.nidaqAnalogOut.StopTask()
        self.blueLaser.nidaqAnalogOut.ClearTask()
        self.orangeLaser.serialPort.close()
        self.orangeLaser.nidaqDigitalOut.StopTask()
        self.orangeLaser.nidaqDigitalOut.ClearTask()
        event.accept()
    

class LaserControlObj():
    
    def __init__(self,app,label,port,shutterControlMode='analog',nidaqDigitalOut=None,ch=0):
        self.app = app        
        
        self.label = QtGui.QLabel(label)
        self.label.setAlignment(QtCore.Qt.AlignHCenter)
        
        self.serialPort = serial.Serial()
        self.serialPort.port = port
        self.serialPort.baudrate = 115200
        self.serialPort.bytesize = serial.EIGHTBITS
        self.serialPort.stopbits = serial.STOPBITS_ONE
        self.serialPort.parity = serial.PARITY_NONE
        self.serialPort.open()
        
        self.shutterControlMode = shutterControlMode
        self.powerControl = QtGui.QDoubleSpinBox()
        self.powerControl.setPrefix('Power:  ')
        if shutterControlMode=='digital':
            self.nidaqDigitalOut = nidaqDigitalOut
            self.nidaqDigitalOutCh = ch
            self.powerControl.setSuffix(' mW')
            self.powerControl.setDecimals(1)
            self.powerControl.setRange(0,100)
            self.powerControl.setSingleStep(0.5)
            self.powerControl.setValue(100)
        else:
            self.serialPort.write('em\r sdmes 0\r sames 1\r') # analog modulation mode
            self.nidaqAnalogOut = nidaq.AnalogOutput(device='Dev1',channel=ch,voltageRange=(0,5))
            self.nidaqAnalogOut.StartTask()
            self.nidaqAnalogOut.Write(np.array([0.0]))
            self.powerControl.setSuffix(' V')
            self.powerControl.setDecimals(2)
            self.powerControl.setRange(0,5)
            self.powerControl.setSingleStep(0.05)
            self.powerControl.setValue(1)
        self.powerControl.valueChanged.connect(self.powerControlChanged)
        
        self.modeMenu = QtGui.QComboBox()
        self.modeMenu.addItems(('Continuous','Pulse'))
        self.modeMenu.currentIndexChanged.connect(self.modeMenuChanged)
        
        self.pulseNumControl = QtGui.QSpinBox()
        self.pulseNumControl.setPrefix('# Pulses:  ')
        self.pulseNumControl.setRange(1,1000)
        self.pulseNumControl.setSingleStep(1)
        self.pulseNumControl.setValue(1)
        self.pulseNumControl.setEnabled(False)
        
        self.pulseDurControl = QtGui.QDoubleSpinBox()
        self.pulseDurControl.setPrefix('Pulse Duration:  ')
        self.pulseDurControl.setSuffix(' s')
        self.pulseDurControl.setDecimals(3)
        self.pulseDurControl.setRange(0.001,60)
        self.pulseDurControl.setSingleStep(0.1)
        self.pulseDurControl.setValue(1)
        self.pulseDurControl.valueChanged.connect(self.pulseDurChanged)
        self.pulseDurControl.setEnabled(False)
        
        self.pulseIntervalControl = QtGui.QDoubleSpinBox()
        self.pulseIntervalControl.setPrefix('Pulse Interval:  ')
        self.pulseIntervalControl.setSuffix(' s')
        self.pulseDurControl.setDecimals(3)
        self.pulseIntervalControl.setRange(0.001,60)
        self.pulseIntervalControl.setSingleStep(0.1)
        self.pulseIntervalControl.setValue(1)
        self.pulseIntervalControl.setEnabled(False)
        
        if shutterControlMode=='analog':
            self.zeroOffsetControl = QtGui.QDoubleSpinBox()
            self.zeroOffsetControl.setPrefix('Zero Offset:  ')
            self.zeroOffsetControl.setSuffix(' V')
            self.zeroOffsetControl.setDecimals(2)
            self.zeroOffsetControl.setRange(0,1)
            self.zeroOffsetControl.setSingleStep(0.05)
            self.zeroOffsetControl.setValue(0)
            
            self.rampDurControl = QtGui.QDoubleSpinBox()
            self.rampDurControl.setPrefix('Ramp:  ')
            self.rampDurControl.setSuffix(' s')
            self.rampDurControl.setDecimals(3)
            self.rampDurControl.setRange(0,1)
            self.rampDurControl.setSingleStep(0.05)
            self.rampDurControl.setValue(0)
        
        self.onOffButton = QtGui.QPushButton('Start',checkable=True)
        self.onOffButton.clicked.connect(self.onOffButtonPress)
        
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.label,0,1,1,1)
        self.layout.addWidget(self.powerControl,1,0,1,1)
        if shutterControlMode=='analog':
            self.layout.addWidget(self.zeroOffsetControl,2,0,1,1)
            self.layout.addWidget(self.rampDurControl,3,0,1,1)
        self.layout.addWidget(self.modeMenu,1,1,1,1)
        self.layout.addWidget(self.pulseNumControl,2,1,1,1)
        self.layout.addWidget(self.pulseDurControl,3,1,1,1)
        self.layout.addWidget(self.pulseIntervalControl,4,1,1,1)
        self.layout.addWidget(self.onOffButton,1,2,1,1)
        
    def powerControlChanged(self,val):
        if self.shutterControlMode=='digital':
            self.serialPort.write('p '+str(val/1e3)+'\r')
        else:
            if val<self.zeroOffsetControl.value():
                self.zeroOffsetControl.setValue(val)
            self.zeroOffsetControl.setMaximum(val)
    
    def modeMenuChanged(self,ind):
        if ind==0:
            self.pulseNumControl.setEnabled(False)
            self.pulseIntervalControl.setEnabled(False)
            self.pulseDurControl.setEnabled(False)
        else:
            self.pulseNumControl.setEnabled(True)
            self.pulseIntervalControl.setEnabled(True)
            self.pulseDurControl.setEnabled(True)
            
    def pulseDurChanged(self,val):
        if self.shutterControlMode=='analog':
            if val<self.rampDurControl.value():
                self.rampDurControl.setValue(val)
            self.rampDurControl.setMaximum(val)
    
    def onOffButtonPress(self,val):
        if self.onOffButton.isChecked():
            self.onOffButton.setText('Stop')
            if self.shutterControlMode=='analog':
                power = self.powerControl.value()
                rampDur = self.rampDurControl.value()
                if rampDur>0:
                    ramp = np.linspace(self.zeroOffsetControl.value(),power,round(rampDur*self.nidaqAnalogOut.sampRate))
            if self.modeMenu.currentIndex()==0:
                if self.shutterControlMode=='digital':
                    self.nidaqDigitalOut.WriteBit(self.nidaqDigitalOutCh,0)
                else:
                    if rampDur>0:
                        self.nidaqAnalogOut.Write(ramp)
                    else:
                        self.nidaqAnalogOut.Write(np.array([power]))
            else:
                pulseDur = self.pulseDurControl.value()
                pulseInt = self.pulseIntervalControl.value()
                for i in range(self.pulseNumControl.value()):
                    if i>0:
                        time.sleep(pulseInt)
                    self.app.processEvents()
                    if not self.onOffButton.isChecked():
                        return
                    if self.shutterControlMode=='digital':
                        self.nidaqDigitalOut.WriteBit(self.nidaqDigitalOutCh,0)
                        time.sleep(pulseDur)
                        self.nidaqDigitalOut.WriteBit(self.nidaqDigitalOutCh,1)
                    else:
                        if rampDur>0:
                            t = time.clock()
                            self.nidaqAnalogOut.Write(ramp)
                            while time.clock()-t<pulseDur:
                                time.sleep(1/self.nidaqAnalogOut.sampRate)
                        else:
                            self.nidaqAnalogOut.Write(np.array([power]))
                            time.sleep(pulseDur)
                        self.nidaqAnalogOut.Write(np.array([0.0]))
                self.onOffButton.click()
        else:
            self.onOffButton.setText('Start')
            if self.shutterControlMode=='digital':
                self.nidaqDigitalOut.WriteBit(self.nidaqDigitalOutCh,1)
            else:
                self.nidaqAnalogOut.Write(np.array([0.0]))
                
# pulseSamples = round(self.nidaqAnalogOut.sampRate*self.pulseDurControl.value())
# intervalSamples = round(self.nidaqAnalogOut.sampRate*self.pulseIntervalControl.value())
# pulseTrain = np.zeros((self.pulseNumControl.value(),pulseSamples+intervalSamples))
# pulseTrain[:,:pulseSamples] = self.powerControl.value()
# self.nidaqAnalogOut.Write(pulseTrain.ravel()[:-intervalSamples+1])
    

def setLayoutGridSpacing(layout,height,width,rows,cols):
    for row in range(rows):
        layout.setRowMinimumHeight(row,height/rows)
        layout.setRowStretch(row,1)
    for col in range(cols):
        layout.setColumnMinimumWidth(col,width/cols)
        layout.setColumnStretch(col,1)
        

if __name__=="__main__":
    start()