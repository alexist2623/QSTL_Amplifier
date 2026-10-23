# THS3491 RGT G≈20 — Altium Rev C 검토본

후속 CAD는 [Rev D](../altium_revD/README.md)에 있다. 아래 내용과 이 폴더의
네이티브 CAD는 원래 Rev C 기록이며, 최신 배치 및 스택 메타데이터 수정은 Rev D에 적용했다.

2026-10-22. 편집 파일은 [프로젝트](QSTL_THS3491_RGT_G20_RevC.PrjPcb), [회로도](QSTL_THS3491_RGT_G20_RevC.SchDoc), [PCB](QSTL_THS3491_RGT_G20_RevC.PcbDoc)이다. **Altium 내부 열기·저장·ERC·repour·DRC는 미검증이며 제조 승인본은 아니다.** 이 PC에서 Altium 편집 화면과 스크립트 검증 로그를 확보하지 못해, 생성 파일을 별도 Altium 판독기로 재검사했다.

## Latest instructions versus this CAD snapshot

The native files in this directory are the existing Rev C snapshot. Later user corrections are documented in [DESIGN_REQUIREMENTS.md](../../../DESIGN_REQUIREMENTS.md) and the [planning drawings](../planning/README.md), but have **not** been applied to these native files. In particular, the C5/C6 EVM placement, relocation of C3/C4 toward the input filters, the narrow C5 supply island, the separate PD16 trace/via, and the NC15 connection to surrounding L1 GND remain planning changes.

The user requested these drawings without launching Altium. Publishing this snapshot does not change the CAD or mark the planning changes as implemented. The revision description and validation results below describe the existing snapshot, including superseded geometry. The scripts in `tools/` are historical generation/review sources; some depend on local KiCad installations, staging data, TI reference imports, and native carrier files that are not needed to open the supplied Altium project and are not a portable rebuild environment.

## Rev C에서 바뀐 점

TI가 공개한 [HSP006A Altium 원본](https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/14/HSP006A.zip)을 기준으로 다시 구성했다. U1, J1/J2/J3, R1–R7의 위치·회전은 원본과 같고 입력 곡선 세 개를 복사했다. 기하 비교 결과는 [좌표 비교](review/source_geometry_comparison.json)에 있다. 그림을 보고 추정했던 Rev B를 대체한다.

- 보드 외형 41.656 × 68.58 mm, TI 원본 edge-launch SMA 풋프린트 사용. SMA와 헤더는 별도 조달/수동 조립 검토 대상이다.
- R4=390 Ω, R3=20.5 Ω, 기본 비반전 이득 `1+390/20.5=20.02439 V/V`. R2=0 Ω 장착, −입력 J1 유지. R2 제거 후에는 외부 연결 상태가 이득에 영향을 준다. R5는 DNP, R6=0 Ω는 실제 부품으로 복원했다.
- 출력 감쇠망 R9–R13 제거. R14=49.9 Ω 직렬, R15=1 MΩ 출력 부하. RF 경로가 해당 SMD 신호 패드를 통과한다.
- +15 V와 −15 V 입력, C1/C2, L1/L2, C3/C4, C5/C6는 U1 중심으로 180° 대칭이다. −15 V 입력의 C2는 L1 상면도에서 왼쪽에 있다.
- 전원은 **입력의 작은 L1 면 → 병렬 비아 → L3 전원 면 → 소자 근처 병렬 비아 → 작은 L1 면**으로 공급한다. 전원 net의 독립 track은 0개다. VCC/VEE 핀 위치 차이와 TEMP 배선 때문에 실제로 채워진 동박 모양까지 완벽한 대칭은 아니다.
- C3/C5를 U1 근처에 배치했다. 이들의 GND 패드는 L1 전원 동박에서 분리되어 있다. U1의 2/5/9/12/15번과 EP 17번은 GND에 연결하며, EP 안에 접지 비아 5개를 넣었다.
- 부품 패드 안의 비아 19개와 EP 비아 5개는 충전·평탄화·동도금 캡(VIPPO/POFV)을 지정한다. 나머지는 별도 GND stitching이다. 관통 비아 0.40/0.20 mm를 사용한다.
- 일반 패드는 thermal gap 0.20 mm / spoke 0.25 mm. U1/EP, H9, C3–C6 GND 패드와 비아는 직접 연결한다. 이 예외는 고주파 바이패스와 방열 경로를 위한 것이다.
- 하면 H9 방열 부품을 유지하고, 관통 전원 비아와 방열 접촉 패드의 단락을 피하도록 원본보다 1.8 mm 아래로 이동했다. 열성능과 기구 접촉은 별도 확인이 필요하다.

## TEMP 헤더

J7은 1×2, **2.54 mm 피치**이며 **1번 TEMP, 2번 GND**다. EVM의 `U1.6 → TJ_RAW → R8(0 Ω) → TEMP` 경로와 TJ_RAW–GND의 C8=100 nF를 유지했다. 점퍼 케이블을 이용한 측정용이며 두 핀을 쇼트하는 점퍼 캡을 꽂는 자리가 아니다.

