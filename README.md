# ai-trading-bot

## 참고자료
- 조코딩 강의자료 : https://jocoding.net/gptbitcoin-paid
- pyubpit 깃허브 : https://github.com/sharebook-kr/pyupbit
- 조코딩 레포지토리 : https://github.com/youtube-jocoding/gpt-bitcoin/tree/main

## pyupbit API 주요 목록
- 종목 조회
    ```python
    print(pyupbit.get_tickers(fiat="KRW"))
    ['KRW-BTC', 'KRW-DASH', 'KRW-ETH', 'KRW-NEO', 'KRW-MTL', 'KRW-LTC', ...]
    ```
    
- 최근 체결 가격
    ```python
    print(pyupbit.get_current_price("KRW-BTC"))
    ```
    
- 종목별 시세 조회 (분봉, 일봉, 주봉, 월봉) - 날짜, 시가/고가/저가/종가/거래량/거래대금
    ```python
    # day/minute1/minute3/minute5/minute10/minute15/minute30/minute60/minute240/week/month
    print(pyupbit.get_ohlcv("KRW-BTC", interval="day")              # 일봉 데이터 (5일)
    print(pyupbit.get_ohlcv("KRW-BTC", interval="minute1"))         # 분봉 데이터
    print(pyupbit.get_ohlcv("KRW-BTC", interval="week"))            # 주봉 데이터
    ```
    
- 종목별 잔액 조회
    ```python
    print(upbit.get_balance("KRW-XRP"))     # KRW-XRP 조회
    print(upbit.get_balance("KRW"))         # 보유 현금 조회
    ```
    
- 매수/매도 주문
    ```python
    # 지정가 매도/매수
    print(upbit.sell_limit_order("KRW-XRP", 600, 20)) # 600원, 20개 매도
    print(upbit.buy_limit_order("KRW-XRP", 613, 10))
    # 시장가 매도/매수
    print(upbit.buy_market_order("KRW-XRP", 10000)) # 수수료(0.05%) 제외 10000원 매도
    print(upbit.sell_market_order("KRW-XRP", 30))
    # 미체결 주문 조회
    upbit.get_order("KRW-LTC")
    ```

## AWS EC2 운영 참고
```
# 현재 경로 상세 출력
ls -al

# 특정 폴더 전체 삭제
rm -rf 폴더명

# 레포지토리 가져오기
git clone 여러분의깃허브레포지토리주소

#pip3 가상 환경 만들기
python3 -m venv bitcoinenv

#가상 환경 활성화
source bitcoinenv/bin/activate

# 경로 이동

cd 폴더명

#서버에서 라이브러리 설치
pip3 install -r requirements.txt

#.env 파일 만들고 API KEY 넣기
vim .env

#autotrade.py 열어서 수정하기
vim autotrade.py

#vim 에디터 입력 모드 전환: i
#vim 에디터 입력 모드 나가기: ESC
#vim 에디터 저장 안하고 나가기: ESC + :q!
#vim 에디터 저장 및 종료: ESC + :wq!

# 그냥 실행하기
python3 autotrade.py

#백그라운드 실행 (자동매매)
nohup python3 -u autotrade_sj_v1.py > output.log 2>&1 &

#실행 확인
ps ax | grep .py

#vim 에디터로 열기
vim output.log
#로그 보기
cat output.log
#로그 맨 끝 보기
tail -f output.log

#종료하기 ex. kill -9 13586
kill -9 PID

# 웹 대시보드 그냥 실행하기
python3 -m streamlit run streamlit_app.py

#백그라운드 실행 (웹 대시보드)
nohup python3 -m streamlit run streamlit_app.py --server.port 8501 > streamlit.log 2>&1 &

#실행 확인
ps ax | grep .py

#vim 에디터로 열기
vim streamlit.log
#로그 보기
cat streamlit.log
```
