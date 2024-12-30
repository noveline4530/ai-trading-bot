import os
from dotenv import load_dotenv
load_dotenv()
import pyupbit
import pandas as pd
import pandas_ta as ta
from pydantic import BaseModel
import json
from openai import OpenAI
import schedule
import time
import requests
from datetime import datetime
import sqlite3
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, WebDriverException, NoSuchElementException
import logging
import base64


# Setup
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
upbit = pyupbit.Upbit(os.getenv("UPBIT_ACCESS_KEY"), os.getenv("UPBIT_SECRET_KEY"))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingDecision(BaseModel):
    decision: str
    percentage: int
    reason: str

def initialize_db(db_path='trading_decisions.sqlite'):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                decision TEXT,
                percentage REAL,
                reason TEXT,
                btc_balance REAL,
                krw_balance REAL,
                btc_avg_buy_price REAL,
                btc_krw_balance REAL,
                total_krw_balance REAL
            );
        ''')
        conn.commit()

def save_decision_to_db(decision, current_status):
    db_path = 'trading_decisions.sqlite'
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
    
        # Parsing current_status from JSON to Python dict
        status_dict = json.loads(current_status)
        current_price = pyupbit.get_orderbook(ticker="KRW-BTC")['orderbook_units'][0]["ask_price"]
        
        # Preparing data for insertion
        data_to_insert = (
            decision.get('decision'),
            decision.get('percentage', 100),  # Defaulting to 100 if not provided
            decision.get('reason', ''),  # Defaulting to an empty string if not provided
            status_dict.get('btc_balance'),
            status_dict.get('krw_balance'),
            status_dict.get('btc_avg_buy_price'),
            status_dict.get('btc_krw_balance'),
            status_dict.get('total_krw_balance')
        )
        
        # Inserting data into the database
        cursor.execute('''
            INSERT INTO decisions (timestamp, decision, percentage, reason, btc_balance, krw_balance, btc_avg_buy_price, btc_krw_balance, total_krw_balance)
            VALUES (datetime('now', 'localtime'), ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data_to_insert)
    
        conn.commit()

def fetch_last_decisions(db_path='trading_decisions.sqlite', num_decisions=10):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, decision, percentage, reason, btc_balance, krw_balance, btc_avg_buy_price, btc_krw_balance, total_krw_balance FROM decisions
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (num_decisions,))
        decisions = cursor.fetchall()

        if decisions:
            formatted_decisions = []
            for decision in decisions:
                # Converting timestamp to milliseconds since the Unix epoch
                ts = datetime.strptime(decision[0], "%Y-%m-%d %H:%M:%S")
                ts_millis = int(ts.timestamp() * 1000)
                
                formatted_decision = {
                    "timestamp": ts_millis,
                    "decision": decision[1],
                    "percentage": decision[2],
                    "reason": decision[3],
                    "btc_balance": decision[4],
                    "krw_balance": decision[5],
                    "btc_avg_buy_price": decision[6],
                    "btc_krw_balance": decision[7],
                    "total_krw_balance": decision[8]
                }
                formatted_decisions.append(str(formatted_decision))
            return "\n".join(formatted_decisions)
        else:
            return "No decisions found."

def get_current_status():
    orderbook = pyupbit.get_orderbook(ticker="KRW-BTC")
    current_time = orderbook['timestamp']
    btc_balance = 0
    krw_balance = 0
    total_krw_balance = 0
    btc_avg_buy_price = 0
    btc_krw_balance = 0
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == "BTC":
            btc_balance = float(b['balance'])
            btc_avg_buy_price = float(b['avg_buy_price'])
            btc_krw_balance = int(btc_balance * btc_avg_buy_price)
        if b['currency'] == "KRW":
            krw_balance = int(float(b['balance']))
    total_krw_balance = int(float(krw_balance + btc_krw_balance))
    current_status = {
        'current_time': current_time,
        'orderbook': orderbook,
        'btc_balance': btc_balance,
        'krw_balance': krw_balance, 
        'btc_avg_buy_price': btc_avg_buy_price,
        'btc_krw_balance': btc_krw_balance,
        'total_krw_balance': total_krw_balance
    }
    return json.dumps(current_status)


