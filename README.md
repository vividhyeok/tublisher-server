# Tublisher

로컬 PC에서 YouTube 영상을 읽기 좋은 EPUB으로 변환하는 개인용 GUI 앱입니다. PySide6 GUI와 framework-agnostic core pipeline으로 구성되어 있습니다.

## 실행

```powershell
pip install -r requirements.txt
python main.py
```

Windows에서는 `run.bat`을 더블클릭해 실행할 수 있습니다. 처음 실행하면 `.venv`를 만들고 필요한 패키지를 설치합니다.

기본 provider는 OpenAI입니다. 실행 전 `.env.example`을 `.env`로 복사하고 `OPENAI_API_KEY`를 채우면 planning, writing, 오디오 STT fallback이 동작합니다.

```env
OPENAI_API_KEY=sk-...
OPENAI_PLANNING_MODEL=gpt-4.1-mini
OPENAI_WRITING_MODEL=gpt-4.1-mini
OPENAI_STT_MODEL=gpt-4o-transcribe
```

## 핵심 흐름

1. YouTube URL 검증
2. 메타데이터와 자막 확보
3. 자막이 없으면 오디오 다운로드 후 OpenAI STT fallback
4. 영상 유형 분류
5. transcript 밀도 분석
6. compact/balanced/expanded 분량 budget 계산
7. 영상 유형에 맞는 Narrative Plan 생성
8. PlanGuard 검사 후 GUI에서 승인/재생성/수정
9. 승인된 plan으로만 원고 작성
10. DraftGuard 검사
11. Markdown, HTML, EPUB 저장

## 구조

```text
app/
├─ core/          # dataclass, length/density policy, guard, orchestrator
├─ providers/     # transcript/audio/stt/planning/writing adapter
├─ renderers/     # markdown/html/epub 생성
└─ ui/            # PySide6 main window, worker, plan review dialog
```

`core`는 PySide6에 의존하지 않습니다. 나중에 CLI나 다른 실행 진입점을 붙이더라도 `BookPipeline`을 그대로 사용할 수 있습니다.

## 영상 유형 처리

모든 영상을 기술 강의처럼 처리하지 않도록 transcript 확보 후 `ContentTypeClassifier`를 실행합니다. 현재 구분하는 유형은 기술 강의, 교육 설명, 뉴스 보도, 뉴스 해설, 개인 의견, 인터뷰, 토론/대담, 리뷰/비평, 에세이/이야기, 혼합입니다.

분류 결과는 plan prompt, writing prompt, plan review 화면에 전달됩니다. Plan Review에서 사용자가 영상 유형을 바꾸면 수정된 `NarrativePlan`이 실제 writing 단계에 반영됩니다.

## 설정

`config.example.toml`을 `config.toml`로 복사해서 기본 저장 폴더, ffmpeg 경로, 기본 provider를 바꿀 수 있습니다. API key는 설정 파일에 저장하지 말고 환경변수나 OS keyring에 둡니다.

## 검증

```powershell
python -m unittest
python -m compileall app tests
```
