import os
import sys
import subprocess
import argparse
import requests
import re
from typing import Tuple, Optional

# ==========================================
# 1. 안전 모드 (민감 정보 마스킹 및 길이 제한)
# ==========================================
# ==========================================
# 1. 민감 정보 마스킹 함수
# ==========================================
def apply_safe_masking(diff_text: str) -> str:
    """정규표현식을 사용해 이메일 및 API Key 등 민감 정보를 마스킹합니다."""
    # 1. 이메일 마스킹
    diff_text = re.sub(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', 
        '***@***.***', 
        diff_text
    )
    
    # 2. API Key, Secret 마스킹 (sk-..., AI_API_KEY=... 형태)
    diff_text = re.sub(r'(sk-[a-zA-Z0-9]{20,})', 'sk-***[MASKED]***', diff_text)
    diff_text = re.sub(
        r'((?:API_KEY|SECRET|PASSWORD|TOKEN)\s*[:=]\s*["\']?)[^"\'\n]+(["\']?)', 
        r'\g<1>***[MASKED]***\g<2>', 
        diff_text, 
        flags=re.IGNORECASE
    )
    return diff_text

# ==========================================
# 2. Git 변경 사항 수집 (줄 수 제한 항상 적용)
# ==========================================
def get_git_diff(safe_mode: bool = False, max_lines: int = 200) -> Tuple[str, int, int]:
    """
    git status 및 git diff 결과를 수집합니다.
    대용량 diff로 인한 API 타임아웃 방지를 위해 줄 수 제한은 항상 적용됩니다.
    """
    # 프로젝트가 git 저장소인지 확인
    if subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], capture_output=True).returncode != 0:
        print("[ERROR] 현재 디렉토리는 Git 저장소가 아닙니다.")
        sys.exit(1)

    # 상태 확인
    status = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    if not status.stdout.strip():
        print("[INFO] 변경 사항이 없습니다. 작업을 종료합니다.")
        sys.exit(0)
    
    file_count = len(status.stdout.strip().split('\n'))

    # Diff 수집 (우선 staged 파일 기준, 없으면 전체 변경 기준)
    diff = subprocess.run(['git', 'diff', '--cached'], capture_output=True, text=True)
    diff_text = diff.stdout
    
    if not diff_text.strip():
        # staged된 파일이 없다면 unstaged 파일들의 diff 수집
        diff = subprocess.run(['git', 'diff'], capture_output=True, text=True)
        diff_text = diff.stdout

    # 1. 줄 수 제한은 안전 모드와 무관하게 항상 적용 (API 터짐 방지)
    lines = diff_text.split('\n')
    if len(lines) > max_lines:
        diff_text = '\n'.join(lines[:max_lines])
        diff_text += f"\n\n... [토큰 절약을 위해 {max_lines}줄로 제한되었습니다.]"

    # 2. 민감 정보 마스킹은 safe_mode가 True일 때만 적용
    if safe_mode:
        diff_text = apply_safe_masking(diff_text)
        # 마스킹 안내 문구 추가
        diff_text += f"\n\n... [SAFE MODE ON: 민감 정보 마스킹이 적용되었습니다.]"
            
    return diff_text, len(diff_text.split('\n')), file_count

# ==========================================
# 2. Git 변경 사항 수집
# ==========================================
def get_git_diff(safe_mode: bool = False, max_lines: int = 200) -> Tuple[str, int, int]:
    """
    git status 및 git diff 결과를 수집합니다.
    staged(git add 된) 파일이 없으면 unstaged 파일을 수집합니다.
    """
    # 프로젝트가 git 저장소인지 확인
    if subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], capture_output=True).returncode != 0:
        print("[ERROR] 현재 디렉토리는 Git 저장소가 아닙니다.")
        sys.exit(1)

    # 상태 확인
    status = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    if not status.stdout.strip():
        print("[INFO] 변경 사항이 없습니다. 작업을 종료합니다.")
        sys.exit(0)
    
    file_count = len(status.stdout.strip().split('\n'))

    # Diff 수집 (우선 staged 파일 기준, 없으면 전체 변경 기준)
    diff = subprocess.run(['git', 'diff', '--cached'], capture_output=True, text=True)
    diff_text = diff.stdout
    
    if not diff_text.strip():
        # staged된 파일이 없다면 unstaged 파일들의 diff 수집
        diff = subprocess.run(['git', 'diff'], capture_output=True, text=True)
        diff_text = diff.stdout

    # 안전 모드 적용
    if safe_mode:
        diff_text = apply_safe_mode(diff_text, max_lines)
            
    return diff_text, len(diff_text.split('\n')), file_count

