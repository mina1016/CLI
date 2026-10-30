import os
import sys
import subprocess
import argparse
import requests

# 1. Git 변경사항 수집 함수
def get_git_diff(safe_mode=False):
    # status 확인
    status = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    if not status.stdout.strip():
        print("[INFO] 변경 사항이 없습니다. 작업을 종료합니다.")
        sys.exit(0)
    
    # diff 수집 (staged 상태의 파일들)
    diff = subprocess.run(['git', 'diff', '--cached'], capture_output=True, text=True)
    diff_text = diff.stdout
    
    # [요구사항] Safe-mode: Diff 일부만 전송 (최대 200줄로 제한)
    if safe_mode:
        lines = diff_text.split('\n')
        if len(lines) > 200:
            diff_text = '\n'.join(lines[:200]) + "\n... [SAFE MODE: Diff 텍스트가 200줄로 제한되었습니다]"
            
    return diff_text, len(diff_text.split('\n'))

# 2. AI API 호출 함수 (오류 수정됨)
def call_ai_api(prompt, model, temperature, max_tokens):
    # 보안을 위해 코드에 API 키를 직접 적지 않고 환경변수에서 가져옵니다.
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        print("[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.")
        print('## 예) export AI_API_KEY="sk-cody-live-..."')
        sys.exit(1)

    print(f"[INFO] AI API 요청 중... (Endpoint: copa.codyssey.kr, Model: {model})")
    
    try:
        # requests 패키지를 활용한 REST API 호출
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        response = requests.post(
            "https://copa.codyssey.kr/v1/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status() # HTTP 응답 코드가 200이 아니면 예외 발생
        
        # JSON 응답에서 텍스트 결과만 추출하여 반환
        return response.json()["choices"][0]["message"]["content"]
        
    except Exception as e:
        print(f"[ERROR] API 호출 실패: {e}")
        sys.exit(1)

# 3. 메인 로직
def main():
    parser = argparse.ArgumentParser(description="AI 기반 Git 커밋/PR 자동 생성기")
    parser.add_argument("command", choices=["commit", "pr"], help="실행할 명령어 (commit 또는 pr)")
    parser.add_argument("--model", default="gpt-5-mini", help="사용할 AI 모델")
    parser.add_argument("--temperature", type=float, default=0.7, help="창의성 조절 (0.0 ~ 1.0)")
    parser.add_argument("--max-tokens", type=int, default=500, help="최대 생성 토큰 수")
    parser.add_argument("--safe-mode", action="store_true", help="민감정보 보호를 위해 Diff 200줄 제한 적용")
    
    args = parser.parse_args()

    # Git Diff 가져오기
    diff_text, line_count = get_git_diff(args.safe_mode)
    print(f"[INFO] Git status 수집 완료: 변경 감지")
    print(f"[INFO] Git diff 수집 완료: {line_count}줄")

    # 프롬프트 구성
    if args.command == "commit":
        prompt = f"""
        다음 git diff를 분석하여 커밋 메시지를 작성해줘.
        규칙:
        1. 첫 줄은 커밋 제목 (50자 이내, feat/fix/docs 등 prefix 사용)
        2. 한 줄 띄우고 커밋 본문 작성
        3. 본문은 변경된 파일이나 핵심 변경 사항을 1~2개 불릿(-)으로 요약할 것.
        
        Git Diff:
        {diff_text}
        """
    else: # pr
        prompt = f"""
        다음 git diff를 분석하여 Pull Request 초안을 작성해줘.
        규칙:
        1. 첫 줄은 PR 제목 (80자 이내)
        2. 본문은 반드시 다음 3개의 마크다운 헤더를 포함할 것: ## Why, ## What, ## How to Test
        3. 각 헤더 아래에는 최소 1개 이상의 불릿(-)을 사용할 것.
        
        Git Diff:
        {diff_text}
        """

    # AI 호출 및 결과 출력
    result = call_ai_api(prompt, args.model, args.temperature, args.max_tokens)
    
    print(f"\n[DONE] {args.command.upper()} 초안 생성 완료\n")
    print(f"--- {args.command.upper()} Message ---")
    print(result)
    print("-------------------------")

if __name__ == "__main__":
    main()