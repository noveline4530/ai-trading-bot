import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px

# 데이터베이스 연결 함수
def get_connection():
    return sqlite3.connect('trading_decisions.sqlite')

# 데이터 로드 함수
def load_data():
    conn = get_connection()
    query = "SELECT * FROM decisions"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# 수익률 계산 함수
def calculate_profit(initial_balance: int, current_balance: int) -> float:
    """
    수익률을 계산하고 문자열 포맷으로 반환하는 함수 (%.2f 형식)
    :param initial_balance: 초기 자금 (int)
    :param current_balance: 현재 자금 (int)
    :return: 수익률 (%) (str, 소수점 둘째 자리까지)
    """
    if initial_balance <= 0:
        raise ValueError("초기 자금은 0보다 커야 합니다.")
    
    return_rate = ((current_balance - initial_balance) / initial_balance) * 100
    return f"{return_rate:.2f}"

# Updated function to create styled line charts without markers
def create_styled_line_chart_without_markers(df, x_col, y_col, title):
    """
    Creates a styled line chart without markers.
    :param df: DataFrame containing the data.
    :param x_col: Column name for the x-axis.
    :param y_col: Column name for the y-axis.
    :param title: Title of the chart.
    :return: Plotly figure object.
    """
    fig = px.line(
        df,
        x=x_col,
        y=y_col,
        title=title,
        template="plotly_white",
        labels={x_col: "Timestamp", y_col: "Value (KRW)"},
    )
    fig.update_traces(line=dict(width=2))
    fig.update_layout(
        title=dict(font=dict(size=20, color="#333"), x=0.5),
        xaxis=dict(title=dict(font=dict(size=14)), tickangle=-45),
        yaxis=dict(title=dict(font=dict(size=14))),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    return fig

# 메인 함수
def main():
    st.set_page_config(
        page_title="SJ's AI Trading Bot",
        page_icon="💰",
        layout="wide",  # 레이아웃 설정 ("centered" 또는 "wide")
    )
    st.title('AI Bitcoin Trading Bot (SJ o1-mini ver1.)')

    # 데이터 로드
    df = load_data()

    # 현재 수익률
    st.header(f"💸누적 수익률: {calculate_profit(1000000, df.iloc[-1]['total_krw_balance'])}%")
    
    # 기본 통계
    st.header('거래 요약')
    st.write(f"Total number of trades: {len(df)}")
    st.write(f"First trade date: {df['timestamp'].min()}")
    st.write(f"Last trade date: {df['timestamp'].max()}")

    # 거래 내역 표시
    st.header('거래 이력')
    st.dataframe(df.iloc[:, 1:])

    # 거래 결정 분포
    st.header('거래 결정 분포')
    decision_counts = df['decision'].value_counts()
    fig = px.pie(values=decision_counts.values, names=decision_counts.index, title='Trade Decisions')
    st.plotly_chart(fig)

    # BTC 잔액 변화
    st.header('보유 BTC 잔액 변화')
    btc_balance_fig = create_styled_line_chart_without_markers(df, x_col='timestamp', y_col='btc_krw_balance', title='BTC KRW Balance')
    st.plotly_chart(btc_balance_fig)

    # KRW 잔액 변화
    st.header('보유 KRW 잔액 변화')
    krw_balance_fig = create_styled_line_chart_without_markers(df, x_col='timestamp', y_col='krw_balance', title='KRW Balance')
    st.plotly_chart(krw_balance_fig)

    # 총 보유 잔액 변화
    st.header('총 보유 잔액 변화')
    total_balance_fig = create_styled_line_chart_without_markers(df, x_col='timestamp', y_col='total_krw_balance', title='Total Balance')
    st.plotly_chart(total_balance_fig)

if __name__ == "__main__":
    main()