TEMP(TJ_SENSE)는 칩 접합온도를 전압으로 나타낸다. 전형값은 25°C에서 1.06 V, 기울기는 3.2 mV/°C다. 전형적인 근사식은 `Tj ≈ 25 + (VTEMP−1.06)/0.0032 °C`이며 정확한 온도계 공식은 아니다. 25°C 전압의 부품 편차와 부하 오차가 있어 보정이 필요하다. 내부 저항 전형값이 35 kΩ이므로 충분히 높은 입력 임피던스의 계측기 또는 버퍼를 사용한다. 10 MΩ 입력을 사용해도 부하 오차가 완전히 없어지지는 않는다. 기준 GND는 U1.5에 연결된다. [TI 데이터시트 §9.3.3, 전기 특성](https://www.ti.com/lit/gpn/ths3491)

## EVM R9·R10·R11의 역할

- R9/R10은 각각 240 Ω인 병렬 출력 부하이며 합성값은 120 Ω이다. 부하와 저항 발열을 나눠 갖는다.
- R11=287 Ω는 R12=287 Ω, R13=54.9 Ω와 출력 감쇠망을 구성한다. 외부 계측기 50 Ω까지 연결하면 전압 비는 약 0.0436, 즉 −27.2 dB이고 증폭기에서 보는 합성 부하는 약 100 Ω이다. 외부 부하가 바뀌면 이 값도 바뀐다.
- 증폭기 폐루프 이득을 정하는 저항은 R3/R4다. 이번 보드에서는 요청대로 R9–R13을 제거했다.

[원본 TI 회로도 강조 PNG](review/TI_original_schematic_highlighted.png), [강조 PDF](review/TI_original_schematic_highlighted.pdf), [출력망 및 TEMP 설명도](review/EVM_R9_R10_R11_TEMP_explained.png). 근거: [TI EVM 가이드](https://www.ti.com/lit/ug/slou483/slou483.pdf). 설명도의 회로는 원본에서 정확히 다시 그린 도식이며 Altium 화면 캡처는 아니다.

## 스택 및 임피던스 설계 기준

JLC04161H-7628, 4층, 공칭 1.6 mm, 외층 1 oz / 내층 0.5 oz. L1/L2 사이 7628 prepreg 0.2104 mm, Er=4.4; 중앙 core 1.065 mm, Er=4.6. L1 RF/국부 전원/GND, L2 GND, L3 분할 전원, L4 GND/방열이다. U1 민감 노드 아래에는 국부 copper void를 둔다.

[JLC 공식 계산기](https://jlcpcb.com/pcb-impedance-calculator)의 soldermask 포함 CPWG 50 Ω 기준은 W=0.3058 mm, G≈0.20 mm다. 이번 zone clearance는 0.205 mm로 설정했으며, 패드/커넥터/바이어스 구간은 일정한 CPWG 단면이 아니다. 이는 SI 해석 결과가 아니다. 이전에 저장한 계산기 입력·결과 화면을 `review/`에 함께 포함했다.

TI 원본은 8층이다. 이 보드는 RF 좌표를 유지하면서 전원/접지/비아/층 수를 바꾼 4층 설계이며 TI EVM과 같은 SI·PI·열·EMC 성능을 보장하지 않는다. 과거 LTspice 결과에도 PCB 기생 성분은 포함되지 않는다.

## 검토 결과와 파일

- [L1 전체](review/layout_L1_annotated.png), [U1 주변 확대](review/layout_core_detail.png), [L3 전원](review/layout_L3_power.png), [회로도](review/schematic.png).
- 생성 전 기하: 오류 0, 미연결 0, 경고 33개. 32개는 가져온 풋프린트의 라이브러리 연결 경고이며 1개는 원본의 직선과 겹치는 약 9 µm 보조 arc 끝점 경고다. 이 보조 arc는 원본 보존을 위해 유지했으며 주 곡선과 전기적으로 겹친다.
- 실제 `.PcbDoc` 재판독: 4층, 부품/기구 객체 35개, 패드 84개, 곡선 3개, 비아 643개, 핀/기하 비교 오류 0. J7 피치 2.54 mm 확인.
- 가져온 동박을 재채움하지 않은 감사 검사: 오류 0, 미연결 0, 경고 47개. 라이브러리 연결 경고 35개, no-paste 패드 표현 경고 11개, 보조 arc 끝점 경고 1개다. 가져오기에서 지원하지 않는 pad별 polygon 규칙만 감사 복사본에 재적용했다.
- 회로도 생성 레코드: 전기적 핀 80개 연결 검사 오류 0. Altium ERC와는 별도 검사다.
- 판독기는 사용하지 않는 legacy Internal Plane 이름을 건너뛴다는 경고도 남겼다. 실제 활성 구리층은 4개로 확인했다.
- [검증 요약](review/validation_summary.json), [재판독 검사](review/native_import_check.json), [DRC](review/native_audit_drc.json), [BOM](assembly/BOM_REVIEW.csv), [SMT BOM](assembly/BOM_SMT_REVIEW.csv), [SMT 좌표](assembly/CPL_SMT_REVIEW.csv), [수동 조립](assembly/BOM_MANUAL_REVIEW.csv), [패드 내 비아](assembly/VIA_IN_PAD_PROCESS_REVIEW.csv).

PNG는 실제 동박 좌표 또는 회로도 생성 레코드로 만든 검토 그림이다. 부품 몸체/3D STEP 모델은 포함하지 않는다. BOM의 기존 MPN/LCSC 정보는 앞선 조사에서 이어받았고 실시간 재고를 다시 확인한 결과는 아니다. 신규 J7과 TI 원본 SMA의 구매 코드/재고는 확정하지 않았다. 조립 발주 전 확인해야 한다.

Altium 내부 검증, 스텐실 개구·비아 캡 공정, 제조사 스택 확인, SMA launch/패드 불연속의 SI, PDN 임피던스, 발열과 EMC 검증은 미완료다. 제조용 Gerber는 이번 검토본에서 발행하지 않았으며 이전 리비전의 Gerber를 사용하면 안 된다.
