import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import pytz

# 페이지 기본 설정
st.set_page_config(page_title="어제의 박스오피스", page_icon="🍿")

# 1. 한국 시간(KST) 기준 '어제' 날짜 계산하기
# 서버가 해외에 있어도 한국 시간으로 고정해서 계산합니다.
kst = pytz.timezone('Asia/Seoul')
today_kst = datetime.now(kst)
yesterday = today_kst - timedelta(days=1)
target_dt = yesterday.strftime('%Y%m%d')  # API 요청용 (예: 20231025)
display_date = yesterday.strftime('%Y년 %m월 %d일') # 화면 표시용

st.title(f"🍿 {display_date} 박스오피스")

# 2. 비밀 금고에서 인증키 불러오기
try:
    kobis_key = st.secrets["KOBIS_KEY"]
except KeyError:
    # 인증키가 설정되지 않았을 때 안내 메시지
    st.error("🔑 Streamlit Cloud의 Secrets 설정에 `KOBIS_KEY`를 추가해 주세요!")
    st.stop() # 이후 코드 실행 멈춤

# 3. 영화진흥위원회 API로 데이터 요청하기
url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
params = {
    "key": kobis_key,
    "targetDt": target_dt
}

try:
    response = requests.get(url, params=params)
    response.raise_for_status() # HTTP 오류 발생 시 예외 처리
    data = response.json()
except Exception as e:
    st.error("📡 데이터를 불러오는 중 문제가 발생했어요. 인터넷 연결이나 API 주소를 확인해 주세요.")
    st.stop()

# 4. 응답 데이터 오류 및 빈 목록 검사
if "faultInfo" in data:
    # 인증키 오류 등 API 자체에서 에러 메시지를 보냈을 때
    st.error("🚫 API 요청이 거절되었습니다. 발급받은 KOBIS_KEY가 정확한지 확인해 주세요.")
    st.stop()

# 데이터 목록 안전하게 꺼내기
movie_list = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])

if not movie_list:
    # 어제 날짜의 데이터가 아직 집계되지 않아 빈 목록이 왔을 때
    st.info(f"⏳ {display_date}의 박스오피스 결과가 아직 집계되지 않았거나 데이터가 없습니다. 조금 뒤에 다시 시도해 주세요.")
    st.stop()

# 5. 데이터를 판다스(Pandas) 표로 변환하고 숫자형으로 바꾸기
df = pd.DataFrame(movie_list)
# API에서 숫자가 모두 문자로 오기 때문에 진짜 숫자로 바꿔줍니다 (그래프 등을 위해)
df['rank'] = df['rank'].astype(int)
df['audiCnt'] = df['audiCnt'].astype(int)
df['audiAcc'] = df['audiAcc'].astype(int)
df['scrnCnt'] = df['scrnCnt'].astype(int)

# 6. 1위 영화 지표 카드 (크게 보여주기)
top1_movie = df.iloc[0] # 순위가 1등인 첫 번째 데이터 추출
st.subheader(f"🏆 1위: {top1_movie['movieNm']}")

# 화면을 3개의 칸으로 나누어 카드 배치
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="일일 관객수", value=f"{top1_movie['audiCnt']:,}명")
with col2:
    st.metric(label="누적 관객수", value=f"{top1_movie['audiAcc']:,}명")
with col3:
    st.metric(label="스크린수", value=f"{top1_movie['scrnCnt']:,}개")

st.divider() # 구분선

# 7. 관객수 상위 5편 막대그래프
st.subheader("📊 관객수 TOP 5")
# 상위 5개만 자른 뒤, 영화명을 기준으로 관객수 막대그래프를 그립니다
top5_df = df.head(5)[['movieNm', 'audiCnt']].set_index('movieNm')
st.bar_chart(top5_df)

st.divider()

# 8. 전체 데이터 표(테이블)로 보여주기
st.subheader("📋 전체 순위표")
# 필요한 기둥(컬럼)만 골라서 이름을 한글로 예쁘게 바꿉니다
display_df = df[['rank', 'movieNm', 'openDt', 'audiCnt', 'audiAcc', 'scrnCnt']]
display_df.columns = ['순위', '영화명', '개봉일', '관객수', '누적관객', '스크린수']

# 표를 화면에 출력 (hide_index=True로 숫자 인덱스 숨김)
st.dataframe(display_df, hide_index=True, use_container_width=True)
