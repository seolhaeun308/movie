import streamlit as st
import pandas as pd
import requests
import random
import plotly.express as px
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# --------------------------------------------------------
# 1. 페이지 기본 설정
# --------------------------------------------------------
st.set_page_config(page_title="박스오피스 대시보드", page_icon="🎬", layout="wide")
st.title("🎬 박스오피스 & 영화 추천 대시보드")

# --------------------------------------------------------
# 2. 보조 함수들 (날씨, 순위변동, 뱃지)
# --------------------------------------------------------
@st.cache_data(ttl=3600)
def get_today_weather():
    """현재 서울 날씨를 가져오는 함수 (회원가입 필요없는 무료 API)"""
    weather_url = "https://api.open-meteo.com/v1/forecast?latitude=37.5665&longitude=126.9780&current=weather_code&timezone=Asia%2FSeoul"
    try:
        res = requests.get(weather_url, timeout=5)
        code = res.json()["current"]["weather_code"]
        if code in [0, 1]: return "맑음", "☀️"
        elif code in [2, 3]: return "구름많음", "☁️"
        elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]: return "비", "🌧️"
        elif code in [71, 73, 75, 77, 85, 86]: return "눈", "❄️"
        else: return "흐림", "🌫️"
    except:
        return "알수없음", "❓"

def get_rank_symbol(inten):
    """순위 증감을 예쁜 화살표 기호로 변환"""
    if inten > 0: return f"▲ {inten}"
    elif inten < 0: return f"▼ {abs(inten)}"
    else: return "-"

def get_milestone_badge(acc):
    """누적 관객수에 따라 흥행 뱃지 부여"""
    if acc >= 10000000: return "👑 천만돌파!"
    elif acc >= 5000000: return "🔥 500만"
    elif acc >= 1000000: return "🎉 100만"
    else: return ""

# --------------------------------------------------------
# 3. 날짜 설정 및 API 인증키 불러오기
# --------------------------------------------------------
KOBIS_KEY = st.secrets["KOBIS_KEY"]

seoul_tz = ZoneInfo("Asia/Seoul")
today = datetime.now(seoul_tz)
yesterday = today - timedelta(days=1)

selected_date = st.date_input("📅 조회할 날짜를 선택하세요 (오늘 기록은 내일 제공됩니다)", value=yesterday, max_value=yesterday)
target_dt = selected_date.strftime("%Y%m%d")

# --------------------------------------------------------
# 4. KOBIS API 데이터 요청
# --------------------------------------------------------
url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
res = requests.get(url, params={"key": KOBIS_KEY, "targetDt": target_dt}, timeout=10)

if res.status_code != 200:
    st.error(f"서버 요청에 실패했습니다. (상태코드: {res.status_code})")
    st.stop()

data = res.json()

if "faultInfo" in data:
    st.error("🔑 인증키가 올바르지 않습니다. 스트림릿 클라우드의 비밀 금고(Secrets)에서 KOBIS_KEY 값을 다시 확인해 주세요.")
    st.stop()

box_list = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])

if not box_list:
    st.warning("⚠️ 선택하신 날짜의 박스오피스 자료가 아직 집계되지 않았거나 없습니다.")
    st.stop()

# --------------------------------------------------------
# 5. 데이터 가공
# --------------------------------------------------------
df = pd.DataFrame(box_list)

# 글자로 온 숫자들을 진짜 숫자로 변환 (계산을 위해)
for col in ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt", "showCnt", "salesShare"]:
    df[col] = pd.to_numeric(df[col])

# 파생 열 추가 (순위 변동, 기록 뱃지, 예고편 링크)
df["순위변동"] = df["rankInten"].apply(get_rank_symbol)
df["기록"] = df["audiAcc"].apply(get_milestone_badge)
df["예고편"] = "https://www.youtube.com/results?search_query=영화+" + df["movieNm"] + "+예고편"

top_movies = df["movieNm"].tolist()

# --------------------------------------------------------
# 6. 화면 출력 - (1) 날씨 기반 맞춤 영화 추천 (포스터 대신 예쁜 배너 디자인)
# --------------------------------------------------------
weather_text, weather_icon = get_today_weather()
st.divider()
st.subheader(f"{weather_icon} 오늘의 날씨 ({weather_text}) 맞춤 영화 추천")

