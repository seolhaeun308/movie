import streamlit as st
from openai import OpenAI

# 페이지 기본 설정
st.set_page_config(
    page_title="정보 선생님 AI 채팅",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 친절한 정보 선생님")
st.write("궁금한 점이 있다면 무엇이든 물어보세요!")

# 1. 비밀 금고(st.secrets)에서 Gemini API 키 불러오기
try:
    gemini_api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("비밀 금고(st.secrets)에 GEMINI_API_KEY가 설정되어 있지 않습니다. 설정을 확인해 주세요.")
    st.stop()

# 2. OpenAI 라이브러리를 활용해 Gemini API 클라이언트 설정
# 제공해주신 구글 엔드포인트와 gemini-2.5-flash 모델명을 그대로 사용합니다.
client = OpenAI(
    api_key=gemini_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

# 3. 이전 대화 기억(세션 상태) 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 4. 화면에 이전 대화 기록(말풍선)을 순서대로 다시 출력하기
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. 사용자가 채팅 입력창에 메시지를 적었을 때 동작
if prompt := st.chat_input("선생님께 질문을 입력하세요..."):
    
    # 사용자가 보낸 메시지를 대화 기록에 저장
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 화면에 사용자 메시지 말풍선 표시
    with st.chat_message("user"):
        st.markdown(prompt)

    # 6. AI의 성격(시스템 프롬프트) 설정 및 이전 대화 내용 합치기
    system_prompt = {
        "role": "system",
        "content": "너는 중고등학생에게 설명하는 친절한 정보 선생님이야. 어려운 말은 쉬운 말로 바꿔 주고, 반드시 순수 한국어로만 답해"
    }
    
    # 시스템 성격과 지금까지의 대화 목록을 합쳐서 API에 전달
    full_messages = [system_prompt] + st.session_state.messages

    # 7. AI의 답변을 실시간 스트리밍 형태로 받아와 말풍선으로 출력
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # 스트리밍 활성화(stream=True)
            response = client.chat.completions.create(
                model="gemini-2.5-flash",
                messages=full_messages,
                stream=True,
            )
            
            # 글자가 실시간으로 흘러나오도록 조각(chunk)을 이어붙임
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    full_response += chunk.choices[0].delta.content
                    message_placeholder.markdown(full_response + "▌")
            
            # 최종 완성된 답변 출력 (커서 제거)
            message_placeholder.markdown(full_response)
            
            # AI의 답변을 대화 기록에 저장
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            # 8. 요청이 실패할 경우 빨간 오류 화면 대신 친절한 안내 문구 표시
            message_placeholder.error("죄송해요, 답변을 가져오는 중에 문제가 생겼어요. 잠시 후에 다시 시도해 주세요!")
