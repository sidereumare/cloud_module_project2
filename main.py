from multiprocessing.managers import BaseManager
import time, sys, os
import requests
import multiprocessing as mp
from abc import *
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from MainProgram import *


# 인터페이스 클래스
class UserInterface(metaclass=ABCMeta):
    @abstractclassmethod
    def update(self):
        pass
    @abstractclassmethod
    def getCookie(self):
        pass
    @abstractclassmethod
    def getTableName(self):
        pass

# cmd UI 클래스
class CmdMain(UserInterface):
    def __init__(self, uiInQueue:mp.Queue, uiOutQueue:mp.Queue):
        self.uiInQueue = uiInQueue
        self.uiOutQueue = uiOutQueue

    # cmd 메인 루프
    def update(self):
        while True:
            if self.uiInQueue.empty() == False:
                data = self.uiInQueue.get()
                if type(data) is list:
                    # cmd 화면 갱신
                    os.system('cls')
                    print(f'[*] Table Name : {data[0]}')
                    print(f'[*] Column Names : {data[1]}')
                    print(f'[*] Data : {len(data[2])}개')
                    for d in data[2]:
                        print(d)
                    print('\n\n\n\n\n\n')
                    print(f'[*] Status : {data[3]}')
                # 입력 처리
                elif data=='cookie':
                    self.uiOutQueue.put(self.getCookie())
                elif data=='tableName':
                    self.uiOutQueue.put(self.getTableName())
                elif data=='exit':
                    break
                else:
                    print('error')
                    break
            # time.sleep(0.1)

    def getCookie(self):
        return input('쿠키값을 입력해 주세요: ')
    
    def getTableName(self):
        return input('테이블 이름을 입력해 주세요: ')

# gui consumer thread
class GUIStartFunc(QThread):
    tableUpdateSignal = pyqtSignal(list)
    getCookieSignal = pyqtSignal()
    getTableNameSignal = pyqtSignal()

    def __init__(self, uiInQueue:mp.Queue, uiOutQueue:mp.Queue):
        super().__init__()
        self.uiInQueue = uiInQueue
        self.uiOutQueue = uiOutQueue

    # gui consumer 메인 루프
    def update(self):
        while True:
            if self.uiInQueue.empty() == False:
                data = self.uiInQueue.get()
                if type(data) is list:
                    self.tableUpdateSignal.emit(data)
                elif data=='cookie':
                    self.getCookieSignal.emit()
                elif data=='tableName':
                    self.getTableNameSignal.emit()
                elif data=='exit':
                    break
                else:
                    print('error')
                    break
            # time.sleep(0.1)
    
    def run(self) -> None:
        self.update()

class PyQtMainWindow(QMainWindow):
    __metaclass__ = UserInterface
    def __init__(self, uiInQueue, uiOutQueue) -> None:
        super().__init__()
        self.uiInQueue = uiInQueue
        self.uiOutQueue = uiOutQueue
        self.mainProgram = None
        self.guiThread = None
    
    # UI 초기화
    def setupUi(self):
        self.setObjectName("MainWindow")
        self.resize(835, 535)
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.lineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit.setText("ANSWER")
        self.lineEdit.setObjectName("lineEdit")
        self.horizontalLayout.addWidget(self.lineEdit)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_2.addWidget(self.label_2)
        self.lineEdit_2 = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit_2.setObjectName("lineEdit_2")
        self.horizontalLayout_2.addWidget(self.lineEdit_2)
        self.pushButton = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton.setObjectName("pushButton")
        self.pushButton.clicked.connect(self.startBtnClick)
        self.horizontalLayout_2.addWidget(self.pushButton)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.dataTable = QtWidgets.QTableWidget(self.centralwidget)
        self.dataTable.setObjectName("dataTable")
        self.dataTable.setColumnCount(0)
        self.dataTable.setRowCount(0)
        self.verticalLayout.addWidget(self.dataTable)
        self.gridLayout.addLayout(self.verticalLayout, 1, 0, 1, 1)
        self.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(self)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 835, 21))
        self.menubar.setObjectName("menubar")
        self.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(self)
        self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)

        self.retranslateUi()
        QtCore.QMetaObject.connectSlotsByName(self)
    # UI 초기화_1
    def retranslateUi(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.label.setText(_translate("MainWindow", "TableName"))
        self.label_2.setText(_translate("MainWindow", "Cookie"))
        self.pushButton.setText(_translate("MainWindow", "시작"))
    
    # 버튼 클릭시 실행되는 함수
    # 버튼 클릭시 mainProgram과 guiThread를 생성하고 실행시킴.
    def startBtnClick(self):
        if self.mainProgram != None:
            self.mainProgram.terminate()
            self.guiThread.terminate()
        self.guiThread = GUIStartFunc(uiInQueue, uiOutQueue)
        self.mainProgram = MainProgram(4, manager, dataManager, uiInQueue, uiOutQueue)
        # ui 시그널 연결
        self.guiThread.tableUpdateSignal.connect(self.update)
        self.guiThread.getCookieSignal.connect(self.getCookie)
        self.guiThread.getTableNameSignal.connect(self.getTableName)
        # 쓰레드 프로세스 실행
        self.guiThread.start()
        self.mainProgram.start()

    # 테이블 업데이트
    @pyqtSlot(list)
    def update(self, data):
        self.dataTable.setColumnCount(len(data[1]))
        self.dataTable.setRowCount(len(data[2]))
        self.dataTable.setHorizontalHeaderLabels(data[1])
        for i, row in enumerate(data[2]):
            for j, col in enumerate(row):
                self.dataTable.setItem(i, j, QtWidgets.QTableWidgetItem(col))
        self.statusbar.showMessage(data[3])
        self.dataTable.resizeColumnsToContents()
        self.dataTable.resizeRowsToContents()

    # 쿠키 입력
    @pyqtSlot()
    def getCookie(self):
        self.uiOutQueue.put(self.lineEdit_2.text())
    
    # 테이블 이름 입력
    @pyqtSlot()
    def getTableName(self):
        self.uiOutQueue.put(self.lineEdit.text())


# A1B94AD8982342583A3B5101F1B7B5AD
# ANSWER
import argparse
if __name__ == '__main__':
    # 인자값 받기
    parser = argparse.ArgumentParser()
    parser.add_argument('--type', type=str, required=True, help='cmd or gui')
    args = parser.parse_args()
    
    # 프로세스간 통신을 위한 큐 생성
    dataManager = getManager()
    manager = mp.Manager()
    uiInQueue = manager.Queue()
    uiOutQueue = manager.Queue()

    # cmd 모드
    if args.type == 'cmd':
        cmd = CmdMain(uiInQueue, uiOutQueue)
        mainProgram = MainProgram(4, manager, dataManager, uiInQueue, uiOutQueue)
        mainProgram.start()
        cmd.update()
        mainProgram.join()
    # gui 모드
    elif args.type == 'gui':
        app = QtWidgets.QApplication(sys.argv)
        mainWindow = PyQtMainWindow(uiInQueue, uiOutQueue)
        mainWindow.show()
        mainWindow.setupUi()
        sys.exit(app.exec_())
    