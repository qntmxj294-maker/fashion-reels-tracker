# 덕구 패션 릴스 레이더 — 무료 운영 개선판

작성·공개 안내 확인: 2026-10-09. 기존 ZIP은 수정하지 않았습니다.

## 바로 사용하는 방법: API 없이 직접 저장

함께 제공한 `fashion-reels-manual.html`을 Chrome 또는 Edge에서 열면 됩니다.
인스타그램에서 발견한 릴스의 링크, 계정명, 확인한 조회수를 직접 입력합니다.
1,000만 회 이상인 기록을 저장·검색·정렬하고 메모와 분류를 붙일 수 있습니다.
API 계정·토큰·결제가 필요 없습니다. 조회수를 자동으로 확인하거나 갱신하지 않습니다.

- 자료는 해당 브라우저의 저장소에 저장됩니다. 다른 컴퓨터/브라우저와 자동 동기화되지 않습니다.
- `JSON 백업`으로 내려받고 `백업 가져오기`로 복원하세요.
- 파일 위치 변경, 시크릿 모드, 브라우저 데이터 삭제 등으로 저장소가 달라지거나 사라질 수 있습니다.
- 직접 입력·가져온 자료는 API 수집 자료와 구분해 표시합니다.
- 같은 링크를 직접 입력하면 최신 기록으로 갱신합니다. API 관측과 수동 메모는 별도로 보존합니다.

## 자동 수집 설정: GitHub + Apify Free

1. GitHub에서 **공개 저장소**를 만들고 기본 브랜치를 `main`으로 사용합니다.
2. 이 폴더 **안의 파일과 `.github` 폴더**를 저장소 최상위에 업로드합니다. ZIP 자체를 올리거나 폴더를 한 단계 더 감싸지 마세요. 숨김 폴더 `.github`가 포함됐는지 확인합니다.
3. Settings → Pages → Source에서 **GitHub Actions**를 선택합니다.
4. Apify 계정을 만들고 Billing → Subscription에서 **Free** 상태를 확인합니다. 유료 업그레이드는 필요 없습니다.
5. Apify 토큰을 GitHub의 Settings → Secrets and variables → Actions → New repository secret에 **`APIFY_TOKEN`**이라는 이름으로 저장합니다. HTML·JSON·소스에 토큰을 넣지 마세요.
6. `accounts.json`에 추적할 **공개 패션 계정**을 입력합니다. 기존 4개는 원본에서 가져온 예시이며, 계정의 현재 공개 상태·패션 적합성은 별도 확인이 필요합니다.
7. Actions → **Daily fashion reels refresh** → Run workflow를 실행합니다. 비용 예약 후 수집합니다. 같은 한국 날짜의 추가 실행·재시도는 수집을 건너뜁니다.
8. Settings → Pages에 표시된 사이트 주소를 엽니다. 실패 시 Actions 로그와 `data/status.json`을 확인하세요.

`git push`가 거부되면 Settings → Actions → General → Workflow permissions 및 브랜치 보호 규칙을 확인합니다. 예약 기록 저장이 실패하면 수집은 실행되지 않습니다.
`github-pages` 환경의 배포 브랜치 제한도 `main`을 허용해야 합니다.

### 기본 수집 범위와 비용

`config.json` 기본값:

| 항목 | 기본값 |
|---|---|
| 실행 | 하루 1회, 한국시간 09:17 예정 |
| 계정 수 | 하루 최대 4개, 초과하면 순환 |
| 계정별 실행 요금 상한 | $0.02 |
| 최근 31일 예약 상한 합계 | 최대 $3 |
| 릴스 요청 수 | 계정별 최대 50개, 수집기 필터·예산에 따라 일부만 반환 |
| 게시 기간 | 최근 365일 |
| 조회수 조건 | 10,000,000 이상 |

기본 설정의 예약 상한 합계는 4개 × $0.02 × 31일 = **$2.48**입니다.
이 수치는 **수집 실행의 예약 상한**이며 실제 청구액이나 Apify 계정 전체 사용액이 아닙니다.
Apify Free의 $5 크레딧은 다른 수집기·저장소 등 계정 사용량과 공유됩니다. Free 크레딧을 소진하면 다음 결제 주기까지 수집이 중단됩니다.

예산은 매달 1일 초기화하는 대신 **매 시점의 최근 31일**을 계산합니다. 결제일이 달라도 여유를 확보하기 위한 설정입니다.
실패·시간 초과·빈 결과도 예약한 최대 금액을 계속 사용한 것으로 계산합니다. 취소된 실행의 예약도 자동 환불하지 않습니다.
`data/budget.json`을 지우거나 과거 상태로 되돌리면 예산 방어가 사라집니다. 유지하세요.

### 바뀐 부분

- 6시간 실행을 하루 1회로 변경. 한국 날짜별 중복 실행 차단.
- 한 번에 모든 계정을 요청하던 방식을 **계정별 별도 요청**으로 변경. 첫 계정이 예산을 소진해 뒤 계정이 계속 누락되는 문제 완화.
- 계정을 늘리면 하루 4개씩 순환. 예: 20개면 계정별 약 5일 주기이며 실시간 추적이 아닙니다.
- 유료 실행 전 `/users/me`로 `plan.tier=FREE`, 월 기본요금 0인지 확인. 응답을 확인하지 못하거나 유료 요금제면 중단.
- 비용 예약을 Git에 먼저 저장한 뒤 수집. 재시도·실패를 통한 중복 지출 방지.
- 기존 `maxItems=12` 제거. 해당 값은 PPE 수집기의 결과 개수 제한을 보장하지 않습니다. `maxTotalChargeUsd`로 실행 비용 제한.
- 계정별 실패 상태, 반환 수, 조건 통과 수 저장. 실패한 계정의 기존 자료 유지.
- API 응답 성공과 ‘등록한 모든 계정의 완전한 수집’을 구분. 결과가 0개여도 인기 릴스가 없다고 단정하지 않음.
- 직접 저장, 분류·메모, 검색·정렬, JSON 백업/가져오기 추가.
- 화면 자료의 외부 링크를 인스타 릴스 주소로 제한. 사용자 텍스트는 HTML로 실행하지 않음.
- 배포 대상으로 HTML/CSS/JS와 공개 데이터만 포함.

