# AI-Powered Git Commit & PR Generator 🚀

> Git 변경 사항(`git status`, `git diff`)을 자동으로 수집하여 의미 있는 커밋 메시지와 Pull Request 초안을 생성해 주는 Python CLI 도구입니다.

## 🛠 1. 설치 및 실행 방법

1. 리포지토리 루트 디렉토리에 `main.py`와 `team_rules.txt` 파일을 위치시킵니다.
2. AI API 키를 환경변수로 설정합니다:
   ```bash
   export AI_API_KEY="여러분의_VIRTUAL_KEY"
   ```
3. 도구를 실행합니다:
   - **커밋 메시지 생성:**
     ```bash
     python main.py commit --model gpt-5-mini
     ```
   - **PR 초안 생성:**
     ```bash
     python main.py pr --model gpt-5-mini --convention team_rules.txt --safe-mode
     ```

---
## ⚖️ 2-1. 실제 리포지토리에 적용 (보너스 과제 1)
## ⚖️ 2-2. 팀 컨벤션 적용 전후 비교 분석 (보너스 과제 2)
여행/호텔 추천 AI 서비스를 개발하는 팀을 위한 팀 규칙 작성. 서비스의 특성을 반영하여 명확한 커밋 및 PR 컨벤션을 디테일하게 구성함



`team_rules.txt` 파일을 적용(`--convention`)했을 때와 적용하지 않았을 때의 AI 생성 결과 차이점 분석 내용

| 비교 항목 | 컨벤션 미적용 (Default) | 컨벤션 적용 (`--convention team_rules.txt`) |
| :--- | :--- | :--- |
| **1. 문체 및 어조** | 건조한 평어(반말) 및 무뚝뚝한 표현 (`"제공함"`, `"확인한다"`) | 일관된 한국어 존댓말 및 정중한 표현 (`"정리하였습니다"`, `"확인합니다"`) |
| **2. 템플릿 및 추가 제안** | 순수 PR 템플릿 요약 중심 | 본문 내에 **"권장 커밋 메시지"** 하위 항목을 스스로 생성하여 추가 제안 |
| **3. 시각적 요소 및 용어** | 이모지 없음, 전형적인 영문/국문 혼용 개발 스타일 | 상단 제목에 이모지(`📚`) 포함 및 친근하고 직관적인 구성 |
| **4. 예외/제한 상황 인지** | diff가 잘린 경우(`--max-lines`) 리뷰어에게 적극적으로 경고 및 양해 구함 | 잘린 코드에 대한 경고보다는 팀 규칙의 형식과 템플릿 완성도에 집중 |

---

## 🔒 3. 주요 옵션 및 보안 (Safe Mode)

- `--model <model_name>`: 사용할 AI 모델 지정 (기본: `gpt-5-mini`)
- `--convention <file_path>`: 팀 컨벤션 규칙 파일을 불러와 적용
- `--safe-mode`: 정규표현식을 이용한 민감 정보(이메일, API Key 등) 자동 마스킹 (`***[MASKED]***`)
- `--max-lines <number>`: 전송 줄 수 제한을 통한 토큰 절약 및 타임아웃 방지 (기본: 200줄)