# VS Code 설정 가이드

이 문서에서는 `lol_banpick_project`를 Visual Studio Code(이하 VS Code)에서 편리하게 사용하기 위한 설정 방법을 설명합니다.  프로젝트에는 `.vscode` 폴더가 포함되어 있어 기본적인 디버깅과 작업 실행이 즉시 가능하도록 설계되어 있습니다.

## 요구 사항

- Python 3.8 이상이 설치된 로컬 개발 환경
- VS Code와 Python 확장
- Riot 개발자 API 키 (.env 파일로 관리)

## 폴더 구조

```
lol_banpick_project/
├── .vscode/
│   ├── launch.json      # 디버거 설정
│   ├── settings.json    # 프로젝트 별 설정 (python interpreter, env file 등)
│   └── tasks.json       # 터미널 작업 정의
├── src/
│   ├── riot_api_skeleton.py
│   └── app.py           # Streamlit UI
├── data/                # 수집한 데이터 저장
├── docs/
│   └── …
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

## 환경 설정 단계

1. **프로젝트 열기**
   - VS Code를 열고 “Open Folder…” 메뉴를 통해 `lol_banpick_project` 디렉터리를 선택합니다.

2. **가상환경 생성**
   - 터미널(Integrated Terminal)에서 다음 명령을 실행하여 가상환경을 만듭니다:
     ```bash
     python -m venv venv
     ```
   - 생성된 가상환경을 활성화한 뒤 패키지를 설치합니다:
     ```bash
     # Linux/Mac
     source venv/bin/activate
     # Windows
     venv\Scripts\activate
     pip install -r requirements.txt
     ```

3. **환경 변수 설정**
   - 프로젝트 루트의 `.env.example`을 `.env`로 복사합니다.
   - 발급받은 Riot API 키를 `RIOT_API_KEY=`에 입력합니다.
   - VS Code는 `.vscode/settings.json`의 `python.envFile` 설정을 통해 `.env`를 자동으로 로드합니다.

4. **디버그 및 작업 실행**
   - **디버거**: Run and Debug 뷰에서 “Python: Launch Riot API script” 구성을 선택하면 `src/riot_api_skeleton.py`가 실행됩니다.  이 과정에서 `.env` 파일의 API 키가 환경변수로 주입됩니다.
   - **작업(Task)**: Terminal → Run Task… 메뉴를 선택하면 “Run Riot API script”, “Install dependencies”, “Run Streamlit UI” 세 가지 작업이 표시됩니다.  
     - `Run Riot API script`: `riot_api_skeleton.py`를 터미널에서 실행합니다.
     - `Install dependencies`: `requirements.txt`에 명시된 의존성을 설치합니다.
     - `Run Streamlit UI`: `streamlit run src/app.py` 명령을 실행하여 웹 기반 UI를 띄웁니다. 브라우저가 자동으로 열리며, UI를 통해 데이터 분석을 수행할 수 있습니다.

5. **코드 자동 서식**
   - `.vscode/settings.json`에 `editor.formatOnSave`가 `true`로 설정되어 있어 파일 저장 시 자동으로 코드 서식이 적용됩니다. 필요에 따라 이 값을 변경할 수 있습니다.

## 테스트 작성

`tests/` 폴더는 프로젝트의 함수와 로직을 검증하기 위한 테스트 코드를 저장하는 장소입니다.  예를 들어 Python의 `unittest`나 `pytest`를 사용하여 API 래퍼 함수의 동작을 검증하는 테스트를 작성할 수 있습니다.  VS Code에서는 Testing 패널을 통해 테스트 실행을 관리할 수 있습니다.

## 참고

- Riot API의 큐 타입 ID는 [Riot 공식 `queues.json` 문서]에서 확인할 수 있습니다.  예를 들어, 420은 Ranked Solo/Duo, 430은 Normal Blind Pick, 440은 Ranked Flex, 450은 ARAM을 의미합니다【173377830907035†L67-L74】.
- 프로젝트 구조 및 초기 설정 방법은 `docs/project_structure.md`에 보다 자세히 설명되어 있습니다.

이 가이드를 따라 VS Code 환경을 구성하면, 데이터 수집과 밴픽 분석 스크립트를 효율적으로 개발하고 디버깅할 수 있습니다.