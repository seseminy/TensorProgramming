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

    # 🚨 [핵심 1] 팝업창(Alert, Confirm) 발생 시 자동 수락 및 내용 기록
    def handle_dialog(dialog):
        print(f"\n🚨 [웹 팝업 감지] 팝업 내용: {dialog.message}")
        dialog.accept() # 팝업의 '확인' 버튼을 자동으로 누름

    page.on("dialog", handle_dialog)

    target_url = "https://information.hanyang.ac.kr/facility/seat/reading-rooms-status?pageTabIndex=1"
    print(f"접속 시도: {target_url}")
    page.goto(target_url)

    xpaths = [
        '//*[@id="61"]/a/div/span[2]',
        '//*[@id="63"]/a/div/span[2]',
        '//*[@id="131"]/a/div/span[2]',
        '//*[@id="132"]/a/div/span[2]'
    ]
    
    data = ['N/A', 'N/A', 'N/A', 'N/A']
    success = False
    
    max_retries = 30
    for attempt in range(max_retries):
        current_url = page.url.lower()
        print(f"[시도 {attempt+1}/{max_retries}] 현재 URL: {current_url}")
        
        if "login" in current_url or "oauth" in current_url:
            try:
                # 🚨 [핵심 2] 무한정 기다리지 않도록 timeout을 1초(1000ms)로 짧게 설정
                if page.locator("input[name='userId']").is_visible(timeout=1000):
                    print("로그인 폼 발견. ID/PW 입력 및 로그인 시도...")
                    # 기존에 값이 남아있을 수 있으므로 지우고(clear) 다시 입력
                    page.locator("input[name='userId']").clear(timeout=1000)
                    page.locator("input[name='userId']").fill(USER_ID, timeout=1000)
                    
                    page.locator("input[name='password']").clear(timeout=1000)
                    page.locator("input[name='password']").fill(USER_PW, timeout=1000)
                    
                    page.locator("ik-login form button").first.click(timeout=2000)
                    
                    print("로그인 버튼 클릭 완료. 전환 대기...")
                    page.wait_for_timeout(5000)
                    continue 
            except Exception as e:
                # Timeout 에러가 발생해도 크롤러가 멈추지 않고 다음 루프를 돌게 함
                print("로그인 폼 로딩 대기 중...")
                
        elif "reading-rooms-status" in current_url:
            # 🚨 [핵심 3] 열람실 페이지에 왔는데 15번(약 30초)이나 
            # 데이터를 못 찾고 있다면 세션이 꼬인 것이므로 새로고침(Reload)
            if attempt == 15:
                print("⚠️ 로딩 지연 감지. 페이지를 강제로 새로고침합니다.")
                page.reload()
                page.wait_for_timeout(3000)
                continue

            try:
                first_seat = page.locator(f"xpath={xpaths[0]}").first
                
                # 좌석 정보가 보이는지 1초만 빠르게 확인
                if first_seat.is_visible(timeout=1000):
                    print("좌석 데이터 렌더링 확인! 데이터 추출 시작...")
                    temp_data = []
                    for xpath in xpaths:
                        element = page.locator(f"xpath={xpath}").first
                        temp_data.append(element.inner_text().strip())
                    
                    if len(temp_data) == 4 and "N/A" not in temp_data:
                        data = temp_data
                        success = True
                        print("데이터 추출 성공!")
                        break 
            except Exception:
                pass # 아직 로딩 중
                
        time.sleep(2)

    # 실패 시 디버그용 스크린샷 
    if not success:
        print("최대 대기 시간을 초과했습니다. 디버깅 스크린샷을 저장합니다.")
        page.screenshot(path="debug_screen.png", full_page=True)
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(page.content())

    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst).strftime('%Y-%m-%d %H')

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