# 날씨에 따른 추천 로직
if weather_text == "맑음":
    rec_movie = top_movies[0]
    msg = "화창한 날씨네요! 현재 극장가 예매율 1위 영화로 활기찬 하루를 보내보세요."
elif weather_text in ["비", "눈"]:
    rec_movie = top_movies[1] if len(top_movies) > 1 else top_movies[0]
    msg = f"{weather_text} 오는 날엔 실내 데이트가 최고죠! 관객들의 꾸준한 사랑을 받는 이 영화를 추천합니다."
else:
    rec_movie = random.choice(top_movies[2:5]) if len(top_movies) >= 5 else top_movies[0]
    msg = "포근한 느낌을 주는 날씨네요. 박스오피스 상위권의 숨은 재미를 찾아보세요!"

# CSS를 활용한 추천 영화 배너 (별도의 이미지 API 없이도 예쁘게 보이도록 디자인)
st.markdown(f"""
    <div style='background: linear-gradient(to right, #ff4b4b, #ff7676); padding: 30px; border-radius: 15px; text-align: center; color: white; margin-bottom: 20px;'>
        <h4 style='margin: 0; font-weight: normal; color: #ffecec;'>{weather_icon} {msg}</h4>
        <h1 style='margin: 15px 0 0 0; font-size: 40px; text-shadow: 2px 2px 4px rgba(0,0,0,0.2);'>🎬 {rec_movie}</h1>
    </div>
""", unsafe_allow_html=True)

# 예고편 버튼을 배너 바로 아래 중앙에 배치
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    st.link_button(f"🎥 '{rec_movie}' 유튜브 예고편 보러가기", f"https://www.youtube.com/results?search_query=영화+{rec_movie}+예고편", use_container_width=True)

st.divider()

# --------------------------------------------------------
# 7. 화면 출력 - (2) 1위 영화 요약
# --------------------------------------------------------
st.subheader(f"🏆 {selected_date.strftime('%Y년 %m월 %d일')} 박스오피스 요약")
top = df.sort_values("rank").iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("1위 영화", top["movieNm"])
c2.metric("당일 관객수", f"{top['audiCnt']:,}명", get_rank_symbol(top['rankInten']))
c3.metric("누적 관객수", f"{top['audiAcc']:,}명", top["기록"])
c4.metric("매출 점유율", f"{top['salesShare']}%")

st.write("") 

# --------------------------------------------------------
# 8. 화면 출력 - (3) 차트 시각화 (막대그래프 & 파이차트)
# --------------------------------------------------------
chart_col1, chart_col2 = st.columns(2)
top5 = df.sort_values("audiCnt", ascending=False).head(5)

with chart_col1:
    st.markdown("##### 📈 관객수 상위 5편")
    st.bar_chart(data=top5.set_index("movieNm")["audiCnt"], use_container_width=True)

with chart_col2:
    st.markdown("##### 🍕 매출 점유율 (상위 5편)")
    # Plotly를 이용한 도넛 차트
    fig = px.pie(top5, values='salesShare', names='movieNm', hole=0.4)
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------
# 9. 화면 출력 - (4) 박스오피스 상세 표
# --------------------------------------------------------
st.subheader("📋 전체 순위 상세")
# 표에 보여줄 열만 선택하고 이름 변경
table = df[["rank", "순위변동", "movieNm", "기록", "openDt", "audiCnt", "audiAcc", "scrnCnt", "salesShare", "예고편"]].copy()
table.columns = ["순위", "변동", "영화명", "기록", "개봉일", "당일관객", "누적관객", "스크린수", "점유율(%)", "예고편"]
table = table.sort_values("순위").reset_index(drop=True)

# 예고편 링크를 클릭 가능한 URL로 표시하기 위해 column_config 사용
st.dataframe(
    table,
    use_container_width=True,
    column_config={
        "예고편": st.column_config.LinkColumn("예고편 링크", display_text="유튜브 검색 🔗"),
        "당일관객": st.column_config.NumberColumn("당일관객", format="%d명"),
        "누적관객": st.column_config.NumberColumn("누적관객", format="%d명")
    }
)