### 대체 수집기 선택

기본 `provider: "filtered"`는 원본의 `themineworks/instagram-reels-views-scraper`입니다. 공개 안내상 `minViews` 미만인 릴스는 결과 요금에서 제외되어 이 용도에 유리합니다. 외부 개발자가 관리하며 실제 접근 성공은 Instagram 상태에 영향을 받습니다.

이 수집기에 문제가 있으면 `config.json`의 `provider`를 **`"apify"`**로 바꿔 다음 날 실행할 수 있습니다. 대체 수집기는 Apify가 관리하는 `apify/instagram-reel-scraper`입니다. **Instagram/Meta의 공식 API라는 뜻은 아닙니다.** 자동으로 두 서비스를 연속 호출하지 않습니다.

대체 수집기는 가져온 릴스 전체에 비용이 발생한 뒤 로컬에서 1,000만 기준을 적용합니다. 같은 $0.02 상한에서는 최신 릴스 몇 개만 읽고 인기 영상을 놓칠 수 있습니다. 무조건 더 저렴하거나 더 넓게 찾는 대안은 아닙니다. 원본 `play_count`와 대체의 `videoPlayCount`/`videoViewCount`는 출처 필드를 함께 저장하며 동일한 지표라고 숨기지 않습니다.

신규 릴스만 받는 monitor mode는 기본으로 쓰지 않았습니다. 오래된 릴스가 나중에 1,000만을 넘는지 다시 확인해야 하기 때문입니다.

## 다른 무료 방법 검토

| 방식 | 판단 |
|---|---|
| 이 도구의 직접 저장 모드 | API 비용 없이 바로 사용. 자동 발굴·자동 조회수 갱신은 없음 |
| 현재 Apify + GitHub 개선판 | 무료 크레딧 내 소규모 자동 추적에 적합. 지정 계정·예산 범위만 수집 |
| Apify 관리 수집기로 변경 | 장애 시 선택 가능. 동일한 무료 크레딧 공유, 필터 전 결과도 과금 |
| 로컬 Instaloader | 오픈소스 대안. 설치·접근 실패 대응·PC 실행이 필요하며 전체 검색과 조회수 확보를 보장하지 않아 기본 대안으로 채택하지 않음 |

수집기가 약속하는 것은 공개 계정별 수집입니다. 전 세계 패션 릴스 전체를 검색하거나 패션 여부를 자동으로 판단하는 제품은 아닙니다.
등록 계정의 콘텐츠에는 패션 외 영상이 섞일 수 있습니다. 원본 링크에서 직접 판단하세요.

## 제한과 운영

- GitHub 예약 작업은 지연될 수 있습니다. 저장소 활동이 없는 공개 저장소의 예약은 60일 후 비활성화될 수 있습니다.
- 조회수는 각 카드의 기록 시점 기준이며 현재 실시간 수치가 아닙니다.
- 최근 기간·요청 수·예산 상한에 걸리면 인기 영상도 누락될 수 있습니다. 전체 수집을 검증하는 로직은 없습니다.
- 페이지를 새로고침하는 버튼은 이미 저장된 데이터를 읽기만 합니다. 유료 수집을 시작하지 않습니다.
- 로컬 `index.html`을 직접 열면 직접 저장 모드가 작동합니다. 자동 JSON 읽기는 웹 서버/GitHub Pages에서 사용합니다.
- 계정 토큰이 제공되지 않았으므로 실제 Instagram 수집, Free 계정 응답, GitHub 배포 성공은 아직 확인하지 못했습니다. 파일과 비용·보존 로직은 모의 API로 검증했습니다.

## 개발 검증

Python 3.12 이상, 추가 패키지 불필요:

```text
python collect.py dry-run
python -m unittest -v test_collect.py
node --test test_app.cjs
```

`dry-run`은 네트워크 요청·예약 저장·수집을 하지 않고 다음 실행 대상을 출력합니다.
로컬 자동 실행은 `python collect.py prepare` 후 `python collect.py collect` 순서입니다. GitHub에서는 워크플로가 예약을 먼저 커밋합니다.

## 확인한 공식 자료

- Apify Free 요금 및 크레딧: https://apify.com/pricing
- Free 소진 시 중단: https://docs.apify.com/account/subscriptions
- 원본 수집기·입력: https://apify.com/themineworks/instagram-reels-views-scraper / https://apify.com/themineworks/instagram-reels-views-scraper/input-schema
- 대체 수집기·입력: https://apify.com/apify/instagram-reel-scraper / https://apify.com/apify/instagram-reel-scraper/input-schema
- 실행 상한 API: https://docs.apify.com/api/v2/actors-runs-post
- Free 확인 API: https://docs.apify.com/api/v2/users-me-get
- GitHub Pages: https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages
- Actions 비용: https://docs.github.com/en/billing/concepts/product-billing/github-actions
- 예약 비활성화: https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows
- Instaloader: https://instaloader.github.io/basic-usage.html

요금·스키마가 바뀌면 공개 자료 및 계정 콘솔을 다시 확인해야 합니다. 이 문서는 유료 구독을 요구하지 않습니다.
