from playwright.sync_api import sync_playwright
import csv
from datetime import datetime
import pytz
import os
import time

USER_ID = os.environ.get("HANYANG_ID")
USER_PW = os.environ.get("HANYANG_PW")

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    target_url = "https://information.hanyang.ac.kr/facility/seat/reading-rooms-status?pageTabIndex=1"
    print(f"접속 시도: {target_url}")
    page.goto(target_url)

    # 요청하신 XPath 목록
    xpaths = [
        '//*[@id="61"]/a/div/span[2]',
        '//*[@id="63"]/a/div/span[2]',
        '//*[@id="131"]/a/div/span[2]',
        '//*[@id="132"]/a/div/span[2]'
    ]
    
    data = ['N/A', 'N/A', 'N/A', 'N/A']
    success = False
    
    # === [강력한 폴링 루프: 최대 60초 동안 지속적으로 상태를 체크하며 시도] ===
    max_retries = 30
    for attempt in range(max_retries):
        current_url = page.url.lower()
        print(f"[시도 {attempt+1}/{max_retries}] 현재 URL: {current_url}")
        
        # 상태 1: 로그인 페이지에 머물고 있는 경우 -> 로그인 시도
        if "login" in current_url or "oauth" in current_url:
            try:
                # 로그인 폼이 아직 안 떴을 수 있으므로 1초 대기 후 시도
                if page.locator("input[name='userId']").is_visible():
                    print("로그인 폼 발견. ID/PW 입력 및 로그인 시도...")
                    page.locator("input[name='userId']").fill(USER_ID)
                    page.locator("input[name='password']").fill(USER_PW)
                    page.locator("ik-login form button").first.click()
                    
                    # 로그인 버튼 클릭 후 5초 정도 페이지 전환을 기다려줌
                    page.wait_for_timeout(5000)
                    continue # 다음 루프로 넘어가서 URL 상태 재확인
            except Exception as e:
                pass # 아직 렌더링 중이면 무시하고 다음 루프에서 재시도
                
        # 상태 2: 열람실 페이지에 진입한 경우 -> 데이터 추출 시도
        elif "reading-rooms-status" in current_url:
            try:
                # 첫 번째 좌석 정보가 화면에 보이는지 확인
                first_seat = page.locator(f"xpath={xpaths[0]}").first
                
                if first_seat.is_visible():
                    print("좌석 데이터 렌더링 확인! 데이터 추출 시작...")
                    temp_data = []
                    for xpath in xpaths:
                        element = page.locator(f"xpath={xpath}").first
                        temp_data.append(element.inner_text().strip())
                    
                    # 정상적으로 4개의 데이터를 모두 찾았다면 루프 종료
                    if len(temp_data) == 4 and "N/A" not in temp_data:
                        data = temp_data
                        success = True
                        print("데이터 추출 성공!")
                        break 
            except Exception as e:
                pass # 데이터를 못 찾았으면 아직 로딩 중인 것이므로 계속 대기
                
        # 아무 상태도 아니거나, 로딩 중이면 2초 대기 후 다시 상태 체크
        time.sleep(2)
        
    # ======================================================================

    # 60초가 지나도 실패한 경우를 위한 디버깅 캡처
    if not success:
        print("최대 대기 시간을 초과하여 데이터를 가져오지 못했습니다. 디버깅 스크린샷을 저장합니다.")
        page.screenshot(path="debug_screen.png", full_page=True)
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(page.content())

    # 5. 시간 기록 (한국 시간 KST 기준)
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst).strftime('%Y-%m-%d %H')

    # 6. CSV 파일 저장 로직 (이전과 동일)
    file_path = 'seat_data.csv'
    file_exists = os.path.isfile(file_path)

    with open(file_path, mode='a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['시간', '제1열람실', '제2열람실', '집중열람실', '노상일HOLMZ'])
        writer.writerow([now] + data)
        
    print(f"[{now}] 최종 크롤링 결과: {data}")
    browser.close()

if __name__ == "__main__":
    if not USER_ID or not USER_PW:
        print("경고: 환경변수 설정 안됨")
    with sync_playwright() as playwright:
        run(playwright)
