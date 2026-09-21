import streamlit as st
import pandas as pd
import requests
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# --------------------------------------------------------
# 1. 페이지 기본 설정
# --------------------------------------------------------
st.set_page_config(page_title="박스오피스 대시보드", page_icon="🎬", layout="wide")
st.title("🎬 박스오피스 & 영화 추천")

# --------------------------------------------------------
# 2. 날씨 정보를 가져오는 함수 (무료 Open-Meteo API 사용)
# --------------------------------------------------------
@st.cache_data(ttl=3600)  # 1시간 동안 날씨 데이터 캐싱(임시 저장)하여 서버 부담 줄이기
def get_today_weather():
    # 서울 기준 위도/경도로 현재 날씨 코드 요청 (API 키 불필요)
    weather_url = "https://api.open-meteo.com/v1/forecast?latitude=37.5665&longitude=126.9780&current=weather_code&timezone=Asia%2FSeoul"
    try:
        res = requests.get(weather_url, timeout=5)
        code = res.json()["current"]["weather_code"]
        
        # WMO 날씨 코드 해석 (0: 맑음, 1~3: 구름, 51~67: 비, 71~77: 눈 등)
        if code in [0, 1]: return "맑음", "☀️"
        elif code in [2, 3]: return "구름많음", "☁️"
        elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]: return "비", "🌧️"
        elif code in [71, 73, 75, 77, 85, 86]: return "눈", "❄️"
        else: return "흐림", "🌫️"
    except:
        return "알수없음", "❓"

# --------------------------------------------------------
# 3. 날짜 설정 및 API 인증키 불러오기
# --------------------------------------------------------
# 비밀 금고에서 인증키 꺼내기 (코드에 절대 노출 금지)
KOBIS_KEY = st.secrets["KOBIS_KEY"]

# 한국 시간 기준 객체 생성
seoul_tz = ZoneInfo("Asia/Seoul")
today = datetime.now(seoul_tz)
yesterday = today - timedelta(days=1)

# '각 날짜별' 조회를 위해 날짜 선택기 추가 (기본값과 최대 선택 가능 날짜를 '어제'로 고정)
selected_date = st.date_input("📅 조회할 날짜를 선택하세요 (오늘 기록은 내일 제공됩니다)", value=yesterday, max_value=yesterday)
target_dt = selected_date.strftime("%Y%m%d")

# --------------------------------------------------------
# 4. KOBIS API 데이터 요청
# --------------------------------------------------------
url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
res = requests.get(url, params={"key": KOBIS_KEY, "targetDt": target_dt}, timeout=10)

# 네트워크 에러 등 API 요청 자체가 실패했을 때
if res.status_code != 200:
    st.error(f"서버 요청에 실패했습니다. 잠시 후 다시 시도해주세요. (상태코드: {res.status_code})")
    st.stop()

data = res.json()

# KOBIS는 키가 틀려도 상태코드 200을 줍니다. 대신 faultInfo 상자가 옵니다.
if "faultInfo" in data:
    st.error("🔑 인증키가 올바르지 않습니다. 스트림릿 클라우드의 비밀 금고(Secrets)에서 KOBIS_KEY 값을 다시 확인해 주세요.")
    st.stop()

# 영화 목록 추출
box_list = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])

# 영화 목록이 비어있을 때 (KOBIS 서버에서 아직 집계를 안 했거나, 너무 옛날인 경우)
if not box_list:
    st.warning("⚠️ 선택하신 날짜의 박스오피스 자료가 아직 집계되지 않았거나 없습니다. 날짜를 변경해 보세요.")
    st.stop()

# --------------------------------------------------------
# 5. 데이터 가공 및 화면 출력
# --------------------------------------------------------
df = pd.DataFrame(box_list)

# 글자로 온 숫자들을 진짜 숫자로 바꾸기 (매출액 점유율인 salesShare 추가)
for col in ["rank", "audiCnt", "audiAcc", "scrnCnt", "showCnt", "salesShare"]:
    df[col] = pd.to_numeric(df[col])

# 날씨 기반 추천 로직 생성
weather_text, weather_icon = get_today_weather()
top_movies = df["movieNm"].tolist()

st.divider()
st.subheader(f"{weather_icon} 오늘의 날씨 ({weather_text}) 맞춤 영화 추천")
if weather_text == "맑음":
    st.info(f"화창한 날씨네요! 현재 가장 인기 있는 1위 영화 **'{top_movies[0]}'**을(를) 추천합니다. 극장 나들이 어떠세요?")
elif weather_text in ["비", "눈"]:
    st.info(f"{weather_text} 오는 날엔 실내 데이트가 최고죠! 관객들의 꾸준한 사랑을 받는 **'{top_movies[1] if len(top_movies) > 1 else top_movies[0]}'**을(를) 추천해 드려요.")
else:
    # 흐리거나 구름 많은 날엔 상위 3~5위 중 랜덤 추천
    rec_movie = random.choice(top_movies[2:5]) if len(top_movies) >= 5 else top_movies[0]
    st.info(f"포근한 느낌을 주는 날씨네요. 숨은 재미를 찾아서 **'{rec_movie}'** 한 편 어떠신가요?")
st.divider()

# 1위 영화 지표 카드 세 장
st.subheader(f"🏆 {selected_date.strftime('%Y년 %m월 %d일')} 박스오피스 요약")
top = df.sort_values("rank").iloc[0]
c1, c2, c3 = st.columns(3)
c1.metric("1위 영화", top["movieNm"])
c2.metric("당일 관객수", f"{top['audiCnt']:,}명")
c3.metric("누적 관객수", f"{top['audiAcc']:,}명")

st.write("") # 빈 줄 삽입

# 표를 한국어 열 이름으로 정리
# KOBIS에서 예매율은 제공하지 않으므로, 당일 예매 비중을 보여주는 '매출점유율(salesShare)'을 사용합니다.
table = df[["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt", "salesShare"]].copy()
table.columns = ["순위", "영화명", "개봉일", "당일관객수", "누적관객수", "스크린수", "매출점유율(%)"]
table = table.sort_values("순위").reset_index(drop=True)

col1, col2 = st.columns([1.5, 1])

with col1:
    st.subheader("📋 전체 순위 및 점유율")
    st.caption("※ KOBIS API는 실시간 예매율 대신 당일 티켓 판매 비중인 '매출점유율'을 제공합니다.")
    st.dataframe(table, use_container_width=True)

with col2:
    st.subheader("📈 관객수 상위 5편")
    top5 = table.sort_values("당일관객수", ascending=False).head(5)
    st.bar_chart(data=top5.set_index("영화명")["당일관객수"], use_container_width=True)
