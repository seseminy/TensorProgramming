from playwright.sync_api import sync_playwright
import csv
from datetime import datetime
import pytz
import os

# GitHub Secrets에서 가져올 로그인 정보
USER_ID = os.environ.get("HANYANG_ID")
USER_PW = os.environ.get("HANYANG_PW")

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # 1. 대상 페이지로 이동
    target_url = "https://information.hanyang.ac.kr/facility/seat/reading-rooms-status?pageTabIndex=1"
    print(f"접속 시도: {target_url}")
    page.goto(target_url)
    page.wait_for_load_state("networkidle")

    # 2. 로그인 페이지인지 확인 후 로그인 수행
    try:
        # 로그인 입력창(userId) 또는 첫 번째 열람실 좌석 정보(id="61") 둘 중 하나가 보일 때까지 대기
        page.wait_for_selector("input[name='userId'], xpath=//*[@id='61']/a/div/span[2]", timeout=30000)
    except Exception as e:
        print("경고: 15초 내에 로그인 창도, 좌석 데이터도 나타나지 않았습니다. 네트워크 지연 가능성.")

    # 3. 로그인 처리 (입력창이 나타난 경우)
    if "login" in page.url.lower() or "oauth" in page.url.lower():
        print(f"로그인 페이지 진입 확인 ({page.url}). 로그인을 시도합니다.")
        
        try:
            page.locator("input[name='userId']").fill(USER_ID)
            page.locator("input[name='password']").fill(USER_PW)
            
            # 클릭 후 네트워크 요청 처리를 위해 약간의 대기
            with page.expect_navigation(timeout=20000):
                 page.locator("ik-login form button").first.click()
            
            print("로그인 버튼 클릭 완료, 페이지 이동 성공.")
            
        except Exception as e:
            print(f"로그인 과정 중 에러 발생: {e}")
            
    else:
        print(f"로그인 과정 생략 (현재 URL: {page.url})")
    
    # 3. 데이터 로딩 대기
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000) # 좌석 데이터 통신을 위한 대기시간


    # 4. 요청하신 XPath 목록 크롤링
    xpaths = [
        '//*[@id="61"]/a/div/span[2]',
        '//*[@id="63"]/a/div/span[2]',
        '//*[@id="131"]/a/div/span[2]',
        '//*[@id="132"]/a/div/span[2]'
    ]

    data = []
    for xpath in xpaths:
        try:
            element = page.locator(f"xpath={xpath}").first
            element.wait_for(state="visible", timeout=5000)
            data.append(element.inner_text().strip())
        except Exception:
            data.append("N/A")

    # 5. 시간 기록 (한국 시간 KST 기준)
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst).strftime('%Y-%m-%d %H')

    # 6. CSV 파일로 데이터 누적 저장
    file_path = 'seat_data.csv'
    file_exists = os.path.isfile(file_path)

    with open(file_path, mode='a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['시간', '제1열람실', '제2열람실', '집중열람실', '노상일HOLMZ'])
        writer.writerow([now] + data)
        
    print(f"[{now}] 크롤링 완료: {data}")
    browser.close()

if __name__ == "__main__":
    if not USER_ID or not USER_PW:
        print("경고: 환경변수(HANYANG_ID, HANYANG_PW)가 설정되지 않았습니다.")
    with sync_playwright() as playwright:
        run(playwright)