def fetch_and_prepare_data():
    # Fetch data
    df_daily = pyupbit.get_ohlcv("KRW-BTC", "day", count=30)
    df_hourly = pyupbit.get_ohlcv("KRW-BTC", interval="minute60", count=24)

    # Define a helper function to add indicators
    def add_indicators(df):
        # Moving Averages
        df['SMA_7'] = ta.sma(df['close'], length=7)
        df['EMA_7'] = ta.ema(df['close'], length=7)
        df['EMA_14'] = ta.ema(df['close'], length=14)
        df['EMA_35'] = ta.ema(df['close'], length=35)
        # df['EMA_100'] = ta.ema(df['close'], length=100)

        # RSI
        df['RSI_14'] = ta.rsi(df['close'], length=14)

        # Stochastic Oscillator
        stoch = ta.stoch(df['high'], df['low'], df['close'], k=14, d=3, smooth_k=3)
        df = df.join(stoch)

        # MACD
        ema_fast = df['close'].ewm(span=12, adjust=False).mean()
        ema_slow = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema_fast - ema_slow
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Histogram'] = df['MACD'] - df['Signal_Line']

        # Bollinger Bands
        df['Middle_Band'] = df['close'].rolling(window=20).mean()
        # Calculate the standard deviation of closing prices over the last 20 days
        std_dev = df['close'].rolling(window=20).std()
        # Calculate the upper band (Middle Band + 2 * Standard Deviation)
        df['Upper_Band'] = df['Middle_Band'] + (std_dev * 2)
        # Calculate the lower band (Middle Band - 2 * Standard Deviation)
        df['Lower_Band'] = df['Middle_Band'] - (std_dev * 2)

        return df

    # Add indicators to both dataframes
    df_daily = add_indicators(df_daily)
    df_hourly = add_indicators(df_hourly)

    combined_df = pd.concat([df_daily, df_hourly], keys=['daily', 'hourly'])
    combined_data = combined_df.to_json(orient='split')

    return json.dumps(combined_data)

def fetch_fear_and_greed_index(limit=1, date_format=''):
    """
    Fetches the latest Fear and Greed Index data.
    Parameters:
    - limit (int): Number of results to return. Default is 1.
    - date_format (str): Date format ('us', 'cn', 'kr', 'world'). Default is '' (unixtime).
    Returns:
    - dict or str: The Fear and Greed Index data in the specified format.
    """
    base_url = "https://api.alternative.me/fng/"
    params = {
        'limit': limit,
        'format': 'json',
        'date_format': date_format
    }
    response = requests.get(base_url, params=params)
    myData = response.json()['data']
    resStr = ""
    for data in myData:
        resStr += str(data)
    return resStr

def capture_and_encode_screenshot(driver):
    try:
        # 스크린샷 캡처
        png = driver.get_screenshot_as_png()
        
        # PIL Image로 변환
        img = Image.open(io.BytesIO(png))
        
        # 이미지 리사이즈 (OpenAI API 제한에 맞춤)
        img.thumbnail((2000, 2000))
        
        # 현재 시간을 파일명에 포함
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"upbit_chart_{current_time}.png"
        
        # 현재 스크립트의 경로를 가져옴
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 파일 저장 경로 설정
        file_path = os.path.join(script_dir, filename)
        
        # 이미지 파일로 저장
        img.save(file_path)
        logger.info(f"스크린샷이 저장되었습니다: {file_path}")
        
        # 이미지를 바이트로 변환
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        
        # base64로 인코딩
        base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        return base64_image, file_path
    except Exception as e:
        logger.error(f"스크린샷 캡처 및 인코딩 중 오류 발생: {e}")
        return None, None

def get_current_base64_image():
    try:
        # 로컬용 셋팅 - Set up Chrome options for headless mode
        # chrome_options = Options()
        # chrome_options.add_argument("--start-maximized")
        # chrome_options.add_argument("--headless")  # 디버깅을 위해 헤드리스 모드 비활성화
        # chrome_options.add_argument("--disable-gpu")
        # chrome_options.add_argument("--no-sandbox")
        # chrome_options.add_argument("--disable-dev-shm-usage")
        # chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

        # # Initialize the WebDriver with the specified options
        # logger.info("ChromeDriver 설정 중...")
        # service = Service(ChromeDriverManager().install())
        # driver = webdriver.Chrome(service=service, options=chrome_options)

        # AWS EC2 서버용 셋팅
        logger.info("ChromeDriver 설정 중...")
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # 헤드리스 모드 사용
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")

        service = Service('/usr/bin/chromedriver')  # Specify the path to the ChromeDriver executable

        # Initialize the WebDriver with the specified options
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Navigate to the desired webpage
        driver.get("https://upbit.com/full_chart?code=CRIX.UPBIT.KRW-BTC")
        logger.info("페이지 로드 완료")

        logger.info("차트 작업 시작")
        # Wait for the page to load completely
        wait = WebDriverWait(driver, 10)  # 10 seconds timeout

        # Wait for the first menu item to be clickable and click it (시간메뉴)
        first_menu_item = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='fullChartiq']/div/div/div[1]/div/div/cq-menu[1]")))
        first_menu_item.click()

        # Wait for the "4 Hour" option to be clickable and click it
        four_hour_option = wait.until(EC.element_to_be_clickable((By.XPATH, "//cq-item[@stxtap=\"Layout.setPeriodicity(4,60,'minute')\"]")))
        four_hour_option.click()

        # Wait for the indicators menu item to be clickable and click it (지표메뉴)
        indicators_menu_item = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='fullChartiq']/div/div/div[1]/div/div/cq-menu[3]")))
        indicators_menu_item.click()

        bolinger_band = wait.until(EC.element_to_be_clickable((By.XPATH, "//cq-item[translate[@original='Bollinger Bands']]")))
        bolinger_band.click()

        # Wait for the indicators menu item to be clickable and click it (지표메뉴)
        indicators_menu_item = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='fullChartiq']/div/div/div[1]/div/div/cq-menu[3]")))
        indicators_menu_item.click()

        # Wait for the indicators container to be present
        indicators_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "cq-scroll.ps-container")))

        # Scroll the container to make the "MACD" indicator visible
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight / 2.5", indicators_container)

        # Wait for the "MACD" indicator to be clickable and click it
        macd_indicator = wait.until(EC.element_to_be_clickable((By.XPATH, "//cq-item[translate[@original='MACD']]")))
        macd_indicator.click()
        logger.info("차트 작업 완료")

        # Take a screenshot to verify the actions
        chart_image, saved_file_path = capture_and_encode_screenshot(driver)
        logger.info(f"스크린샷 캡처 완료. 저장된 파일 경로: {saved_file_path}")
    except Exception as e:
        logger.error("Error making current chart image: {e}")
        return ""
    finally:
        # Close the browser
        driver.quit()
        return chart