# ==========================================
# 3. 팀 컨벤션 규칙 로드
# ==========================================
def load_convention(file_path: Optional[str]) -> str:
    """외부 텍스트 파일에서 팀의 커밋/PR 규칙을 불러옵니다."""
    if not file_path:
        return ""
    
    if not os.path.exists(file_path):
        print(f"[WARNING] 컨벤션 파일을 찾을 수 없습니다: {file_path}")
        return ""
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            rules = f.read().strip()
            return f"\n[팀 컨벤션 규칙]\n다음 규칙을 반드시 엄격하게 지켜서 작성해줘:\n{rules}\n"
    except Exception as e:
        print(f"[WARNING] 컨벤션 파일을 읽는 중 오류가 발생했습니다: {e}")
        return ""

# ==========================================
# 4. AI API 호출 로직
# ==========================================
# ==========================================
# 4. AI API 호출 로직 (교육용 서버 맞춤형 수정)
# ==========================================
def call_ai_api(prompt: str, model: str, temperature: float, max_tokens: int) -> str:
    """REST API를 사용하여 AI 모델을 호출합니다."""
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        print("[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    print(f"[INFO] AI API 요청 중... (Model: {model})")
    
    response = None
    try:
        # 가이드 코드와 동일한 헤더 구조
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 가이드 코드와 동일하게 모델명과 사용자 메시지만 딱 맞춘 최소 구조
        # (temperature, max_tokens, system role은 서버가 거부하므로 제거)
        payload = {
            "model": model, 
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        response = requests.post(
            "https://copa.codyssey.kr/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=300
        )
        response.raise_for_status() 
        
        return response.json()["choices"][0]["message"]["content"]
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] 네트워크 통신 또는 API 호출 실패: {e}")
        if response is not None and response.text:
            print(f"[DEBUG] 응답 내용: {response.text}")
        sys.exit(1)
# ==========================================
# 5. 메인 실행부
# ==========================================
def main():
    parser = argparse.ArgumentParser(description="AI 기반 Git 커밋/PR 자동 생성기 (Advanced)")
    parser.add_argument("command", choices=["commit", "pr"], help="실행할 명령어 (commit 또는 pr)")
    parser.add_argument("--model", default="gpt-5-mini", help="사용할 AI 모델 (기본: gpt-5-mini)")
    parser.add_argument("--temperature", type=float, default=0.7, help="창의성 조절 (0.0 ~ 1.0, 기본: 0.7)")
    parser.add_argument("--max-tokens", type=int, default=800, help="최대 생성 토큰 수")
    
    # 보너스 과제 구현 인자
    parser.add_argument("--safe-mode", action="store_true", help="민감정보 마스킹 및 Diff 줄 수 제한 적용")
    parser.add_argument("--max-lines", type=int, default=200, help="safe-mode 적용 시 최대 전송 줄 수")
    parser.add_argument("--convention", type=str, help="팀 컨벤션 규칙 파일 경로 (예: rules.txt)")
    
    args = parser.parse_args()

    # 1. Git Diff 가져오기
    diff_text, line_count, file_count = get_git_diff(args.safe_mode, args.max_lines)
    print(f"[INFO] Git status 수집 완료: {file_count}개 파일 변경 감지")
    print(f"[INFO] Git diff 수집 완료: {line_count}줄 전달 예정")

    # 2. 팀 컨벤션 로드
    convention_text = load_convention(args.convention)

    # 3. 프롬프트 구성 (요구사항 완벽 반영)
    if args.command == "commit":
        prompt = f"""
다음 git diff를 분석하여 Git 커밋 메시지를 작성해줘.

[필수 작성 규칙]
1. 첫 줄은 커밋 제목으로 작성하며 50자 이내로 제한해. (feat/fix/docs 등 prefix 사용)
2. 한 줄 띄우고 커밋 본문을 작성해.
3. 본문에는 변경된 핵심 파일(또는 모듈) 1~3개를 언급하고, 변경 사항을 1~2개의 불릿(-) 기호로 요약해.
{convention_text}

[Git Diff]
{diff_text}
"""
    else: # pr
        prompt = f"""
다음 git diff를 분석하여 Pull Request(PR) 초안을 작성해줘.

[필수 작성 규칙]
1. 첫 줄은 PR 제목으로 작성하며 80자 이내로 제한해.
2. 본문은 반드시 다음 3개의 마크다운 섹션 헤더(##)를 정확히 포함해야 해:
   ## Why (변경 배경)
   ## What (핵심 변경 사항)
   ## How to Test (테스트 방법)
3. 각 헤더 아래에는 반드시 1개 이상의 불릿(-)을 사용하여 내용을 요약해.
{convention_text}

[Git Diff]
{diff_text}
"""

    # 4. AI 호출 및 결과 출력
    result = call_ai_api(prompt, args.model, args.temperature, args.max_tokens)
    
    print(f"\n[DONE] {args.command.upper()} 초안 생성 완료!\n")
    print("=" * 50)
    print(result.strip())
    print("=" * 50)

if __name__ == "__main__":
    main()