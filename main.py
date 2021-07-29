from bs4 import BeautifulSoup
import requests
import telegram
import time
import json

# 텔레그램 메시지 전송
def sendAlarm(token, chatID, message):
    bot = telegram.Bot(token=token)
    bot.sendMessage(chat_id=chatID, text=message)

#댓글 수집
def crwalReply(isMGallery, galleryID, articleNo):
    if isMGallery:
        articleURL = f'https://gall.dcinside.com/mgallery/board/view/?id={galleryID}&no={articleNo}&_rk=&page=1'
    else:
        articleURL = f'https://gall.dcinside.com/board/view/?id={galleryID}&no={articleNo}&_rk=&page=1'

    lightHeader = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'}

    heavyHeaders = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    }

    #요청 거부시 1초 sleep, 10회 이상일 경우 1분 sleep
    exceptCount = 0
    while True:
        try:
            articleResponse = requests.get(articleURL, headers=lightHeader)
        except:
            if exceptCount >= 10:
                time.sleep(60)
            time.sleep(1)
            exceptCount += 1
        else:
            exceptCount = 0
            break

    articleSoup =  BeautifulSoup(articleResponse.text, 'html.parser')

    #댓글 api 토큰
    e_s_n_o = articleSoup.find("input", {"id": "e_s_n_o"})['value']

    #댓글 api form data
    replyData = {
        'id': galleryID,
        'no': articleNo,
        'cmt_id': galleryID,
        'cmt_no': articleNo,
        'e_s_n_o': e_s_n_o,
        'comment_page': 1
    }

    while True:
        try:
            replyResponse = requests.post('https://gall.dcinside.com/board/comment/', replyData, headers=heavyHeaders)
        except:
            if exceptCount >= 10:
                time.sleep(60)
            time.sleep(1)
        else:
            break

    rawReply = json.loads(replyResponse.text)

    allReplies = []

    for reply in rawReply['comments']:

        memoSoup =  BeautifulSoup(reply['memo'], 'html.parser')
        memo = memoSoup.text

        if 'https://dcimg5.dcinside.com/dccon.php' in reply['memo']:
            reply['memo'] = '디시콘'
        if reply['ip'] == '':
            allReplies.append([reply['name'], reply['no'], memo, reply['depth'], reply['reg_date']])
        else:
            allReplies.append([f"{reply['name']}({reply['ip']})", reply['no'], memo, reply['depth'], reply['reg_date']])

    return allReplies

def makeRepleTree(reply):
    previousReple = None

    for reple in reply:
        if reple[3] == 0:
            previousReple = reple[0]
        else:
            reple.append(previousReple)

    return reply

#텔레그램 토큰, 채팅 ID, 갤러리 ID, 게시물 번호, 최소 댓글 개수, 댓글 재전송 시간
def main(token, chatID, gallID, articleNo, replyNumbers, interval): 
    sendList = {}
    
    while True:
        try:
            
            replies = crwalReply(True, gallID, articleNo)

            if len(replies) == replyNumbers:
                pass
            else:
                replies = makeRepleTree(replies)
                for reple in replies: 
                    #답글일 경우            댓글 id가 존재할 경우      interval초가 지났을 경우                           댓글 id가 리스트에 없는 경우
                    if reple[3] == 1 and ((reple[1] in sendList and (time.time() - sendList[reple[1]]) > interval) or (not reple[1] in sendList)):
                        print(f'호출: [닉네임: {reple[0]} | 내용: {reple[2]} | 시간: {reple[4]}] 대상 매니저: {reple[5]}')
                        sendAlarm(token, chatID, f'호출 발생\n닉네임(IP): {reple[0]}\n내용: {reple[2]}\n시간: {reple[4]}\n대상 매니저: {reple[5]}\nhttps://m.dcinside.com/board/{gallID}')
                        sendList[reple[1]] = time.time()

            previousSendList = list(sendList)
            for i in previousSendList: #시간 업데이트가 없는 요소 삭제
                if time.time() - sendList[i] > 700:
                    del sendList[i]

            time.sleep(3) #3초마다 재전송

        except: #예외 무시
            pass