def get_instructions(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            instructions = file.read()
        return instructions
    except FileNotFoundError:
        logger.error("File not found.")
    except Exception as e:
        logger.error("An error occurred while reading the file:", e)

def analyze_data_with_gpt4(data_json, last_decisions, fear_and_greed, current_status, current_base64_image):
    instructions_path = "instructions_sj_v1.md"
    try:
        instructions = get_instructions(instructions_path)
        if not instructions:
            logger.info("No instructions found.")
            return None
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": data_json},
                {"role": "user", "content": last_decisions},
                {"role": "user", "content": fear_and_greed},
                {"role": "user", "content": current_status},
                {"role": "user", "content": {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{current_base64_image}"
                        }
                    }}
            ],
            response_format={"type":"json_object"}
        )
        advice = response.choices[0].message.content
        logger.info(f"##AI Result: {advice}")
        return advice
    except Exception as e:
        logger.error(f"Error in analyzing data with GPT-4: {e}")
        return None

def execute_buy(percentage):
    logger.info("Attempting to buy BTC with a percentage of KRW balance...")
    try:
        krw_balance = upbit.get_balance("KRW")
        amount_to_invest = krw_balance * (percentage / 100)
        if amount_to_invest > 5000:  # Ensure the order is above the minimum threshold
            result = upbit.buy_market_order("KRW-BTC", amount_to_invest * 0.9995)  # Adjust for fees
            logger.info("Buy order successful:", result)
    except Exception as e:
        logger.error(f"Failed to execute buy order: {e}")

def execute_sell(percentage):
    logger.info("Attempting to sell a percentage of BTC...")
    try:
        btc_balance = upbit.get_balance("BTC")
        amount_to_sell = btc_balance * (percentage / 100)
        current_price = pyupbit.get_orderbook(ticker="KRW-BTC")['orderbook_units'][0]["ask_price"]
        if current_price * amount_to_sell > 5000:  # Ensure the order is above the minimum threshold
            result = upbit.sell_market_order("KRW-BTC", amount_to_sell)
            logger.info("Sell order successful:", result)
    except Exception as e:
        logger.error(f"Failed to execute sell order: {e}")

def make_decision_and_execute():
    logger.info("Making decision and executing...")
    try:
        data_json = fetch_and_prepare_data()
        last_decisions = fetch_last_decisions()
        fear_and_greed = fetch_fear_and_greed_index(limit=30)
        current_status = get_current_status()
        current_base64_image = get_current_base64_image()
    except Exception as e:
        logger.error(f"Error: {e}")
    else:
        max_retries = 5
        retry_delay_seconds = 5
        decision = None
        for attempt in range(max_retries):
            try:
                advice = analyze_data_with_gpt4(data_json, last_decisions, fear_and_greed, current_status, current_base64_image)
                decision = json.loads(advice)
                break
            except Exception as e:
                logger.error(f"JSON parsing failed: {e}. Retrying in {retry_delay_seconds} seconds...")
                time.sleep(retry_delay_seconds)
                logger.error(f"Attempt {attempt + 2} of {max_retries}")
        if not decision:
            logger.error("Failed to make a decision after maximum retries.")
            return
        else:
            try:
                percentage = decision.get('percentage', 100)

                if decision.get('decision') == "buy":
                    execute_buy(percentage)
                elif decision.get('decision') == "sell":
                    execute_sell(percentage)
                
                save_decision_to_db(decision, current_status)
            except Exception as e:
                logger.error(f"Failed to execute the decision or save to DB: {e}")

if __name__ == "__main__":
    initialize_db()
    make_decision_and_execute()

    # Schedule the task to run at 00:01
    schedule.every().day.at("00:01").do(make_decision_and_execute)

    # Schedule the task to run at 04:01
    schedule.every().day.at("08:01").do(make_decision_and_execute)

    # Schedule the task to run at 16:01
    schedule.every().day.at("16:01").do(make_decision_and_execute)

    while True:
        schedule.run_pending()
        time.sleep(1)